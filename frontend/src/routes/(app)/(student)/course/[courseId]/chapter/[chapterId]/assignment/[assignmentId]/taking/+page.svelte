<script lang="ts">
	import { untrack } from 'svelte';
	import { beforeNavigate, goto } from '$app/navigation';
	import { page } from '$app/state';
	import { Home, ChevronLeft, ChevronRight, Check } from 'lucide-svelte';
	import QuizSidebar from '$lib/components/QuizSidebar.svelte';
	import type { PageProps } from './$types';
	import type { Question, UserAnswer } from '$lib/api/entities';
	import { saveDraft, submitAssignment } from '$lib/api/calledAPI';
	import { getApiErrorMessage } from '$lib/api/errors';
	import {
		buildAnswerPayload,
		clearAnswerDraft,
		loadAnswerDraft,
		remainingSeconds,
		saveAnswerDraft
	} from '$lib/utils/assignment';
	import { showToast } from '$lib/stores/toast.svelte';
	import FieldError from '$lib/components/FieldError.svelte';
	import { FIELD_LIMITS, tooLongError } from '$lib/utils/validation';
	import { confirmAction } from '$lib/stores/confirm.svelte';

	let { data }: PageProps = $props();
	let questions: Question[] = $derived(data.questions);

	let currentIndex = $state(0);

	let attemptId = $derived(data.attempt.id);

	let userAnswers = $state<Record<number, UserAnswer>>(
		untrack(() => loadAnswerDraft(data.attempt.id))
	);

	$effect(() => {
		saveAnswerDraft(attemptId, userAnswers);
	});

	let currentQuestion = $derived(questions[currentIndex]);
	let currentAnswer = $derived(userAnswers[currentQuestion?.id]);

	let durationSeconds = $derived(remainingSeconds(data.attempt.deadline));

	let isSubmitting = $state(false);
	let leaving = $state(false);

	const DRAFT_SYNC_SECONDS = 30;

	let lastSyncedAnswers = $state('');

	async function syncDraftToServer() {
		if (isSubmitting) return;

		const payload = buildAnswerPayload(userAnswers);
		if (payload.length === 0) return;

		const snapshot = JSON.stringify(payload);
		if (snapshot === lastSyncedAnswers) return;

		try {
			await saveDraft(data.assignmentId, payload);
			lastSyncedAnswers = snapshot;
		} catch {
		}
	}

	$effect(() => {
		const timer = setInterval(syncDraftToServer, DRAFT_SYNC_SECONDS * 1000);
		return () => clearInterval(timer);
	});

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

	let answerError = $derived(
		currentAnswer && currentAnswer.type !== 'MULTIPLE_CHOICE'
			? tooLongError(currentAnswer.text, FIELD_LIMITS.answerText, 'Câu trả lời')
			: ''
	);

	function updateTextAnswer(text: string) {
		userAnswers[currentQuestion.id] = {
			type: currentQuestion.question_type as 'FILL_IN_BLANK' | 'ESSAY',
			text
		};
	}

	function goTo(index: number) {
		if (index < 0 || index >= questions.length) return;

		currentIndex = index;
		syncDraftToServer();
	}

	async function handleSubmit(auto = false) {
		if (isSubmitting) return;

		const tooLong = Object.values(userAnswers).find(
			(answer) =>
				answer.type !== 'MULTIPLE_CHOICE' &&
				tooLongError(answer.text, FIELD_LIMITS.answerText, 'Câu trả lời') !== ''
		);
		if (tooLong) {
			showToast(`Có câu trả lời vượt quá ${FIELD_LIMITS.answerText} ký tự.`, 'error');
			return;
		}

		if (!auto) {
			const remaining = questions.length - answeredCount;
			const agreed = await confirmAction({
				title: remaining > 0 ? 'Nộp bài khi còn câu bỏ trống?' : 'Nộp bài ngay bây giờ?',
				message:
					remaining > 0
						? `Bạn còn ${remaining} câu chưa trả lời. Các câu bỏ trống sẽ không được tính điểm, và nộp rồi thì không sửa lại được.`
						: `Bạn đã trả lời hết ${questions.length} câu. Nộp rồi thì không sửa lại được nữa.`,
				confirmLabel: remaining > 0 ? 'Vẫn nộp bài' : 'Nộp bài',
				cancelLabel: 'Quay lại làm tiếp',
				tone: remaining > 0 ? 'warning' : 'info'
			});
			if (!agreed) return;
		}

		const submitted = await submitAttempt();
		if (!submitted) return;

		leaving = true;
		await goto(page.url.pathname.replace(/\/taking$/, ''));
	}

	async function submitAttempt() {
		isSubmitting = true;
		try {
			const submission = await submitAssignment(data.assignmentId, buildAnswerPayload(userAnswers));
			clearAnswerDraft(attemptId);
			showToast(
				submission.score === null
					? 'Đã nộp bài. Bài có câu tự luận nên chờ gia sư chấm.'
					: `Đã nộp bài. Điểm của bạn: ${submission.score}`,
				'success'
			);
			return true;
		} catch (err) {
			showToast(getApiErrorMessage(err, 'Nộp bài không thành công.'), 'error');
			return false;
		} finally {
			isSubmitting = false;
		}
	}

	beforeNavigate((navigation) => {
		if (leaving || isSubmitting) return;

		const target = navigation.to?.url;
		if (!target) return;

		navigation.cancel();
		confirmLeaveAttempt(target);
	});

	async function confirmLeaveAttempt(target: URL) {
		const agreed = await confirmAction({
			title: 'Rời khỏi bài làm?',
			message: `Rời khỏi trang này sẽ kết thúc lượt làm bài. Hệ thống nộp bài với ${answeredCount}/${questions.length} câu bạn đã trả lời và bạn không quay lại làm tiếp được.`,
			confirmLabel: 'Nộp bài và rời đi',
			cancelLabel: 'Ở lại làm tiếp',
			tone: 'warning'
		});
		if (!agreed) return;

		const submitted = await submitAttempt();
		if (!submitted) return;

		leaving = true;
		await goto(`${target.pathname}${target.search}`);
	}

	function handleFinish() {
		handleSubmit(false);
	}

	function handleTimeUp() {
		showToast('Đã hết giờ làm bài, hệ thống đang nộp bài của bạn.', 'info');
		handleSubmit(true);
	}
