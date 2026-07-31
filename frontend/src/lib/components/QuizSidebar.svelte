<script lang="ts">
	import type { Question } from '$lib/api/entities';
	import { Menu, Clock, Check, X } from 'lucide-svelte';

	interface Props {
		questions: Question[];
		currentIndex: number;
		onSelectQuestion: (index: number) => void;
		mode?: 'taking' | 'review';
		durationSeconds?: number;
		onFinish?: () => void;
		onTimeUp?: () => void;
		answeredIds?: number[];
		results?: Record<number, boolean>;
	}

	let {
		questions,
		currentIndex,
		onSelectQuestion,
		mode = 'taking',
		durationSeconds = 0,
		onFinish,
		onTimeUp,
		answeredIds = [],
		results = {}
	}: Props = $props();

	let sidebarCollapsed = $state(false);

	let totalSeconds = $derived(durationSeconds);
	let hasNotifiedTimeUp = false;
	let hasTimeLimit = $derived(durationSeconds > 0);

	$effect(() => {
		if (mode !== 'taking' || !hasTimeLimit) return;

		const timer = setInterval(() => {
			if (totalSeconds > 0) {
				totalSeconds -= 1;
				if (totalSeconds === 0 && !hasNotifiedTimeUp) {
					hasNotifiedTimeUp = true;
					onTimeUp?.();
				}
			}
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

	let answeredSet = $derived(new Set(answeredIds));
	let answeredCount = $derived(answeredSet.size);

	function isAnswered(question: Question) {
		return answeredSet.has(question.id);
	}

	function cellClasses(question: Question, index: number) {
		if (index === currentIndex) {
			return 'bg-indigo-400 text-white shadow-lg shadow-indigo-900/30';
		}

		if (mode === 'review') {
			const isCorrect = results[question.id];
			if (isCorrect === true) return 'bg-emerald-400/15 text-emerald-300';
			if (isCorrect === false) return 'bg-rose-400/15 text-rose-300';
			return 'bg-white/4 text-indigo-100/40';
		}

		return isAnswered(question)
			? 'bg-white/10 text-white'
			: 'bg-white/4 text-indigo-100/40 hover:bg-white/10 hover:text-white';
	}
</script>

<aside
	class={`flex shrink-0 flex-col overflow-hidden bg-[#0C1550] text-white transition-all duration-300 ${sidebarCollapsed ? 'w-16' : 'w-72'}`}
>
	<div
		class={`flex items-center border-b border-white/10 py-6 ${sidebarCollapsed ? 'justify-center px-0' : 'justify-between px-5'}`}
	>
		{#if !sidebarCollapsed}
			<div class="min-w-0">
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
		{#if mode === 'taking'}
			<div class="px-5 pt-5">
				{#if hasTimeLimit}
					<div
						class={`flex items-center justify-center gap-2 rounded-2xl border py-2.5 text-sm font-bold tabular-nums transition-colors
					${timeIsLow ? 'border-rose-400/30 bg-rose-400/10 text-rose-300' : 'border-white/10 bg-white/5 text-indigo-100/80'}`}
					>
						<Clock class="h-4 w-4" />
						{timeLabel}
					</div>
				{:else}
					<div
						class="flex items-center justify-center gap-2 rounded-2xl border border-white/10 bg-white/5 py-2.5 text-sm font-bold text-indigo-100/60"
					>
						<Clock class="h-4 w-4" />
						Không giới hạn
					</div>
				{/if}
			</div>
		{/if}

		<div class="flex-1 overflow-y-auto px-5 py-5">
			<div class="grid grid-cols-4 gap-2.5">
				{#each questions as question, i (question.id)}
					<button
						onclick={() => onSelectQuestion(i)}
						class={`relative flex aspect-square w-full items-center justify-center rounded-2xl text-sm font-semibold transition-all ${cellClasses(question, i)}`}
					>
						{i + 1}
						{#if i !== currentIndex}
							{#if mode === 'taking' && isAnswered(question)}
								<Check
									class="absolute -right-1 -top-1 h-3.5 w-3.5 rounded-full bg-emerald-400 p-0.5 text-[#0C1550]"
								/>
							{:else if mode === 'review' && results[question.id] === true}
								<Check
									class="absolute -right-1 -top-1 h-3.5 w-3.5 rounded-full bg-emerald-400 p-0.5 text-[#0C1550]"
								/>
							{:else if mode === 'review' && results[question.id] === false}
								<X
									class="absolute -right-1 -top-1 h-3.5 w-3.5 rounded-full bg-rose-400 p-0.5 text-[#0C1550]"
								/>
							{/if}
						{/if}
					</button>
				{/each}
			</div>
		</div>

		{#if mode === 'taking' && onFinish}
			<div class="px-5 pb-5">
				<button
					onclick={onFinish}
					class="w-full rounded-full bg-white py-2.5 text-sm font-semibold text-[#0C1550] transition-colors hover:bg-indigo-50"
				>
					Hoàn thành ({answeredCount}/{questions.length})
				</button>
			</div>
		{/if}
	{:else}
		<div class="flex-1"></div>
	{/if}
</aside>
