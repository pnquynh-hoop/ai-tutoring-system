<script lang="ts">
	import { goto, invalidateAll } from '$app/navigation';
	import {
		createAssignment,
		createQuestion,
		deleteAssignment,
		deleteQuestion,
		updateAssignment,
		updateQuestion
	} from '$lib/api/calledAPI';
	import { getApiErrorMessage } from '$lib/api/errors';
	import type { QuestionType, TutorAnswer, TutorQuestion } from '$lib/api/entities';
	import { showToast } from '$lib/stores/toast.svelte';
	import { ArrowLeft, Check, ClipboardEdit, Pencil, Plus, Trash2, X } from 'lucide-svelte';
	import type { PageProps } from './$types';

	// ============================================================
	// Soạn bài tập cho MỘT CHƯƠNG (Assignment 1-1 Chapter theo model backend),
	// kèm bộ câu hỏi: Question 1-N Answer.
	// ============================================================

	let { data }: PageProps = $props();

	let courseId = $derived(data.courseId);
	let chapter = $derived(data.chapter);
	let assignment = $derived(data.assignment);
	let questions = $derived(data.questions);

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

	// --- Form thông tin bài tập ---
	let form = $state({ title: '', due_date: '', time_limit_minutes: '' });
	let isSavingAssignment = $state(false);

	$effect(() => {
		form = {
			title: data.assignment?.title ?? '',
			due_date: toDatetimeLocal(data.assignment?.due_date),
			time_limit_minutes: data.assignment?.time_limit_minutes
				? String(data.assignment.time_limit_minutes)
				: ''
		};
	});

	function goBack() {
		goto(`/course-mgt/${courseId}`);
	}

	function selectChapter(chapterId: number) {
		goto(`/course-mgt/${courseId}/assignment-mgt?chapter=${chapterId}`, {
			invalidateAll: true
		});
	}

	async function saveAssignment() {
		if (!chapter || isSavingAssignment) return;
		if (!form.title.trim()) {
			showToast('Vui lòng nhập tiêu đề bài tập', 'error');
			return;
		}
		if (!form.due_date) {
			showToast('Vui lòng chọn hạn nộp', 'error');
			return;
		}

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

	async function removeAssignment() {
		if (!assignment) return;
		if (!window.confirm('Xoá bài tập của chương này? Toàn bộ câu hỏi cũng sẽ bị xoá.')) return;

		try {
			await deleteAssignment(assignment.id);
			showToast('Đã xoá bài tập', 'success');
			await invalidateAll();
		} catch (err) {
			showToast(getApiErrorMessage(err, 'Xoá bài tập không thành công.'), 'error');
		}
	}

	// --- Soạn câu hỏi ---
	const emptyAnswers = (): TutorAnswer[] => [
		{ content: '', is_correct: true },
		{ content: '', is_correct: false }
	];

	let editingQuestionId = $state<number | null>(null);
	let showQuestionForm = $state(false);
	let isSavingQuestion = $state(false);
	let questionForm = $state<{
		content: string;
		question_type: QuestionType;
		explanation: string;
		answers: TutorAnswer[];
	}>({
		content: '',
		question_type: 'MULTIPLE_CHOICE',
		explanation: '',
		answers: emptyAnswers()
	});

	function startAddQuestion() {
		editingQuestionId = null;
		questionForm = {
			content: '',
			question_type: 'MULTIPLE_CHOICE',
			explanation: '',
			answers: emptyAnswers()
		};
		showQuestionForm = true;
	}

	function startEditQuestion(question: TutorQuestion) {
		editingQuestionId = question.id;
		questionForm = {
			content: question.content,
			question_type: question.question_type,
			explanation: question.explanation,
			answers: question.answers.length
				? question.answers.map((a) => ({ content: a.content, is_correct: a.is_correct }))
				: emptyAnswers()
		};
		showQuestionForm = true;
	}

	/** Đổi loại câu hỏi thì bộ đáp án phải theo ràng buộc của backend. */
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
		questionForm.answers = [...questionForm.answers, { content: '', is_correct: false }];
	}

	function removeOption(index: number) {
		questionForm.answers = questionForm.answers.filter((_, i) => i !== index);
	}

	/** Trắc nghiệm chỉ được đúng 1 đáp án đúng - khớp validate ở backend. */
	function markCorrect(index: number) {
		questionForm.answers = questionForm.answers.map((answer, i) => ({
			...answer,
			is_correct: i === index
		}));
	}

	async function saveQuestion() {
		if (!assignment || isSavingQuestion) return;
		if (!questionForm.content.trim()) {
			showToast('Vui lòng nhập nội dung câu hỏi', 'error');
			return;
		}

		isSavingQuestion = true;
		try {
			const payload = {
				assignment: assignment.id,
				content: questionForm.content.trim(),
				question_type: questionForm.question_type,
				explanation: questionForm.explanation.trim(),
				answers: questionForm.answers
					.filter((a) => a.content.trim() !== '')
					.map((a) => ({ content: a.content.trim(), is_correct: a.is_correct }))
			};

			if (editingQuestionId) {
				await updateQuestion(editingQuestionId, payload);
				showToast('Đã cập nhật câu hỏi', 'success');
			} else {
				await createQuestion(payload);
				showToast('Đã thêm câu hỏi', 'success');
			}
			showQuestionForm = false;
			await invalidateAll();
		} catch (err) {
			showToast(getApiErrorMessage(err, 'Lưu câu hỏi không thành công.'), 'error');
		} finally {
			isSavingQuestion = false;
		}
	}

	async function removeQuestion(question: TutorQuestion) {
		if (!window.confirm('Xoá câu hỏi này?')) return;
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
	<link rel="preconnect" href="https://fonts.googleapis.com" />
	<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="" />
	<link
		href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Sora:wght@600;700;800&display=swap"
		rel="stylesheet"
	/>
	<title>Soạn bài tập</title>
</svelte:head>

<div class="min-h-screen bg-[#F4F5F8]" style="font-family:'Inter',sans-serif;">
	<header
		class="flex items-center justify-between border-b border-slate-200/70 bg-white/80 px-8 py-4 backdrop-blur"
	>
		<button
			onclick={goBack}
			class="flex items-center gap-2 rounded-full bg-slate-100 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-200"
		>
			<ArrowLeft class="h-4 w-4" />
			Về cây khóa học
		</button>
	</header>

	<main class="px-8 py-8">
		<div class="mx-auto max-w-4xl space-y-6">
			<!-- CHỌN CHƯƠNG: bài tập luôn thuộc về một chương -->
			<div
				class="rounded-2xl border border-slate-200/70 bg-white p-6 shadow-sm shadow-slate-200/50"
			>
				<h2
					class="mb-3 text-sm font-semibold text-slate-800"
					style="font-family:'Sora',sans-serif;"
				>
					Chương của bài tập
				</h2>
				<div class="flex flex-wrap gap-2">
					{#each data.tree.chapters as ch (ch.id)}
						<button
							onclick={() => selectChapter(ch.id)}
							class={`rounded-xl border px-3 py-1.5 text-xs font-medium transition-colors ${
								chapter?.id === ch.id
									? 'border-[#0C1550] bg-[#0C1550] text-white'
									: 'border-slate-200 text-slate-600 hover:bg-slate-50'
							}`}
						>
							{ch.title}
							{#if ch.assignment !== null}
								<span class="ml-1 opacity-70">· có BT</span>
							{/if}
						</button>
					{/each}
				</div>
			</div>

			{#if !chapter}
				<div class="py-20 text-center text-slate-400">
					<p>Khóa học chưa có chương nào. Hãy tạo chương trước khi soạn bài tập.</p>
				</div>
			{:else}
				<!-- THÔNG TIN BÀI TẬP -->
				<div
					class="rounded-2xl border border-slate-200/70 bg-white p-6 shadow-sm shadow-slate-200/50"
				>
					<div class="mb-4 flex items-center justify-between">
						<h2 class="text-sm font-semibold text-slate-800" style="font-family:'Sora',sans-serif;">
							{assignment ? 'Thông tin bài tập' : 'Tạo bài tập cho chương này'}
						</h2>
						{#if assignment}
							<button
								onclick={removeAssignment}
								class="flex items-center gap-1.5 rounded-xl border border-rose-200 px-3 py-1.5 text-xs font-medium text-rose-600 hover:bg-rose-50"
							>
								<Trash2 class="h-3.5 w-3.5" />
								Xoá bài tập
							</button>
						{/if}
					</div>

					<div class="space-y-3">
						<input
							class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-indigo-300"
							placeholder="Tiêu đề bài tập"
							bind:value={form.title}
						/>
						<div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
							<label class="block">
								<span class="mb-1 block text-xs font-medium text-slate-500">Hạn nộp</span>
								<input
									type="datetime-local"
									class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-indigo-300"
									bind:value={form.due_date}
								/>
							</label>
							<label class="block">
								<span class="mb-1 block text-xs font-medium text-slate-500">
									Thời gian làm bài (phút, để trống nếu không giới hạn)
								</span>
								<input
									type="number"
									min="1"
									class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-indigo-300"
									bind:value={form.time_limit_minutes}
								/>
							</label>
						</div>
						<div class="flex justify-end">
							<button
								onclick={saveAssignment}
								disabled={isSavingAssignment}
								class="flex items-center gap-1.5 rounded-xl bg-[#0C1550] px-4 py-2 text-xs font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
							>
								<ClipboardEdit class="h-3.5 w-3.5" />
								{assignment ? 'Lưu thay đổi' : 'Tạo bài tập'}
							</button>
						</div>
					</div>
				</div>

				<!-- CÂU HỎI -->
				{#if assignment}
					<div
						class="rounded-2xl border border-slate-200/70 bg-white p-6 shadow-sm shadow-slate-200/50"
					>
						<div class="mb-4 flex items-center justify-between">
							<h2
								class="text-sm font-semibold text-slate-800"
								style="font-family:'Sora',sans-serif;"
							>
								Câu hỏi ({questions.length})
							</h2>
							<button
								onclick={startAddQuestion}
								class="flex items-center gap-1.5 rounded-xl bg-[#0C1550] px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-700"
							>
								<Plus class="h-3.5 w-3.5" />
								Thêm câu hỏi
							</button>
						</div>

						{#if showQuestionForm}
							<div class="mb-4 space-y-3 rounded-xl border border-slate-200 bg-slate-50 p-4">
								<textarea
									rows="2"
									class="w-full resize-none rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-indigo-300"
									placeholder="Nội dung câu hỏi"
									bind:value={questionForm.content}></textarea>

								<div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
									<select
										class="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-indigo-300"
										bind:value={questionForm.question_type}
										onchange={onQuestionTypeChange}
									>
										<option value="MULTIPLE_CHOICE">Trắc nghiệm</option>
										<option value="FILL_IN_BLANK">Điền khuyết</option>
										<option value="ESSAY">Tự luận</option>
									</select>
									<input
										class="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-indigo-300"
										placeholder="Lời giải chi tiết"
										bind:value={questionForm.explanation}
									/>
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
													class="min-w-0 flex-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm outline-none focus:border-indigo-300"
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

										{#if questionForm.question_type === 'MULTIPLE_CHOICE'}
											<button
												onclick={addOption}
												class="flex items-center gap-1.5 text-xs font-medium text-slate-500 hover:text-indigo-600"
											>
												<Plus class="h-3 w-3" />
												Thêm phương án
											</button>
										{/if}
									</div>
								{/if}

								<div class="flex justify-end gap-2">
									<button
										onclick={() => (showQuestionForm = false)}
										class="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-white"
									>
										Huỷ
									</button>
									<button
										onclick={saveQuestion}
										disabled={isSavingQuestion}
										class="rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
									>
										{editingQuestionId ? 'Lưu câu hỏi' : 'Thêm câu hỏi'}
									</button>
								</div>
							</div>
						{/if}

						<div class="space-y-2">
							{#each questions as question, index (question.id)}
								<div class="rounded-xl border border-slate-100 bg-slate-50 p-4">
									<div class="flex items-start justify-between gap-3">
										<div class="min-w-0">
											<p class="text-sm font-medium text-slate-700">
												Câu {index + 1}: {question.content}
											</p>
											<p class="mt-1 text-xs text-slate-400">
												{questionTypeLabel[question.question_type]}
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
									</div>
								</div>
							{/each}

							{#if questions.length === 0 && !showQuestionForm}
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
	</main>
</div>
