<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import {
		createAssignment,
		createQuestion,
		deleteAssignment,
		deleteQuestion,
		publishAssignment,
		updateAssignment,
		updateQuestion
	} from '$lib/api/calledAPI';
	import { getApiErrorMessage } from '$lib/api/errors';
	import type { QuestionType, TutorAnswer, TutorQuestion } from '$lib/api/entities';
	import { showToast } from '$lib/stores/toast.svelte';
	import { confirmAction, notifyAction } from '$lib/stores/confirm.svelte';
	import FieldError from '$lib/components/FieldError.svelte';
	import {
		POINT_STEP,
		TOTAL_SCORE,
		distributePoints,
		isValidPointStep,
		sumPoints
	} from '$lib/utils/assignment';
	import {
		capError,
		ENTITY_CAPS,
		isNearCap,
		quotaLabel,
		FIELD_LIMITS,
		futureDateError,
		hasError,
		rangeError,
		textError,
		tooLongError,
		blockNonNumericKey
	} from '$lib/utils/validation';
	import { Check, ClipboardEdit, Globe, Lock, Pencil, Plus, Trash2, X } from 'lucide-svelte';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	let chapter = $derived(data.chapter);
	let assignment = $derived(data.assignment);
	let questions = $derived(data.questions);
	let isLocked = $derived(assignment?.is_published ?? false);
	let questionQuota = $derived(quotaLabel(questions.length, ENTITY_CAPS.questionsPerAssignment));
	let questionNearCap = $derived(
		isNearCap(questions.length, ENTITY_CAPS.questionsPerAssignment, 10)
	);

	const questionTypeLabel: Record<QuestionType, string> = {
		MULTIPLE_CHOICE: 'Trắc nghiệm',
		FILL_IN_BLANK: 'Điền khuyết',
		ESSAY: 'Tự luận'
	};

	function toDatetimeLocal(iso: string | null | undefined): string {
		if (!iso) return '';
		const d = new Date(iso);
		const pad = (n: number) => String(n).padStart(2, '0');
		return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
	}

	let form = $derived({ title: '', due_date: '', time_limit_minutes: '' });
	let isSavingAssignment = $state(false);
	let assignmentErrors = $state<Record<string, string>>({});

	function clearAssignmentError(field: string) {
		assignmentErrors = { ...assignmentErrors, [field]: '' };
	}

	function validateAssignment(): boolean {
		assignmentErrors = {
			title: textError(form.title, FIELD_LIMITS.title, 'Tiêu đề bài tập'),
			due_date: futureDateError(form.due_date, 'Hạn nộp'),
			time_limit_minutes: rangeError(
				form.time_limit_minutes,
				1,
				FIELD_LIMITS.timeLimitMinutes,
				'Thời gian làm bài'
			)
		};
		return !hasError(assignmentErrors);
	}

	$effect(() => {
		form = {
			title: data.assignment?.title ?? '',
			due_date: toDatetimeLocal(data.assignment?.due_date),
			time_limit_minutes: data.assignment?.time_limit_minutes
				? String(data.assignment.time_limit_minutes)
				: ''
		};
	});

	async function saveAssignment() {
		if (!chapter || isSavingAssignment || isLocked) return;
		if (!validateAssignment()) return;

		isSavingAssignment = true;
		try {
			const payload = {
				chapter: chapter.id,
				title: form.title.trim(),
				due_date: new Date(form.due_date).toISOString(),
				time_limit_minutes: form.time_limit_minutes ? Number(form.time_limit_minutes) : null
			};

			if (assignment) {
				await updateAssignment(assignment.id, payload);
				showToast('Đã cập nhật bài tập', 'success');
			} else {
				await createAssignment(payload);
				showToast('Đã tạo bài tập cho chương', 'success');
			}
			await invalidateAll();
		} catch (err) {
			showToast(getApiErrorMessage(err, 'Lưu bài tập không thành công.'), 'error');
		} finally {
			isSavingAssignment = false;
		}
	}

	async function confirmPublishAssignment() {
		if (!assignment) return;

		const agreed = await confirmAction({
			title: 'Công khai bài tập cho học sinh?',
			message: `Học sinh trong khóa sẽ làm được bài tập "${assignment.title}". Đã công khai thì không đưa về lại bản nháp được.`,
			confirmLabel: 'Công khai',
			tone: 'warning'
		});
		if (!agreed) return;

		try {
			await publishAssignment(assignment.id);
			showToast('Đã công khai bài tập', 'success');
			await invalidateAll();
		} catch (err) {
			await notifyAction({
				title: 'Chưa công khai được bài tập',
				message: getApiErrorMessage(err, 'Công khai bài tập không thành công.'),
				confirmLabel: 'Đã hiểu',
				tone: 'info'
			});
		}
	}

	async function removeAssignment() {
		if (!assignment || isLocked) return;
		const agreed = await confirmAction({
			title: 'Xoá bài tập của chương này?',
			message: `Bài tập "${assignment.title}" và toàn bộ câu hỏi bên trong sẽ bị xoá. Thao tác này không hoàn tác được.`,
			confirmLabel: 'Xoá bài tập',
			tone: 'danger'
		});
		if (!agreed) return;

		try {
			await deleteAssignment(assignment.id);
			showToast('Đã xoá bài tập', 'success');
			await invalidateAll();
		} catch (err) {
			showToast(getApiErrorMessage(err, 'Xoá bài tập không thành công.'), 'error');
		}
	}

	const emptyAnswers = (): TutorAnswer[] => [
		{ content: '', is_correct: true },
		{ content: '', is_correct: false }
	];

	let activeEditor = $state<number | 'new' | null>(null);
	let editingQuestionId = $derived(typeof activeEditor === 'number' ? activeEditor : null);
	let isAddingQuestion = $derived(activeEditor === 'new');
	let isSavingQuestion = $state(false);
	let questionErrors = $state<Record<string, string>>({});

	let questionForm = $state<{
		content: string;
		question_type: QuestionType;
		explanation: string;
		point: number | null;
		answers: TutorAnswer[];
	}>({
		content: '',
		question_type: 'MULTIPLE_CHOICE',
		explanation: '',
		point: null,
		answers: emptyAnswers()
	});

	let totalPoint = $derived(
		sumPoints(questions.filter((q) => q.point !== null).map((q) => Number(q.point)))
	);
	let unsetPointCount = $derived(questions.filter((question) => question.point === null).length);
	let isPointTotalValid = $derived(unsetPointCount === 0 && totalPoint === TOTAL_SCORE);
	let isSharingPoints = $state(false);

	let optionQuota = $derived(
		quotaLabel(questionForm.answers.length, ENTITY_CAPS.answersPerQuestion)
	);
	let optionNearCap = $derived(
		isNearCap(questionForm.answers.length, ENTITY_CAPS.answersPerQuestion, 1)
	);

	function clearQuestionError(field: string) {
		questionErrors = { ...questionErrors, [field]: '' };
	}

	function pointError(point: number | null): string {
		if (point === null || Number.isNaN(point)) return '';
		if (point < POINT_STEP) return `Điểm mỗi câu ít nhất là ${POINT_STEP}.`;
		if (point > TOTAL_SCORE) return `Điểm mỗi câu nhiều nhất là ${TOTAL_SCORE}.`;
		if (!isValidPointStep(point))
			return `Điểm phải là bội của ${POINT_STEP}, ví dụ 0.25, 0.5, 1.75.`;
		return '';
	}

	function checkPointOnBlur(event: FocusEvent & { currentTarget: HTMLInputElement }) {
		const message = event.currentTarget.validity.badInput
			? 'Điểm phải là số.'
			: pointError(questionForm.point);
		questionErrors = { ...questionErrors, point: message };
	}

	function describeDistribution(points: number[]): string {
		const countByPoint: Record<string, number> = {};
		for (const point of points) {
			countByPoint[point] = (countByPoint[point] ?? 0) + 1;
		}

		return Object.keys(countByPoint)
			.map(Number)
			.sort((a, b) => b - a)
			.map((point) => `${countByPoint[point]} câu ${point} điểm`)
			.join(', ');
	}

	async function sharePointsEvenly() {
		if (isLocked || isSharingPoints || questions.length === 0) return;

		const points = distributePoints(questions.length);

		const agreed = await confirmAction({
			title: 'Chia đều điểm cho cả đề?',
			message:
				`${questions.length} câu sẽ được chia thành: ${describeDistribution(points)}. ` +
				`Tổng ${sumPoints(points)} điểm. Điểm gia sư đã đặt tay cho từng câu sẽ bị ghi đè.`,
			confirmLabel: 'Lưu',
			cancelLabel: 'Hủy',
			tone: 'info'
		});
		if (!agreed) return;

		isSharingPoints = true;
		try {
			await Promise.all(
				questions.map((question, index) => updateQuestion(question.id, { point: points[index] }))
			);
			showToast('Đã chia đều điểm cho các câu hỏi', 'success');
			await invalidateAll();
		} catch (err) {
			showToast(getApiErrorMessage(err, 'Chia đều điểm không thành công.'), 'error');
		} finally {
			isSharingPoints = false;
		}
	}

	function validateQuestion(): boolean {
		questionErrors = {
			content: textError(questionForm.content, FIELD_LIMITS.questionContent, 'Nội dung câu hỏi'),
			explanation: tooLongError(
				questionForm.explanation,
				FIELD_LIMITS.explanation,
				'Lời giải chi tiết'
			)
		};

		questionErrors.point = pointError(questionForm.point);

		if (questionForm.question_type !== 'ESSAY') {
			const badIndex = questionForm.answers.findIndex(
				(answer) => textError(answer.content, FIELD_LIMITS.answerContent, 'Phương án') !== ''
			);
			if (badIndex !== -1) {
				questionErrors.answers = textError(
					questionForm.answers[badIndex].content,
					FIELD_LIMITS.answerContent,
					`Phương án ${badIndex + 1}`
				);
			}
		}

		return !hasError(questionErrors);
	}

	function closeEditor() {
		activeEditor = null;
		questionErrors = {};
	}

	function startAddQuestion() {
		if (isLocked) return;

		const capMessage = capError(
			questions.length,
			ENTITY_CAPS.questionsPerAssignment,
			'Mỗi bài tập chỉ có số câu hỏi'
		);
		if (capMessage) {
			showToast(capMessage, 'error');
			return;
		}

		questionForm = {
			content: '',
			question_type: 'MULTIPLE_CHOICE',
			explanation: '',
			point: null,
			answers: emptyAnswers()
		};
		questionErrors = {};
		activeEditor = 'new';
	}

	function startEditQuestion(question: TutorQuestion) {
		if (isLocked) return;

		questionForm = {
			content: question.content,
			question_type: question.question_type,
			explanation: question.explanation,
			point: question.point === null ? null : Number(question.point),
			answers: question.answers.length
				? question.answers.map((a) => ({ content: a.content, is_correct: a.is_correct }))
				: emptyAnswers()
		};
		questionErrors = {};
		activeEditor = question.id;
	}

	function onQuestionTypeChange() {
		if (questionForm.question_type === 'ESSAY') {
			questionForm.answers = [];
		} else if (questionForm.question_type === 'FILL_IN_BLANK') {
			questionForm.answers = [
				{ content: questionForm.answers[0]?.content ?? '', is_correct: true }
			];
		} else if (questionForm.answers.length < 2) {
			questionForm.answers = emptyAnswers();
		}
	}

	function addOption() {
		const capMessage = capError(
			questionForm.answers.length,
			ENTITY_CAPS.answersPerQuestion,
			'Mỗi câu hỏi chỉ có số phương án'
		);
		if (capMessage) {
			questionErrors = { ...questionErrors, answers: capMessage };
			return;
		}

		questionForm.answers = [...questionForm.answers, { content: '', is_correct: false }];
	}

	function removeOption(index: number) {
		questionForm.answers = questionForm.answers.filter((_, i) => i !== index);
	}

	function markCorrect(index: number) {
		questionForm.answers = questionForm.answers.map((answer, i) => ({
			...answer,
			is_correct: i === index
		}));
	}

	async function saveQuestion() {
		if (!assignment || isSavingQuestion || isLocked) return;
		if (!validateQuestion()) return;

		isSavingQuestion = true;
		try {
			const payload = {
				content: questionForm.content.trim(),
				question_type: questionForm.question_type,
				explanation: questionForm.explanation.trim(),
				point: questionForm.point,
				answers: questionForm.answers
					.filter((a) => a.content.trim() !== '')
					.map((a) => ({ content: a.content.trim(), is_correct: a.is_correct }))
			};

			if (editingQuestionId) {
				await updateQuestion(editingQuestionId, payload);
				showToast('Đã cập nhật câu hỏi', 'success');
			} else {
				await createQuestion({ ...payload, assignment: assignment.id });
				showToast('Đã thêm câu hỏi', 'success');
			}
			closeEditor();
			await invalidateAll();
		} catch (err) {
			showToast(getApiErrorMessage(err, 'Lưu câu hỏi không thành công.'), 'error');
		} finally {
			isSavingQuestion = false;
		}
	}

	async function removeQuestion(question: TutorQuestion) {
		if (isLocked) return;

		const agreed = await confirmAction({
			title: 'Xoá câu hỏi này?',
			message: `Câu hỏi "${question.content}" sẽ bị xoá khỏi bài tập. Thao tác này không hoàn tác được.`,
			confirmLabel: 'Xoá câu hỏi',
			tone: 'danger'
		});
		if (!agreed) return;

		try {
			await deleteQuestion(question.id);
			showToast('Đã xoá câu hỏi', 'success');
			await invalidateAll();
		} catch (err) {
			showToast(getApiErrorMessage(err, 'Xoá câu hỏi không thành công.'), 'error');
		}
	}