</script>

<div class="flex-1 overflow-y-auto">
	<div class="flex min-h-screen bg-slate-50">
		<div class="flex flex-1 flex-col">
			<header
				class="flex items-center justify-between border-b border-slate-200/70 bg-white/80 px-8 py-4 backdrop-blur"
			>
				<span class="text-sm font-medium text-slate-500"
					>Câu {currentIndex + 1} / {questions.length}</span
				>
				<a
					href="/stu-dashboard"
					class="flex items-center gap-2 rounded-full bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
				>
					<Home class="h-4 w-4" />
					Trang chủ
				</a>
			</header>

			<main class="flex flex-1 flex-col items-center overflow-y-auto px-8 py-10">
				<h1
					class="mb-8 max-w-2xl text-center text-xl font-bold uppercase tracking-tight text-slate-900 font-heading"
				>
					{data.assignment.title}
				</h1>

				<div
					class="w-full max-w-2xl rounded-2xl border border-slate-200/70 bg-white p-8 shadow-sm shadow-slate-200/50"
				>
					<p class="mb-6 text-base font-semibold text-slate-800 font-heading">
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
							? 'border-brand-400 bg-brand-50 text-brand-700'
							: 'border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:bg-slate-50'
					}`}
								>
									<span
										class={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2 text-[10px] font-bold transition-colors
						${
							currentAnswer?.type === 'MULTIPLE_CHOICE' && currentAnswer.answerId === answer.id
								? 'border-brand-400 bg-brand-400 text-white'
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
							class="w-full rounded-full border border-slate-200 bg-white px-5 py-3.5 text-sm font-medium text-slate-700 outline-none focus:border-brand-400"
						/>
					{:else if currentQuestion.question_type === 'ESSAY'}
						<textarea
							value={currentAnswer?.type === 'ESSAY' ? currentAnswer.text : ''}
							oninput={(e) => updateTextAnswer(e.currentTarget.value)}
							placeholder="Nhập câu trả lời của bạn..."
							rows="6"
							class="w-full resize-none rounded-2xl border border-slate-200 bg-white px-5 py-3.5 text-sm font-medium text-slate-700 outline-none focus:border-brand-400"
						></textarea>
					{/if}
					<FieldError message={answerError} />
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
						class="flex items-center gap-2 rounded-full bg-brand-600 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-40"
					>
						Câu tiếp theo
						<ChevronRight class="h-4 w-4" />
					</button>
				</div>
			</main>
		</div>

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
