<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { getSubmissionDetail, gradeSubmission } from '$lib/api/calledAPI';
	import { getApiErrorMessage } from '$lib/api/errors';
	import type { Submission, SubmissionDetail } from '$lib/api/entities';
	import { POINT_STEP, buildGradePayload, isValidPointStep, sumPoints } from '$lib/utils/assignment';
	import Avatar from '$lib/components/Avatar.svelte';
	import { showToast } from '$lib/stores/toast.svelte';
	import FieldError from '$lib/components/FieldError.svelte';
	import { FIELD_LIMITS, tooLongError, blockNonNumericKey } from '$lib/utils/validation';
	import { confirmAction } from '$lib/stores/confirm.svelte';
	import { CheckCircle2, ChevronRight, ClipboardCheck, Clock } from 'lucide-svelte';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	let submissions = $derived(data.submissions);

	let selected = $state<SubmissionDetail | null>(null);
	let isLoadingDetail = $state(false);
	let isSaving = $state(false);
	let drafts = $state<Record<number, { point: number | null; tutor_comment: string }>>({});
	let gradeErrors = $state<Record<number, string>>({});

	function clearGradeError(answerId: number) {
		gradeErrors = { ...gradeErrors, [answerId]: '' };
	}

	function maxPointOf(answerId: number): number {
		const answer = selected?.stu_answers.find((item) => item.id === answerId);
		return Number(answer?.question_point ?? 0);
	}

	function gradeErrorFor(answerId: number): string {
		const draft = drafts[answerId];
		if (!draft) return '';

		const point = draft.point;
		const maxPoint = maxPointOf(answerId);

		if (point !== null && !Number.isNaN(point)) {
			if (point < 0 || point > maxPoint) {
				return `Điểm phải nằm trong khoảng 0 - ${maxPoint}.`;
			}

			if (!isValidPointStep(point)) {
				return `Điểm phải là bội của ${POINT_STEP}, ví dụ 0.25, 0.5, 1.75.`;
			}
		}

		return tooLongError(draft.tutor_comment, FIELD_LIMITS.tutorComment, 'Nhận xét');
	}

	function checkGradeOnBlur(answerId: number, input: HTMLInputElement) {
		const message = input.validity.badInput ? 'Điểm phải là số.' : gradeErrorFor(answerId);
		gradeErrors = { ...gradeErrors, [answerId]: message };
	}

	function validateGrade(): boolean {
		if (!selected) return false;

		const errors: Record<number, string> = {};

		for (const id of Object.keys(drafts)) {
			const answerId = Number(id);
			errors[answerId] = gradeErrorFor(answerId);
		}

		gradeErrors = errors;
		return !Object.values(errors).some((message) => message !== '');
	}

	let pendingCount = $derived(submissions.filter((s) => s.score === null).length);

	type AssignmentGroup = {
		assignmentId: number;
		title: string;
		chapterTitle: string;
		items: Submission[];
		pendingCount: number;
	};

	let assignmentGroups = $derived.by(() => {
		const groups = new Map<number, AssignmentGroup>();

		for (const submission of submissions) {
			let group = groups.get(submission.assignment);

			if (!group) {
				group = {
					assignmentId: submission.assignment,
					title: submission.assignment_title,
					chapterTitle: submission.chapter_title,
					items: [],
					pendingCount: 0
				};
				groups.set(submission.assignment, group);
			}

			group.items.push(submission);

			if (submission.score === null) {
				group.pendingCount += 1;
			}
		}

		const groupList = [...groups.values()];

		for (const group of groupList) {
			group.items.sort((first, second) => {
				return Number(second.score === null) - Number(first.score === null);
			});
		}

		groupList.sort((first, second) => second.pendingCount - first.pendingCount);
		return groupList;
	});

	let chosenAssignmentId = $state<number | null | undefined>(undefined);

	let openedGroupId = $derived(
		chosenAssignmentId === undefined
			? (assignmentGroups[0]?.assignmentId ?? null)
			: chosenAssignmentId
	);

	function toggleGroup(assignmentId: number) {
		chosenAssignmentId = openedGroupId === assignmentId ? null : assignmentId;
	}

	function formatDate(iso: string | null): string {
		if (!iso) return '--';
		return new Date(iso).toLocaleString('vi-VN', {
			day: '2-digit',
			month: '2-digit',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	async function openSubmission(submissionId: number) {
		isLoadingDetail = true;
		try {
			const detail = await getSubmissionDetail(submissionId);
			selected = detail;
			drafts = Object.fromEntries(
				detail.stu_answers.map((answer) => [
					answer.id,
					{
						point: answer.point === null ? null : Number(answer.point),
						tutor_comment: answer.tutor_comment ?? ''
					}
				])
			);
		} catch (err) {
			showToast(getApiErrorMessage(err, 'Không mở được bài nộp.'), 'error');
		} finally {
			isLoadingDetail = false;
		}
	}

	async function saveGrade() {
		if (!selected || isSaving) return;
		if (!validateGrade()) return;

		const agreed = await confirmAction({
			title: 'Lưu điểm cho bài nộp này?',
			message: `Điểm và nhận xét sẽ được gửi tới ${selected.student.full_name}. Học sinh nhìn thấy ngay sau khi lưu.`,
			confirmLabel: 'Lưu điểm',
			tone: 'info'
		});
		if (!agreed) return;

		isSaving = true;
		try {
			const graded = await gradeSubmission(selected.id, buildGradePayload(drafts));
			selected = graded;
			showToast(
				graded.score === null
					? 'Đã lưu điểm, bài vẫn còn câu chưa chấm.'
					: `Đã chấm xong. Điểm tổng: ${graded.score}`,
				'success'
			);
			await invalidateAll();
		} catch (err) {
			showToast(getApiErrorMessage(err, 'Lưu điểm không thành công.'), 'error');
		} finally {
			isSaving = false;
		}
	}
</script>

<svelte:head>
	<title>Chấm bài</title>
</svelte:head>

<div class="grid h-full grid-cols-1 gap-6 px-8 py-8 lg:grid-cols-[320px_1fr]">
	<div
		class="flex min-h-0 flex-col rounded-2xl border border-slate-200/70 bg-white p-5 shadow-sm shadow-slate-200/50"
	>
		<div class="mb-4 flex shrink-0 items-center justify-between gap-2">
			<h2 class="text-sm font-semibold text-slate-800 font-heading">Bài đã nộp</h2>
			<span
				class="inline-flex shrink-0 items-center gap-1.5 rounded-full bg-amber-50 px-3 py-1.5 text-xs font-medium text-amber-700"
			>
				<ClipboardCheck class="h-3.5 w-3.5" />
				{pendingCount} chờ chấm
			</span>
		</div>

		<div class="min-h-0 flex-1 space-y-2 overflow-y-auto pr-1">
			{#each assignmentGroups as group (group.assignmentId)}
				<div class="overflow-hidden rounded-xl border border-slate-100">
					<button
						onclick={() => toggleGroup(group.assignmentId)}
						class="flex w-full items-center gap-2 p-3 text-left transition-colors hover:bg-slate-50"
					>
						<ChevronRight
							class={`h-4 w-4 shrink-0 text-slate-400 transition-transform ${openedGroupId === group.assignmentId ? 'rotate-90' : ''}`}
						/>
						<div class="min-w-0 flex-1">
							<p class="truncate text-sm font-medium text-slate-700">{group.title}</p>
							<p class="truncate text-xs text-slate-400">
								{group.chapterTitle} · {group.items.length} bài nộp
							</p>
						</div>
						{#if group.pendingCount > 0}
							<span
								class="shrink-0 rounded-full bg-amber-50 px-2 py-0.5 text-[11px] font-medium text-amber-700"
							>
								{group.pendingCount} chờ chấm
							</span>
						{:else}
							<span
								class="shrink-0 rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-emerald-700"
							>
								Đã chấm xong
							</span>
						{/if}
					</button>

					{#if openedGroupId === group.assignmentId}
						<div class="space-y-2 border-t border-slate-100 bg-slate-50/60 p-2">
							{#each group.items as submission (submission.id)}
								<button
									onclick={() => openSubmission(submission.id)}
									class={`w-full rounded-lg border bg-white p-3 text-left transition-colors ${selected?.id === submission.id ? 'border-brand-950' : 'border-slate-100 hover:bg-slate-50'}`}
								>
									<div class="flex items-center gap-3">
										<Avatar
											src={submission.student.avatar}
											name={submission.student.full_name}
											size="md"
										/>
										<div class="min-w-0 flex-1">
											<p class="truncate text-sm font-medium text-slate-700">
												{submission.student.full_name}
											</p>
											<p class="truncate text-xs text-slate-400">
												Nộp lúc {formatDate(submission.submitted_at)}
											</p>
										</div>
										{#if submission.score === null}
											<span
												class="shrink-0 rounded-full bg-amber-50 px-2 py-0.5 text-[11px] font-medium text-amber-700"
											>
												Chờ chấm
											</span>
										{:else}
											<span
												class="shrink-0 rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-semibold text-emerald-700"
											>
												{submission.score}
											</span>
										{/if}
									</div>
								</button>
							{/each}
						</div>
					{/if}
				</div>
			{/each}

			{#if assignmentGroups.length === 0}
				<p class="py-10 text-center text-sm text-slate-400">
					Chưa có học sinh nào nộp bài trong khóa này.
				</p>
			{/if}
		</div>
	</div>

	<div
		class="min-h-0 overflow-y-auto rounded-2xl border border-slate-200/70 bg-white p-6 shadow-sm shadow-slate-200/50"
	>
		{#if isLoadingDetail}
			<p class="py-20 text-center text-sm text-slate-400">Đang tải bài làm...</p>
		{:else if !selected}
			<p class="py-20 text-center text-sm text-slate-400">
				Chọn một bài nộp ở danh sách bên trái để chấm.
			</p>
		{:else}
			<div class="mb-5 flex flex-wrap items-center justify-between gap-3">
				<div>
					<h2 class="text-base font-bold text-slate-900 font-heading">
						{selected.assignment_title}
					</h2>
					<p class="mt-0.5 text-xs text-slate-400">
						{selected.student.full_name} · {selected.chapter_title} · nộp lúc {formatDate(
							selected.submitted_at
						)}
					</p>
				</div>
				<div class="flex items-center gap-2 text-xs text-slate-500">
					<Clock class="h-3.5 w-3.5" />
					Thang điểm {sumPoints(selected.stu_answers.map((item) => Number(item.question_point)))}
				</div>
			</div>

			<div class="space-y-4">
				{#each selected.stu_answers as answer, index (answer.id)}
					<div class="rounded-xl border border-slate-200 bg-white p-4">
						<p class="text-sm font-medium text-slate-700">
							Câu {index + 1}: {answer.question_content}
						</p>

						<div class="mt-2 space-y-1 text-xs">
							<p class="text-slate-500">
								Học sinh trả lời:
								<span class="font-medium text-slate-700">
									{answer.selected_answer ?? answer.answer_text ?? '(không trả lời)'}
								</span>
							</p>
							{#if answer.correct_answer}
								<p class="text-slate-500">
									Đáp án đúng:
									<span class="font-medium text-emerald-600">{answer.correct_answer}</span>
								</p>
							{/if}
						</div>

						{#if answer.question_type === 'ESSAY'}
							<div class="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-[150px_1fr]">
								<div class="flex items-center gap-1.5">
									<input
										type="number"
										step={POINT_STEP}
										min="0"
										max={answer.question_point}
										placeholder="Điểm"
										class="w-full min-w-0 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm outline-none focus:border-brand-300"
										bind:value={drafts[answer.id].point}
										oninput={() => clearGradeError(answer.id)}
										onkeydown={blockNonNumericKey}
										onblur={(event) => checkGradeOnBlur(answer.id, event.currentTarget)}
									/>
									<span class="shrink-0 text-xs text-slate-400">
										/ {answer.question_point}
									</span>
								</div>
								<input
									placeholder="Nhận xét cho học sinh"
									class="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm outline-none focus:border-brand-300"
									bind:value={drafts[answer.id].tutor_comment}
									oninput={() => clearGradeError(answer.id)}
								/>
							</div>
							<FieldError message={gradeErrors[answer.id]} />
						{:else}
							<p class="mt-3 flex items-center gap-1.5 text-xs font-medium">
								{#if answer.is_correct}
									<CheckCircle2 class="h-3.5 w-3.5 text-emerald-500" />
									<span class="text-emerald-600">Đúng · {answer.point} điểm</span>
								{:else}
									<span class="text-rose-500">Sai · {answer.point ?? 0} điểm</span>
								{/if}
							</p>
						{/if}
					</div>
				{/each}
			</div>

			<div class="mt-6 flex items-center justify-between border-t border-slate-100 pt-5">
				<p class="text-sm text-slate-500">
					Điểm tổng hiện tại:
					<span class="font-bold text-slate-800">{selected.score ?? 'chưa chấm xong'}</span>
				</p>
				<button
					onclick={saveGrade}
					disabled={isSaving}
					class="flex items-center gap-2 rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
				>
					<ClipboardCheck class="h-4 w-4" />
					Lưu điểm
				</button>
			</div>
		{/if}
	</div>
</div>