</script>

<svelte:head>
	<title>Soạn bài tập</title>
</svelte:head>

<div class="px-8 py-8">
	<div class="mx-auto max-w-4xl space-y-6">
		{#if !chapter}
			<div class="py-20 text-center text-slate-400">
				<p>Khóa học chưa có chương nào. Hãy tạo chương trước khi soạn bài tập.</p>
			</div>
		{:else}
			<div
				class="rounded-2xl border border-slate-200/70 bg-white p-6 shadow-sm shadow-slate-200/50"
			>
				<div class="mb-4 flex items-center justify-between">
					<div class="min-w-0">
						<p class="truncate text-xs text-slate-400">{chapter.title}</p>
						<h2 class="text-sm font-semibold text-slate-800 font-heading">
							{assignment ? 'Thông tin bài tập' : 'Tạo bài tập cho chương này'}
						</h2>
					</div>
					{#if assignment}
						<div class="flex items-center gap-2">
							{#if assignment.is_published}
								<span
									class="rounded-full bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-600"
								>
									Đã công khai
								</span>
							{:else}
								<button
									onclick={confirmPublishAssignment}
									class="flex items-center gap-1.5 rounded-xl border border-emerald-200 px-3 py-1.5 text-xs font-medium text-emerald-600 hover:bg-emerald-50"
								>
									<Globe class="h-3.5 w-3.5" />
									Công khai bài tập
								</button>
								<button
									onclick={removeAssignment}
									class="flex items-center gap-1.5 rounded-xl border border-rose-200 px-3 py-1.5 text-xs font-medium text-rose-600 hover:bg-rose-50"
								>
									<Trash2 class="h-3.5 w-3.5" />
									Xoá bài tập
								</button>
							{/if}
						</div>
					{/if}
				</div>

				{#if isLocked}
					<div
						class="mb-4 flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3"
					>
						<Lock class="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
						<p class="text-xs leading-relaxed text-amber-800">
							Bài tập đã công khai nên bị khoá: không sửa thông tin, không thêm sửa xoá câu hỏi và
							không xoá được bài tập. Học sinh có thể đang làm bài, sửa lúc này sẽ làm sai điểm của
							những bài đã nộp.
						</p>
					</div>
				{/if}

				<div class="space-y-3">
					<div>
						<input
							disabled={isLocked}
							aria-invalid={assignmentErrors.title ? 'true' : undefined}
							oninput={() => clearAssignmentError('title')}
							class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-300 disabled:bg-slate-50 disabled:text-slate-400 aria-invalid:border-rose-400"
							placeholder="Tiêu đề bài tập"
							bind:value={form.title}
						/>
						<FieldError message={assignmentErrors.title} />
					</div>
					<div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
						<label class="block">
							<span class="mb-1 block text-xs font-medium text-slate-500">Hạn nộp</span>
							<input
								type="datetime-local"
								disabled={isLocked}
								aria-invalid={assignmentErrors.due_date ? 'true' : undefined}
								oninput={() => clearAssignmentError('due_date')}
								class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-300 disabled:bg-slate-50 disabled:text-slate-400 aria-invalid:border-rose-400"
								bind:value={form.due_date}
							/>
							<FieldError message={assignmentErrors.due_date} />
						</label>
						<label class="block">
							<span class="mb-1 block text-xs font-medium text-slate-500">
								Thời gian làm bài (phút, để trống nếu không giới hạn)
							</span>
							<input
								type="number"
								min="1"
								disabled={isLocked}
								aria-invalid={assignmentErrors.time_limit_minutes ? 'true' : undefined}
								oninput={() => clearAssignmentError('time_limit_minutes')}
								class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-300 disabled:bg-slate-50 disabled:text-slate-400 aria-invalid:border-rose-400"
								bind:value={form.time_limit_minutes}
							/>
							<FieldError message={assignmentErrors.time_limit_minutes} />
						</label>
					</div>
					{#if !isLocked}
						<div class="flex justify-end">
							<button
								onclick={saveAssignment}
								disabled={isSavingAssignment}
								class="flex items-center gap-1.5 rounded-xl bg-brand-600 px-4 py-2 text-xs font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
							>
								<ClipboardEdit class="h-3.5 w-3.5" />
								{assignment ? 'Lưu thay đổi' : 'Tạo bài tập'}
							</button>
						</div>
					{/if}
				</div>
			</div>

			{#if assignment}
				<div
					class="rounded-2xl border border-slate-200/70 bg-white p-6 shadow-sm shadow-slate-200/50"
				>
					<div class="mb-4 flex items-center justify-between">
						<h2 class="text-sm font-semibold text-slate-800 font-heading">
							Câu hỏi
							<span
								class={questionNearCap
									? 'font-normal text-amber-600'
									: 'font-normal text-slate-400'}
							>
								{questionQuota}
							</span>
						</h2>
						{#if !isLocked}
							<div class="flex items-center gap-2">
								<span
									class={`text-xs font-semibold ${
										isPointTotalValid ? 'text-emerald-600' : 'text-amber-600'
									}`}
								>
									Tổng {totalPoint}/{TOTAL_SCORE} điểm
								</span>
								{#if questions.length > 0}
									<button
										onclick={sharePointsEvenly}
										disabled={isSharingPoints}
										class="rounded-xl border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-50 disabled:opacity-40"
									>
										Chia đều điểm
									</button>
								{/if}
								<button
									onclick={startAddQuestion}
									class="flex items-center gap-1.5 rounded-xl bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand-700"
								>
									<Plus class="h-3.5 w-3.5" />
									Thêm câu hỏi
								</button>
							</div>
						{/if}
					</div>

					{#if !isLocked && questions.length > 0 && !isPointTotalValid}
						<p class="mb-3 rounded-xl bg-amber-50 px-3 py-2 text-xs font-medium text-amber-700">
							{#if unsetPointCount > 0}
								Còn {unsetPointCount} câu chưa đặt điểm.
							{:else}
								Tổng điểm các câu phải bằng {TOTAL_SCORE} mới được phép công khai bài tập.
							{/if}
						</p>
					{/if}

					{#snippet questionEditor()}
						<div class="mb-4 space-y-3 rounded-xl border border-brand-300 bg-slate-50 p-4">
							<div>
								<textarea
									rows="2"
									aria-invalid={questionErrors.content ? 'true' : undefined}
									oninput={() => clearQuestionError('content')}
									class="w-full resize-none rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-300 aria-invalid:border-rose-400"
									placeholder="Nội dung câu hỏi"
									bind:value={questionForm.content}></textarea>
								<FieldError message={questionErrors.content} />
							</div>

							<div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
								<select
									class="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-300"
									bind:value={questionForm.question_type}
									onchange={onQuestionTypeChange}
								>
									<option value="MULTIPLE_CHOICE">Trắc nghiệm</option>
									<option value="FILL_IN_BLANK">Điền khuyết</option>
									<option value="ESSAY">Tự luận</option>
								</select>
								<div>
									<input
										aria-invalid={questionErrors.explanation ? 'true' : undefined}
										oninput={() => clearQuestionError('explanation')}
										class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-300 aria-invalid:border-rose-400"
										placeholder="Lời giải chi tiết"
										bind:value={questionForm.explanation}
									/>
									<FieldError message={questionErrors.explanation} />
								</div>
							</div>

							<div class="sm:w-1/2">
								<div class="flex items-center gap-2">
									<input
										type="number"
										step={POINT_STEP}
										min={POINT_STEP}
										max={TOTAL_SCORE}
										aria-invalid={questionErrors.point ? 'true' : undefined}
										oninput={() => clearQuestionError('point')}
										onkeydown={blockNonNumericKey}
										onblur={checkPointOnBlur}
										class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-300 aria-invalid:border-rose-400"
										placeholder="Điểm của câu hỏi (để trống nếu chưa quyết)"
										bind:value={questionForm.point}
									/>
									<span class="shrink-0 text-xs text-slate-400">điểm</span>
								</div>
								<FieldError message={questionErrors.point} />
							</div>

							{#if questionForm.question_type === 'ESSAY'}
								<p class="text-xs text-slate-500">
									Câu tự luận không có phương án; gia sư sẽ chấm tay ở mục Chấm bài.
								</p>
							{:else}
								<div class="space-y-2">
									<p class="text-xs font-medium text-slate-500">
										{questionForm.question_type === 'MULTIPLE_CHOICE'
											? 'Phương án (chọn 1 đáp án đúng)'
											: 'Đáp án đúng'}
										{#if questionForm.question_type === 'MULTIPLE_CHOICE'}
											<span class={optionNearCap ? 'text-amber-600' : 'text-slate-400'}>
												· {optionQuota}
											</span>
										{/if}
									</p>
									{#each questionForm.answers as answer, index (index)}
										<div class="flex items-center gap-2">
											{#if questionForm.question_type === 'MULTIPLE_CHOICE'}
												<button
													onclick={() => markCorrect(index)}
													class={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-2 ${
														answer.is_correct
															? 'border-emerald-500 bg-emerald-500 text-white'
															: 'border-slate-300 text-transparent'
													}`}
													aria-label="Đánh dấu đáp án đúng"
												>
													<Check class="h-3 w-3" />
												</button>
											{/if}
											<input
												oninput={() => clearQuestionError('answers')}
												class="min-w-0 flex-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm outline-none focus:border-brand-300"
												placeholder={questionForm.question_type === 'MULTIPLE_CHOICE'
													? `Phương án ${index + 1}`
													: 'Đáp án đúng'}
												bind:value={answer.content}
											/>
											{#if questionForm.question_type === 'MULTIPLE_CHOICE' && questionForm.answers.length > 2}
												<button
													onclick={() => removeOption(index)}
													class="rounded-lg p-1.5 text-slate-400 hover:bg-rose-50 hover:text-rose-500"
													aria-label="Xoá phương án"
												>
													<X class="h-4 w-4" />
												</button>
											{/if}
										</div>
									{/each}
									<FieldError message={questionErrors.answers} />

									{#if questionForm.question_type === 'MULTIPLE_CHOICE'}
										<button
											onclick={addOption}
											class="flex items-center gap-1.5 text-xs font-medium text-slate-500 hover:text-brand-600"
										>
											<Plus class="h-3 w-3" />
											Thêm phương án
										</button>
									{/if}
								</div>
							{/if}

							<div class="flex justify-end gap-2">
								<button
									onclick={closeEditor}
									class="rounded-lg bg-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-300"
								>
									Huỷ
								</button>
								<button
									onclick={saveQuestion}
									disabled={isSavingQuestion}
									class="rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
								>
									{editingQuestionId ? 'Lưu câu hỏi' : 'Thêm câu hỏi'}
								</button>
							</div>
						</div>
					{/snippet}

					{#if isAddingQuestion}
						{@render questionEditor()}
					{/if}

					<div class="space-y-2">
						{#each questions as question, index (question.id)}
							{#if editingQuestionId === question.id}
								{@render questionEditor()}
							{:else}
								<div class="rounded-xl border border-slate-200 bg-white p-4">
									<div class="flex items-start justify-between gap-3">
										<div class="min-w-0">
											<p class="text-sm font-medium text-slate-700">
												Câu {index + 1}: {question.content}
											</p>
											<p class="mt-1 text-xs text-slate-400">
												{questionTypeLabel[question.question_type]}
												{#if question.point === null}
													· <span class="font-medium text-amber-600">chưa đặt điểm</span>
												{:else}
													· {question.point} điểm
												{/if}
												{#if question.answers.length > 0}
													· {question.answers.length} phương án
												{/if}
											</p>
											{#if question.answers.length > 0}
												<div class="mt-2 space-y-1">
													{#each question.answers as answer (answer.id ?? answer.content)}
														<p
															class={`text-xs ${answer.is_correct ? 'font-semibold text-emerald-600' : 'text-slate-500'}`}
														>
															{answer.is_correct ? '✓' : '·'}
															{answer.content}
														</p>
													{/each}
												</div>
											{/if}
										</div>
										{#if !isLocked}
											<div class="flex shrink-0 items-center gap-1">
												<button
													onclick={() => startEditQuestion(question)}
													class="rounded-lg p-1.5 text-slate-400 hover:bg-white hover:text-slate-600"
													aria-label="Sửa câu hỏi"
												>
													<Pencil class="h-4 w-4" />
												</button>
												<button
													onclick={() => removeQuestion(question)}
													class="rounded-lg p-1.5 text-slate-400 hover:bg-rose-50 hover:text-rose-500"
													aria-label="Xoá câu hỏi"
												>
													<Trash2 class="h-4 w-4" />
												</button>
											</div>
										{/if}
									</div>
								</div>
							{/if}
						{/each}

						{#if questions.length === 0 && !isAddingQuestion}
							<p class="py-6 text-center text-sm text-slate-400">
								Bài tập chưa có câu hỏi nào. Học sinh chỉ nộp được khi có ít nhất 1 câu.
							</p>
						{/if}
					</div>
				</div>
			{:else}
				<p class="text-center text-sm text-slate-400">
					Tạo bài tập trước rồi mới soạn được câu hỏi.
				</p>
			{/if}
		{/if}
	</div>
</div>
