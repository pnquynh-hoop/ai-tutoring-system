<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { Home, ChevronLeft, ChevronRight, Check } from 'lucide-svelte';
	import QuizSidebar from '$lib/components/QuizSidebar.svelte';
	import type { PageProps } from './$types';
	import type { Question, UserAnswer } from '$lib/api/entities';
	import { submitAssignment } from '$lib/api/calledAPI';
	import { getApiErrorMessage } from '$lib/api/errors';
	import { buildAnswerPayload, remainingSeconds } from '$lib/utils/assignment';
	import { showToast } from '$lib/stores/toast.svelte';

	let { data }: PageProps = $props();
	let questions: Question[] = $derived(data.questions);

	let currentIndex = $state(0);

	let userAnswers = $state<Record<number, UserAnswer>>({});

	let currentQuestion = $derived(questions[currentIndex]);
	let currentAnswer = $derived(userAnswers[currentQuestion?.id]);

	// Thời gian còn lại tính từ deadline của server, không tính lại từ đầu ở client
	// nên tải lại trang giữa chừng vẫn ra đúng số giây còn lại.
	let durationSeconds = $derived(remainingSeconds(data.attempt.deadline));

	let isSubmitting = $state(false);

	let answeredCount = $derived(
		questions.filter((q) => {
			const ans = userAnswers[q.id];
			if (!ans) return false;
			if (ans.type === 'MULTIPLE_CHOICE') return ans.answerId !== undefined;
			return ans.text.trim().length > 0;
		}).length
	);

	function selectAnswer(answerId: number) {
		userAnswers[currentQuestion.id] = { type: 'MULTIPLE_CHOICE', answerId };
	}

	function updateTextAnswer(text: string) {
		userAnswers[currentQuestion.id] = {
			type: currentQuestion.question_type as 'FILL_IN_BLANK' | 'ESSAY',
			text
		};
	}

	function goTo(index: number) {
		if (index >= 0 && index < questions.length) currentIndex = index;
	}

	async function handleSubmit(auto = false) {
		if (isSubmitting) return;
		if (!auto && answeredCount < questions.length) {
			const remaining = questions.length - answeredCount;
			if (!window.confirm(`Còn ${remaining} câu chưa trả lời. Vẫn nộp bài?`)) return;
		}

		isSubmitting = true;
		try {
			const submission = await submitAssignment(data.assignmentId, buildAnswerPayload(userAnswers));
			showToast(
				submission.score === null
					? 'Đã nộp bài. Bài có câu tự luận nên chờ gia sư chấm.'
					: `Đã nộp bài. Điểm của bạn: ${submission.score}`,
				'success'
			);
			await goto(page.url.pathname.replace(/\/taking$/, ''));
		} catch (err) {
			showToast(getApiErrorMessage(err, 'Nộp bài không thành công.'), 'error');
		} finally {
			isSubmitting = false;
		}
	}

	function handleFinish() {
		handleSubmit(false);
	}

	function handleTimeUp() {
		showToast('Đã hết giờ làm bài, hệ thống đang nộp bài của bạn.', 'info');
		handleSubmit(true);
	}
</script>

<svelte:head>
	<link rel="preconnect" href="https://fonts.googleapis.com" />
	<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="" />
	<link
		href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700;800&family=Inter:wght@400;500;600&display=swap"
		rel="stylesheet"
	/>
</svelte:head>

