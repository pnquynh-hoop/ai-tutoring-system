<script lang="ts">
	import { goto, invalidateAll } from '$app/navigation';
	import { getSubmissionDetail, gradeSubmission } from '$lib/api/calledAPI';
	import { getApiErrorMessage } from '$lib/api/errors';
	import type { SubmissionDetail } from '$lib/api/entities';
	import { buildGradePayload } from '$lib/utils/assignment';
	import Avatar from '$lib/components/Avatar.svelte';
	import { showToast } from '$lib/stores/toast.svelte';
	import { ArrowLeft, CheckCircle2, ClipboardCheck, Clock } from 'lucide-svelte';
	import type { PageProps } from './$types';

	// ============================================================
	// Chấm bài: câu trắc nghiệm/điền khuyết đã được backend chấm tự động khi nộp,
	// gia sư chỉ nhập điểm cho câu tự luận (point === null), sau đó backend tính
	// lại điểm tổng của Submission.
	// ============================================================

	let { data }: PageProps = $props();

	let courseId = $derived(data.courseId);
	let submissions = $derived(data.submissions);

	let selected = $state<SubmissionDetail | null>(null);
	let isLoadingDetail = $state(false);
	let isSaving = $state(false);
	/** Điểm và nhận xét gia sư đang nhập, khóa theo id của StudentAnswer. */
	let drafts = $state<Record<number, { point: string; tutor_comment: string }>>({});

	let pendingCount = $derived(submissions.filter((s) => s.score === null).length);

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
					{ point: answer.point ?? '', tutor_comment: answer.tutor_comment ?? '' }
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
	<link rel="preconnect" href="https://fonts.googleapis.com" />
	<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="" />
	<link
		href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Sora:wght@600;700;800&display=swap"
		rel="stylesheet"
	/>
	<title>Chấm bài</title>
</svelte:head>

<div class="min-h-screen bg-[#F4F5F8]" style="font-family:'Inter',sans-serif;">
	<header
		class="flex items-center justify-between border-b border-slate-200/70 bg-white/80 px-8 py-4 backdrop-blur"
	>
		<button
			onclick={() => goto(`/course-mgt/${courseId}`)}
			class="flex items-center gap-2 rounded-full bg-slate-100 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-200"
		>
			<ArrowLeft class="h-4 w-4" />
			Về cây khóa học
		</button>
		<div
			class="inline-flex items-center gap-1.5 rounded-full bg-amber-50 px-3 py-1.5 text-xs font-medium text-amber-700"
		>
			<ClipboardCheck class="h-3.5 w-3.5" />
			{pendingCount} bài chờ chấm
		</div>
	</header>

	<main class="grid grid-cols-1 gap-6 px-8 py-8 lg:grid-cols-[360px_1fr]">
		<!-- DANH SÁCH BÀI NỘP -->
		<div class="rounded-2xl border border-slate-200/70 bg-white p-5 shadow-sm shadow-slate-200/50">
			<h2 class="mb-4 text-sm font-semibold text-slate-800" style="font-family:'Sora',sans-serif;">
				Bài đã nộp - {data.course.name}
			</h2>

			<div class="space-y-2">
				{#each submissions as submission (submission.id)}
					<button
						onclick={() => openSubmission(submission.id)}
						class={`w-full rounded-xl border p-3 text-left transition-colors ${
							selected?.id === submission.id
								? 'border-[#0C1550] bg-slate-50'
								: 'border-slate-100 hover:bg-slate-50'
						}`}
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
									{submission.assignment_title} · {formatDate(submission.submitted_at)}
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

				{#if submissions.length === 0}
					<p class="py-10 text-center text-sm text-slate-400">
						Chưa có học sinh nào nộp bài trong khóa này.
					</p>
				{/if}
			</div>
		</div>

		<!-- CHI TIẾT BÀI LÀM -->
		<div class="rounded-2xl border border-slate-200/70 bg-white p-6 shadow-sm shadow-slate-200/50">
			{#if isLoadingDetail}
				<p class="py-20 text-center text-sm text-slate-400">Đang tải bài làm...</p>
			{:else if !selected}
				<p class="py-20 text-center text-sm text-slate-400">
					Chọn một bài nộp ở danh sách bên trái để chấm.
				</p>
			{:else}
				<div class="mb-5 flex flex-wrap items-center justify-between gap-3">
					<div>
						<h2 class="text-base font-bold text-slate-900" style="font-family:'Sora',sans-serif;">
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
						Tối đa {selected.point_per_question} điểm/câu
					</div>
				</div>

				<div class="space-y-4">
					{#each selected.stu_answers as answer, index (answer.id)}
						<div class="rounded-xl border border-slate-100 bg-slate-50 p-4">
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
								<div class="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-[120px_1fr]">
									<input
										type="number"
										step="0.25"
										min="0"
										max={selected.point_per_question}
										placeholder="Điểm"
										class="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm outline-none focus:border-indigo-300"
										bind:value={drafts[answer.id].point}
									/>
									<input
										placeholder="Nhận xét cho học sinh"
										class="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm outline-none focus:border-indigo-300"
										bind:value={drafts[answer.id].tutor_comment}
									/>
								</div>
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
						class="flex items-center gap-2 rounded-xl bg-[#0C1550] px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
					>
						<ClipboardCheck class="h-4 w-4" />
						Lưu điểm
					</button>
				</div>
			{/if}
		</div>
	</main>
</div>
