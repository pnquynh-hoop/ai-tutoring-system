<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import {
		Home,
		Clock,
		CalendarDays,
		ListChecks,
		FileQuestion,
		ArrowRight,
		RotateCcw
	} from 'lucide-svelte';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
	const assignment = $derived(data.assignment);

	// Backend giới hạn số lượt nộp cho mỗi bài tập và trả về qua max_attempts/attempts_used.
	let attemptsLeft = $derived(Math.max(0, assignment.maxAttempts - assignment.attemptsUsed));
	let isOverdue = $derived(new Date(assignment.dueDate).getTime() < Date.now());
	let canStart = $derived(attemptsLeft > 0 && !isOverdue);

	let dueDateLabel = $derived(
		new Date(assignment.dueDate).toLocaleDateString('vi-VN', {
			day: '2-digit',
			month: '2-digit',
			year: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		})
	);

	function handleStart() {
		goto(`${page.url.pathname}/taking`);
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
	<header
		class="flex items-center justify-between border-b border-slate-200/70 bg-white/80 px-8 py-4 backdrop-blur"
	>
		<a
			href="/"
			class="flex items-center gap-2 rounded-full bg-[#0C1550] px-4 py-2 text-sm font-medium text-white hover:bg-indigo-900"
		>
			<Home class="h-4 w-4" />
			Trang chủ
		</a>
	</header>

	<main class="flex flex-1 flex-col items-center px-8 py-10">
		<h1
			class="mb-8 max-w-2xl text-center text-xl font-bold uppercase tracking-tight text-slate-900"
			style="font-family:'Sora',sans-serif;"
		>
			{assignment.title}
		</h1>

		<div
			class="w-full max-w-2xl rounded-2xl border border-slate-200/70 bg-white p-8 shadow-sm shadow-slate-200/50"
		>
			<div class="grid grid-cols-2 gap-4">
				<div class="flex items-center gap-3 rounded-2xl bg-slate-50 px-4 py-3.5">
					<div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-indigo-100">
						<Clock class="h-4.5 w-4.5 text-indigo-600" />
					</div>
					<div class="min-w-0">
						<p class="text-xs font-medium text-slate-500">Thời gian làm bài</p>
						<p class="truncate text-sm font-semibold text-slate-800">
							{assignment.timeLimitMinutes
								? `${assignment.timeLimitMinutes} phút`
								: 'Không giới hạn'}
						</p>
					</div>
				</div>

				<div class="flex items-center gap-3 rounded-2xl bg-slate-50 px-4 py-3.5">
					<div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-rose-100">
						<CalendarDays class="h-4.5 w-4.5 text-rose-600" />
					</div>
					<div class="min-w-0">
						<p class="text-xs font-medium text-slate-500">Hạn chót</p>
						<p class="truncate text-sm font-semibold text-slate-800">{dueDateLabel}</p>
					</div>
				</div>

				<div class="flex items-center gap-3 rounded-2xl bg-slate-50 px-4 py-3.5">
					<div
						class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-emerald-100"
					>
						<FileQuestion class="h-4.5 w-4.5 text-emerald-600" />
					</div>
					<div class="min-w-0">
						<p class="text-xs font-medium text-slate-500">Số câu hỏi</p>
						<p class="truncate text-sm font-semibold text-slate-800">
							{assignment.totalQuestions} câu
						</p>
					</div>
				</div>

				<div class="flex items-center gap-3 rounded-2xl bg-slate-50 px-4 py-3.5">
					<div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-amber-100">
						<ListChecks class="h-4.5 w-4.5 text-amber-600" />
					</div>
					<div class="min-w-0">
						<p class="text-xs font-medium text-slate-500">Dạng bài tập</p>
						<p class="truncate text-sm font-semibold text-slate-800">
							{assignment.questionTypes.length} dạng
						</p>
					</div>
				</div>

				<div class="col-span-2 flex items-center gap-3 rounded-2xl bg-slate-50 px-4 py-3.5">
					<div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-sky-100">
						<RotateCcw class="h-4.5 w-4.5 text-sky-600" />
					</div>
					<div class="min-w-0">
						<p class="text-xs font-medium text-slate-500">Lượt làm bài</p>
						<p class="truncate text-sm font-semibold text-slate-800">
							Đã dùng {assignment.attemptsUsed}/{assignment.maxAttempts} lượt · còn {attemptsLeft} lượt
						</p>
					</div>
				</div>
			</div>

			<div class="mt-6 border-t border-slate-100 pt-6">
				<p class="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400">
					Cấu trúc bài tập
				</p>
				<div class="space-y-2">
					{#each assignment.questionTypes as qt (qt.label)}
						<div class="flex items-center justify-between rounded-xl bg-slate-50 px-4 py-2.5">
							<span class="text-sm font-medium text-slate-700">{qt.label}</span>
							<span class="text-sm font-semibold text-slate-500">{qt.count} câu</span>
						</div>
					{/each}
				</div>
			</div>
		</div>

		<button
			onclick={handleStart}
			disabled={!canStart}
			class="mt-8 flex items-center gap-2 rounded-full bg-[#0C1550] px-8 py-3 text-sm font-semibold text-white transition-colors hover:bg-indigo-900 disabled:cursor-not-allowed disabled:opacity-40"
		>
			{assignment.attemptsUsed > 0 ? 'Làm lại bài tập' : 'Bắt đầu làm bài'}
			<ArrowRight class="h-4 w-4" />
		</button>

		{#if !canStart}
			<p class="mt-3 text-center text-xs font-medium text-slate-500">
				{isOverdue
					? 'Bài tập đã hết hạn nộp.'
					: `Bạn đã dùng hết ${assignment.maxAttempts} lượt làm bài.`}
			</p>
		{/if}
	</main>
</div>