<div class="flex-1 overflow-y-auto">
	<div class="flex min-h-screen bg-[#F5F6FA]" style="font-family:'Inter',sans-serif;">
		<!-- MAIN -->
		<div class="flex flex-1 flex-col">
			<header
				class="flex items-center justify-between border-b border-slate-200/70 bg-white/80 px-8 py-4 backdrop-blur"
			>
				<span class="text-sm font-medium text-slate-500"
					>Câu {currentIndex + 1} / {questions.length}</span
				>
				<a
					href="/"
					class="flex items-center gap-2 rounded-full bg-[#0C1550] px-4 py-2 text-sm font-medium text-white hover:bg-indigo-900"
				>
					<Home class="h-4 w-4" />
					Trang chủ
				</a>
			</header>

			<main class="flex flex-1 flex-col items-center overflow-y-auto px-8 py-10">
				<h1
					class="mb-8 max-w-2xl text-center text-xl font-bold uppercase tracking-tight text-slate-900"
					style="font-family:'Sora',sans-serif;"
				>
					{data.assignment.title}
				</h1>

				<div
					class="w-full max-w-2xl rounded-2xl border border-slate-200/70 bg-white p-8 shadow-sm shadow-slate-200/50"
				>
					<p
						class="mb-6 text-base font-semibold text-slate-800"
						style="font-family:'Sora',sans-serif;"
					>
						Câu {currentIndex + 1}: {currentQuestion.content}
					</p>

					{#if currentQuestion.question_type === 'MULTIPLE_CHOICE'}
						<div class="space-y-3">
							{#each currentQuestion.answers as answer (answer.id)}
								<button
									onclick={() => selectAnswer(answer.id)}
									class={`flex w-full items-center gap-3 rounded-full border px-5 py-3.5 text-left text-sm font-medium transition-all
					${
						currentAnswer?.type === 'MULTIPLE_CHOICE' && currentAnswer.answerId === answer.id
							? 'border-indigo-400 bg-indigo-50 text-indigo-700'
							: 'border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:bg-slate-50'
					}`}
								>
									<span
										class={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2 text-[10px] font-bold transition-colors
						${
							currentAnswer?.type === 'MULTIPLE_CHOICE' && currentAnswer.answerId === answer.id
								? 'border-indigo-400 bg-indigo-400 text-white'
								: 'border-slate-300 text-transparent'
						}`}
									>
										<Check class="h-3 w-3" />
									</span>
									{answer.content}
								</button>
							{/each}
						</div>
					{:else if currentQuestion.question_type === 'FILL_IN_BLANK'}
						<input
							type="text"
							value={currentAnswer?.type === 'FILL_IN_BLANK' ? currentAnswer.text : ''}
							oninput={(e) => updateTextAnswer(e.currentTarget.value)}
							placeholder="Nhập câu trả lời..."
							class="w-full rounded-full border border-slate-200 bg-white px-5 py-3.5 text-sm font-medium text-slate-700 outline-none focus:border-indigo-400"
						/>
					{:else if currentQuestion.question_type === 'ESSAY'}
						<textarea
							value={currentAnswer?.type === 'ESSAY' ? currentAnswer.text : ''}
							oninput={(e) => updateTextAnswer(e.currentTarget.value)}
							placeholder="Nhập câu trả lời của bạn..."
							rows="6"
							class="w-full resize-none rounded-2xl border border-slate-200 bg-white px-5 py-3.5 text-sm font-medium text-slate-700 outline-none focus:border-indigo-400"
						></textarea>
					{/if}
				</div>

				<div class="mt-8 flex w-full max-w-2xl items-center justify-between gap-4">
					<button
						onclick={() => goTo(currentIndex - 1)}
						disabled={currentIndex === 0}
						class="flex items-center gap-2 rounded-full border border-slate-200 bg-white px-5 py-2.5 text-sm font-medium text-slate-600 transition-colors hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
					>
						<ChevronLeft class="h-4 w-4" />
						Câu trước
					</button>

					<span class="text-sm font-semibold text-slate-500"
						>{answeredCount}/{questions.length} câu</span
					>

					<button
						onclick={() => goTo(currentIndex + 1)}
						disabled={currentIndex === questions.length - 1}
						class="flex items-center gap-2 rounded-full bg-[#0C1550] px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-indigo-900 disabled:cursor-not-allowed disabled:opacity-40"
					>
						Câu tiếp theo
						<ChevronRight class="h-4 w-4" />
					</button>
				</div>
			</main>
		</div>

		<!-- SIDEBAR -->
		<QuizSidebar
			{questions}
			{currentIndex}
			answeredIds={Object.keys(userAnswers).map(Number)}
			onSelectQuestion={goTo}
			mode="taking"
			{durationSeconds}
			onFinish={handleFinish}
			onTimeUp={handleTimeUp}
		/>
	</div>
</div>
