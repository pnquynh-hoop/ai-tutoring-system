<script lang="ts">
	import { Home, Menu, Clock, ChevronLeft, ChevronRight, Check } from 'lucide-svelte';

	let courseName = $state('Tiếng anh 12');
	let studentName = $state('Quỳnh');
	let quizTitle = $state('Bài ôn tập chương số 5. Mệnh đề quan hệ đầy đủ và rút gọn');

	let questions = $state(
		Array.from({ length: 20 }, (_, i) => ({
			id: i + 1,
			text: `Mệnh đề nào sau đây đúng ngữ pháp mệnh đề quan hệ rút gọn? (Câu ${i + 1})`,
			options: ['abc', 'abc', 'abc', 'abc'],
			selected: null as number | null
		}))
	);

	let currentIndex = $state(0);
	let sidebarCollapsed = $state(false);

	let currentQuestion = $derived(questions[currentIndex]);
	let answeredCount = $derived(questions.filter((q) => q.selected !== null).length);

	function selectAnswer(optionIndex: number) {
		questions[currentIndex].selected = optionIndex;
	}

	function goTo(index: number) {
		if (index >= 0 && index < questions.length) currentIndex = index;
	}

	// ---- Đồng hồ đếm ngược ----
	let totalSeconds = $state(24 * 60 - 6);

	$effect(() => {
		const timer = setInterval(() => {
			if (totalSeconds > 0) totalSeconds -= 1;
		}, 1000);
		return () => clearInterval(timer);
	});

	let timeLabel = $derived.by(() => {
		const h = Math.floor(totalSeconds / 3600);
		const m = Math.floor((totalSeconds % 3600) / 60);
		const s = totalSeconds % 60;
		return [h, m, s].map((n) => String(n).padStart(2, '0')).join(':');
	});
	let timeIsLow = $derived(totalSeconds < 300);
</script>

<svelte:head>
	<link rel="preconnect" href="https://fonts.googleapis.com" />
	<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="" />
	<link
		href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700;800&family=Inter:wght@400;500;600&display=swap"
		rel="stylesheet"
	/>
	<title>{quizTitle}</title>
</svelte:head>

<div class="flex min-h-screen bg-[#F5F6FA]" style="font-family:'Inter',sans-serif;">
	<!-- SIDEBAR -->
	<aside
		class={`flex shrink-0 flex-col overflow-hidden bg-[#0C1550] text-white transition-all duration-300 ${sidebarCollapsed ? 'w-16' : 'w-72'}`}
	>
		<div
			class={`flex items-center border-b border-white/10 py-6 ${sidebarCollapsed ? 'justify-center px-0' : 'justify-between px-5'}`}
		>
			{#if !sidebarCollapsed}
				<div class="min-w-0">
					<p
						class="truncate text-[15px] font-bold tracking-tight text-white"
						style="font-family:'Sora',sans-serif;"
					>
						{courseName}
					</p>
					<p class="mt-0.5 text-[11px] font-medium uppercase tracking-wider text-indigo-100/40">
						{questions.length} câu hỏi
					</p>
				</div>
			{/if}
			<button
				onclick={() => (sidebarCollapsed = !sidebarCollapsed)}
				class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white/5 text-indigo-100/50 transition-colors hover:bg-white/10 hover:text-white"
			>
				<Menu class="h-4 w-4" />
			</button>
		</div>

		{#if !sidebarCollapsed}
			<!-- ĐỒNG HỒ ĐẾM NGƯỢC -->
			<div class="px-5 pt-5">
				<div
					class={`flex items-center justify-center gap-2 rounded-2xl border py-2.5 text-sm font-bold tabular-nums transition-colors
						${timeIsLow ? 'border-rose-400/30 bg-rose-400/10 text-rose-300' : 'border-white/10 bg-white/5 text-indigo-100/80'}`}
				>
					<Clock class="h-4 w-4" />
					{timeLabel}
				</div>
			</div>

			<!-- LƯỚI SỐ CÂU HỎI -->
			<div class="flex-1 overflow-y-auto px-5 py-5">
				<div class="grid grid-cols-4 gap-2.5">
					{#each questions as question, i (i)}
						<button
							onclick={() => goTo(i)}
							class={`relative flex aspect-square w-full items-center justify-center rounded-2xl text-sm font-semibold transition-all
					${
						i === currentIndex
							? 'bg-indigo-400 text-white shadow-lg shadow-indigo-900/30'
							: question.selected !== null
								? 'bg-white/10 text-white'
								: 'bg-white/4 text-indigo-100/40 hover:bg-white/10 hover:text-white'
					}`}
						>
							{question.id}
							{#if question.selected !== null && i !== currentIndex}
								<Check
									class="absolute -right-1 -top-1 h-3.5 w-3.5 rounded-full bg-emerald-400 p-0.5 text-[#0C1550]"
								/>
							{/if}
						</button>
					{/each}
				</div>
			</div>

			<div class="px-5 pb-5">
				<button
					class="w-full rounded-full bg-white py-2.5 text-sm font-semibold text-[#0C1550] transition-colors hover:bg-indigo-50"
				>
					Hoàn thành ({answeredCount}/{questions.length})
				</button>
			</div>
		{:else}
			<div class="flex-1"></div>
		{/if}

		<div class={`border-t border-white/10 py-4 ${sidebarCollapsed ? 'px-0' : 'px-3'}`}>
			<div
				class={`flex items-center rounded-xl py-2 hover:bg-white/5 ${sidebarCollapsed ? 'justify-center px-0' : 'gap-3 px-2'}`}
			>
				<div
					class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-linear-to-tr from-rose-400 to-orange-300 text-sm font-bold text-white"
				>
					{studentName[0]}
				</div>
				{#if !sidebarCollapsed}
					<div class="min-w-0 flex-1">
						<p class="truncate text-sm font-medium text-white">{studentName}</p>
						<p class="truncate text-xs text-indigo-100/50">Học sinh lớp 12</p>
					</div>
				{/if}
			</div>
		</div>
	</aside>

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
				{quizTitle}
			</h1>

			<div
				class="w-full max-w-2xl rounded-2xl border border-slate-200/70 bg-white p-8 shadow-sm shadow-slate-200/50"
			>
				<p
					class="mb-6 text-base font-semibold text-slate-800"
					style="font-family:'Sora',sans-serif;"
				>
					Câu {currentQuestion.id}: {currentQuestion.text}
				</p>

				<div class="space-y-3">
					{#each currentQuestion.options as option, i (i)}
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
							{option}
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
</div>
