<script lang="ts">
	import { Home, ChevronLeft, ChevronRight, Check } from 'lucide-svelte';
	import QuizSidebar from '$lib/components/QuizSidebar.svelte';

	let questions = $state(
		Array.from({ length: 20 }, (_, i) => ({
			id: i + 1,
			content: `Mệnh đề nào sau đây đúng ngữ pháp mệnh đề quan hệ rút gọn? (Câu ${i + 1})`,
			options: [
				{ id: 1, content: 'abc' },
				{ id: 2, content: 'abc' },
				{ id: 3, content: 'abc' },
				{ id: 4, content: 'abc' }
			],
			selected: null as number | null,
			isCorrect: null as boolean | null
		}))
	);

	let currentIndex = $state(0);

	let currentQuestion = $derived(questions[currentIndex]);
	let answeredCount = $derived(questions.filter((q) => q.selected !== null).length);

	function selectAnswer(optionIndex: number) {
		questions[currentIndex].selected = optionIndex;
	}

	function goTo(index: number) {
		if (index >= 0 && index < questions.length) currentIndex = index;
	}

	function handleFinish() {
		// TODO: submit bài làm
	}

	function handleTimeUp() {
		// TODO: tự động nộp bài khi hết giờ
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
					Ôn tập Chương 1. Mệnh đề quan hệ và mệnh đề quan hệ rút gọn đa dạng
				</h1>

				<div
					class="w-full max-w-2xl rounded-2xl border border-slate-200/70 bg-white p-8 shadow-sm shadow-slate-200/50"
				>
					<p
						class="mb-6 text-base font-semibold text-slate-800"
						style="font-family:'Sora',sans-serif;"
					>
						Câu {currentQuestion.id}: {currentQuestion.content}
					</p>

					<div class="space-y-3">
						{#each currentQuestion.options as option, i (option.id)}
							<button
								onclick={() => selectAnswer(i)}
								class={`flex w-full items-center gap-3 rounded-full border px-5 py-3.5 text-left text-sm font-medium transition-all
				${
					currentQuestion.selected === i
						? 'border-indigo-400 bg-indigo-50 text-indigo-700'
						: 'border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:bg-slate-50'
				}`}
							>
								<span
									class={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2 text-[10px] font-bold transition-colors
					${currentQuestion.selected === i ? 'border-indigo-400 bg-indigo-400 text-white' : 'border-slate-300 text-transparent'}`}
								>
									<Check class="h-3 w-3" />
								</span>
								{option.content}
							</button>
						{/each}
					</div>
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
			onSelectQuestion={goTo}
			mode="taking"
			durationSeconds={3600}
			onFinish={handleFinish}
			onTimeUp={handleTimeUp}
		/>
	</div>
</div>
