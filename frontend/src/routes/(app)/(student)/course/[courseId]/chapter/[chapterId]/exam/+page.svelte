<script lang="ts">
	import { goto } from '$app/navigation';
	import { Home, ChevronRight, Clock, ListChecks, RotateCcw, ShieldAlert, PlayCircle } from 'lucide-svelte';
	import type { PageData } from './$types';
	import type { Chapter, Lesson } from '$lib/api/entities';
	import { postStartTest } from '$lib/api/calledAPI';
	import { showToast } from '$lib/stores/toast.svelte';
	import axios from 'axios';

	// Giả định kiểu dữ liệu Test trả về từ BE. Điều chỉnh lại theo entities.ts thực tế của dự án.
	interface TestDetail {
		id: number;
		title: string;
		description?: string | null;
		duration_minutes: number;
		question_count: number;
		attempts_allowed: number | null; // null = không giới hạn
		attempts_used: number;
		passing_score?: number | null;
	}

	let { data }: { data: PageData } = $props();
	let course_tree = $derived(data.course_tree);
	let test = $derived(data.test as TestDetail);

	const activeChapter = $derived(
		course_tree.chapters.find((ch: Chapter) => ch.lessons.some((ls: Lesson) => ls.id === data.lessonId))
	);

	const attemptsLeft = $derived(
		test.attempts_allowed === null ? null : Math.max(test.attempts_allowed - test.attempts_used, 0)
	);

	const canStart = $derived(test.attempts_allowed === null || (attemptsLeft ?? 0) > 0);

	let isStarting = $state(false);

	async function handleStart() {
		if (isStarting || !canStart) return;
		isStarting = true;
		try {
			const attempt = await postStartTest(test.id);
			await goto(`/course/${course_tree.id}/test/${test.id}/attempt/${attempt.id}`);
		} catch (err: unknown) {
			const message = axios.isAxiosError(err)
				? (err.response?.data?.message ?? 'Không thể bắt đầu bài test.')
				: 'Đã xảy ra lỗi.';
			showToast(message, 'error');
		} finally {
			isStarting = false;
		}
	}
</script>

<svelte:head>
	<link rel="preconnect" href="https://fonts.googleapis.com" />
	<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="" />
	<link
		href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700;800&family=Inter:wght@400;500;600&family=Sora:wght@600;700;800&display=swap"
		rel="stylesheet"
	/>
	<title>{test.title}</title>
</svelte:head>

<div class="flex-1 overflow-y-auto">
	<div class="flex h-full min-h-0 flex-1 flex-col" style="font-family:'Inter',sans-serif;">
		<!-- HEADER / BREADCRUMB -->
		<header
			class="flex items-center justify-between gap-4 border-b border-slate-200/70 bg-white/80 px-8 py-4 backdrop-blur"
		>
			<nav class="flex min-w-0 flex-1 items-center gap-2 text-sm text-slate-500">
				<span class="shrink-0 font-medium text-slate-700">{course_tree.name}</span>
				{#if activeChapter}
					<ChevronRight class="h-3.5 w-3.5 shrink-0 text-slate-300" />
					<span class="min-w-0 truncate font-medium text-slate-700">{activeChapter.title}</span>
				{/if}
				<ChevronRight class="h-3.5 w-3.5 shrink-0 text-slate-300" />
				<span class="min-w-0 truncate font-semibold text-[#0C1550]">{test.title}</span>
			</nav>

			<a
				href="/stu-dashboard"
				class="flex shrink-0 items-center gap-2 rounded-full bg-[#0C1550] px-4 py-2 text-sm font-medium text-white hover:bg-indigo-900"
			>
				<Home class="h-4 w-4" />
				Trang chủ
			</a>
		</header>

		<!-- MAIN -->
		<main class="flex flex-1 items-center justify-center overflow-y-auto px-8 py-10">
			<div class="w-full max-w-2xl">
				<div class="rounded-2xl border border-slate-200/70 bg-white p-8 shadow-sm shadow-slate-200/50">
					<h1
						class="mb-2 text-center text-xl font-bold uppercase tracking-tight text-slate-900"
						style="font-family:'Sora',sans-serif;"
					>
						{test.title}
					</h1>

					{#if test.description}
						<p class="mb-6 text-center text-sm text-slate-500">{test.description}</p>
					{/if}

					<!-- THÔNG TIN BÀI TEST -->
					<div class="mb-8 grid grid-cols-2 gap-4">
						<div class="flex items-center gap-3 rounded-xl border border-slate-100 bg-slate-50 p-4">
							<div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600">
								<Clock class="h-5 w-5" />
							</div>
							<div class="min-w-0">
								<p class="text-[11px] font-medium uppercase tracking-wide text-slate-400">Thời gian làm bài</p>
								<p class="text-sm font-semibold text-slate-800">{test.duration_minutes} phút</p>
							</div>
						</div>

						<div class="flex items-center gap-3 rounded-xl border border-slate-100 bg-slate-50 p-4">
							<div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-teal-50 text-teal-600">
								<ListChecks class="h-5 w-5" />
							</div>
							<div class="min-w-0">
								<p class="text-[11px] font-medium uppercase tracking-wide text-slate-400">Số câu hỏi</p>
								<p class="text-sm font-semibold text-slate-800">{test.question_count} câu</p>
							</div>
						</div>

						<div class="flex items-center gap-3 rounded-xl border border-slate-100 bg-slate-50 p-4">
							<div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-amber-50 text-amber-600">
								<RotateCcw class="h-5 w-5" />
							</div>
							<div class="min-w-0">
								<p class="text-[11px] font-medium uppercase tracking-wide text-slate-400">Lượt làm bài</p>
								<p class="text-sm font-semibold text-slate-800">
									{#if test.attempts_allowed === null}
										Không giới hạn
									{:else}
										Còn {attemptsLeft} / {test.attempts_allowed} lượt
									{/if}
								</p>
							</div>
						</div>

						{#if test.passing_score !== null && test.passing_score !== undefined}
							<div class="flex items-center gap-3 rounded-xl border border-slate-100 bg-slate-50 p-4">
								<div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-violet-50 text-violet-600">
									<ShieldAlert class="h-5 w-5" />
								</div>
								<div class="min-w-0">
									<p class="text-[11px] font-medium uppercase tracking-wide text-slate-400">Điểm đạt</p>
									<p class="text-sm font-semibold text-slate-800">{test.passing_score} điểm</p>
								</div>
							</div>
						{/if}
					</div>

					<!-- LƯU Ý: không có trợ lý AI trong trang làm bài -->
					<div class="mb-6 rounded-xl border border-amber-100 bg-amber-50 px-4 py-3 text-xs text-amber-700">
						Trong quá trình làm bài, bạn sẽ không được hỗ trợ bởi trợ lý AI. Hãy đảm bảo đã sẵn sàng
						trước khi bắt đầu.
					</div>

					<div class="flex justify-center">
						<button
							onclick={handleStart}
							disabled={!canStart || isStarting}
							class="flex items-center gap-2 rounded-full bg-[#0C1550] px-8 py-3 text-sm font-semibold text-white transition-colors hover:bg-indigo-900 disabled:cursor-not-allowed disabled:opacity-50"
						>
							<PlayCircle class="h-4 w-4" />
							{isStarting ? 'Đang bắt đầu...' : canStart ? 'Bắt đầu làm bài' : 'Đã hết lượt làm bài'}
						</button>
					</div>
				</div>
			</div>
		</main>
	</div>
</div>