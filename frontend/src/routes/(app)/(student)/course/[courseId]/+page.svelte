<script lang="ts">
	import { goto } from '$app/navigation';
	import {
		Home,
		ChevronRight,
		Target,
		ClipboardCheck,
		AlertTriangle,
		Lock,
		CheckCircle2,
		PlayCircle,
		Lightbulb
	} from 'lucide-svelte';
	import Chatbot from '$lib/components/Chatbot.svelte';
	// import type { PageData } from './$types';

	// ============================================================
	// TODO: khi có API thật, xóa mockData và dùng:
	// let { data }: { data: PageData } = $props();
	// let overview = $derived(data.overview);
	// ============================================================

	interface ChapterStat {
		id: number;
		title: string;
		order: number;
		total_lessons: number;
		completed_lessons: number;
		average_score: number | null;
		pending_assignments: number;
		first_incomplete_lesson_id: number | null;
	}

	interface CourseOverview {
		course: {
			id: number;
			name: string;
			tutor_name: string | null;
			description: string;
			subject_name: string;
			grade: number;
		};
		progress: {
			total_lessons: number;
			completed_lessons: number;
			percent: number;
		};
		chapters: ChapterStat[];
	}

	const mockData: CourseOverview = {
		course: {
			id: 1,
			name: 'Luyện Thi THPT QG Toán Học 2026',
			tutor_name: null,
			description: 'Khóa học ôn luyện toàn diện kiến thức Toán 12.',
			subject_name: 'Toán Học',
			grade: 5
		},
		progress: {
			total_lessons: 18,
			completed_lessons: 7,
			percent: 39
		},
		chapters: [
			{
				id: 1,
				title: 'Chương 1: Ứng dụng đạo hàm để khảo sát hàm số',
				order: 1,
				total_lessons: 6,
				completed_lessons: 6,
				average_score: 8.5,
				pending_assignments: 0,
				first_incomplete_lesson_id: null
			},
			{
				id: 2,
				title: 'Chương 2: Hàm số lũy thừa, mũ và logarit',
				order: 2,
				total_lessons: 5,
				completed_lessons: 1,
				average_score: 4.8,
				pending_assignments: 1,
				first_incomplete_lesson_id: 8
			},
			{
				id: 3,
				title: 'Chương 3: Nguyên hàm, tích phân và ứng dụng',
				order: 3,
				total_lessons: 4,
				completed_lessons: 0,
				average_score: null,
				pending_assignments: 1,
				first_incomplete_lesson_id: 13
			},
			{
				id: 4,
				title: 'Chương 4: Số phức',
				order: 4,
				total_lessons: 3,
				completed_lessons: 0,
				average_score: null,
				pending_assignments: 0,
				first_incomplete_lesson_id: 17
			}
		]
	};

	let overview = $state(mockData);

	let nextLessonId = $derived(
		overview.chapters.find((c) => c.first_incomplete_lesson_id !== null)
			?.first_incomplete_lesson_id ?? null
	);

	// Chỉ tính trên các chương ĐÃ có điểm (average_score !== null)
	let scoredChapters = $derived(overview.chapters.filter((c) => c.average_score !== null));

	let courseAverageScore = $derived(
		scoredChapters.length > 0
			? scoredChapters.reduce((sum, c) => sum + (c.average_score ?? 0), 0) / scoredChapters.length
			: null
	);

	let totalPendingAssignments = $derived(
		overview.chapters.reduce((sum, c) => sum + c.pending_assignments, 0)
	);

	// Chương yếu nhất: có điểm và điểm thấp nhất
	let weakestChapter = $derived(
		scoredChapters.length > 0
			? scoredChapters.reduce((min, c) => ((c.average_score ?? 10) < (min.average_score ?? 10) ? c : min))
			: null
	);

	function scoreTone(score: number | null) {
		if (score === null) return 'text-slate-400 bg-slate-50';
		if (score < 5) return 'text-rose-600 bg-rose-50';
		if (score < 8) return 'text-amber-600 bg-amber-50';
		return 'text-emerald-600 bg-emerald-50';
	}

	function chapterStatus(chapter: ChapterStat) {
		if (chapter.completed_lessons === chapter.total_lessons) return 'done';
		if (chapter.completed_lessons > 0) return 'in_progress';
		return 'not_started';
	}
</script>

<svelte:head>
	<link rel="preconnect" href="https://fonts.googleapis.com" />
	<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="" />
	<link
		href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Sora:wght@600;700;800&display=swap"
		rel="stylesheet"
	/>
	<title>{overview.course.name}</title>
</svelte:head>

<div class="flex h-full min-h-0 flex-1 flex-col" style="font-family:'Inter',sans-serif;">
	<header
		class="flex items-center justify-between gap-4 border-b border-slate-200/70 bg-white/80 px-8 py-4 backdrop-blur"
	>
		<nav class="flex min-w-0 flex-1 items-center gap-2 text-sm text-slate-500">
			<span class="min-w-0 truncate font-semibold text-[#0C1550]">{overview.course.name}</span>
		</nav>

		<a
			href="/stu-dashboard"
			class="flex shrink-0 items-center gap-2 rounded-full bg-[#0C1550] px-4 py-2 text-sm font-medium text-white hover:bg-indigo-900"
		>
			<Home class="h-4 w-4" />
			Trang chủ
		</a>
	</header>

	<main class="min-h-0 flex-1 space-y-8 overflow-y-auto px-8 py-8">
		<!-- HERO KHÓA HỌC -->
		<div
			class="relative overflow-hidden rounded-2xl border border-slate-200/70 bg-white p-8 shadow-sm shadow-slate-200/50"
		>
			<div
				class="absolute -right-10 -top-10 h-40 w-40 rounded-full bg-linear-to-br from-indigo-500/10 to-violet-500/10"
			></div>

			<div class="relative flex flex-wrap items-start justify-between gap-6">
				<div class="min-w-0 max-w-2xl">
					<div class="mb-3 flex flex-wrap items-center gap-2">
						<span class="rounded-full bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-600">
							{overview.course.subject_name}
						</span>
						<span class="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
							Khối {overview.course.grade}
						</span>
					</div>

					<h1 class="mb-2 text-2xl font-bold text-slate-900" style="font-family:'Sora',sans-serif;">
						{overview.course.name}
					</h1>

					<p class="mb-3 text-sm leading-relaxed text-slate-500">
						{overview.course.description}
					</p>

					<p class="text-xs text-slate-400">
						Gia sư phụ trách:
						<span class="font-medium text-slate-600">
							{overview.course.tutor_name ?? 'Chưa phân công'}
						</span>
					</p>
				</div>

				<button
					onclick={() => nextLessonId && goto(`/course/${overview.course.id}/lesson/${nextLessonId}`)}
					disabled={!nextLessonId}
					class="flex shrink-0 items-center gap-2 rounded-full bg-[#0C1550] px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-indigo-900/20 transition-all hover:scale-[1.02] hover:bg-indigo-900 disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:scale-100"
				>
					<PlayCircle class="h-4 w-4" />
					{overview.progress.completed_lessons > 0 ? 'Tiếp tục học' : 'Bắt đầu học'}
				</button>
			</div>

			<div class="relative mt-6">
				<div class="mb-1.5 flex items-center justify-between text-xs">
					<span class="font-medium text-slate-600">Tiến độ khóa học</span>
					<span class="font-semibold text-[#0C1550]">
						{overview.progress.completed_lessons}/{overview.progress.total_lessons} bài · {overview.progress.percent}%
					</span>
				</div>
				<div class="h-2 w-full overflow-hidden rounded-full bg-slate-100">
					<div
						class="h-full rounded-full bg-linear-to-r from-indigo-500 to-violet-500 transition-all duration-500"
						style={`width: ${overview.progress.percent}%`}
					></div>
				</div>
			</div>
		</div>

		<!-- THỐNG KÊ RIÊNG CỦA KHÓA HỌC NÀY -->
		<div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
			<div
				class="flex items-center gap-4 rounded-2xl border border-slate-200/70 bg-white p-5 shadow-sm shadow-slate-200/50"
			>
				<div class="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600">
					<ClipboardCheck class="h-5 w-5" />
				</div>
				<div>
					<p class="text-lg font-bold text-slate-900">
						{courseAverageScore !== null ? courseAverageScore.toFixed(1) : '—'}
					</p>
					<p class="text-xs text-slate-500">Điểm TB bài tập khóa này</p>
				</div>
			</div>

			<div
				class="flex items-center gap-4 rounded-2xl border border-slate-200/70 bg-white p-5 shadow-sm shadow-slate-200/50"
			>
				<div class="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-amber-50 text-amber-600">
					<AlertTriangle class="h-5 w-5" />
				</div>
				<div>
					<p class="text-lg font-bold text-slate-900">{totalPendingAssignments}</p>
					<p class="text-xs text-slate-500">Bài tập chưa nộp trong khóa</p>
				</div>
			</div>

			<div
				class="flex items-center gap-4 rounded-2xl border border-slate-200/70 bg-white p-5 shadow-sm shadow-slate-200/50"
			>
				<div class="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-rose-50 text-rose-600">
					<Target class="h-5 w-5" />
				</div>
				<div class="min-w-0">
					<p class="truncate text-sm font-bold text-slate-900">
						{weakestChapter ? `Chương ${weakestChapter.order}` : 'Chưa có dữ liệu'}
					</p>
					<p class="truncate text-xs text-slate-500">Chương cần ôn lại nhất</p>
				</div>
			</div>
		</div>

		<!-- GỢI Ý ÔN TẬP — chỉ hiện khi có chương yếu -->
		{#if weakestChapter && weakestChapter.average_score !== null && weakestChapter.average_score < 6}
			<div class="flex items-start gap-4 rounded-2xl border border-amber-200 bg-amber-50 p-5">
				<div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-amber-100 text-amber-600">
					<Lightbulb class="h-5 w-5" />
				</div>
				<div class="min-w-0 flex-1">
					<p class="text-sm font-semibold text-amber-900">Gợi ý ôn tập</p>
					<p class="mt-0.5 text-sm text-amber-800">
						Điểm trung bình <span class="font-semibold">{weakestChapter.title}</span> hiện đang
						là <span class="font-semibold">{weakestChapter.average_score.toFixed(1)}</span> —
						thấp hơn các chương khác. Hãy xem lại lý thuyết và làm thêm bài tập ôn luyện ở chương này.
					</p>
					<button
						onclick={() => goto(`/course/${overview.course.id}/chapter/${weakestChapter.id}`)}
						class="mt-3 inline-flex items-center gap-1.5 text-sm font-semibold text-amber-900 hover:underline"
					>
						Ôn lại chương này
						<ChevronRight class="h-3.5 w-3.5" />
					</button>
				</div>
			</div>
		{/if}

		<!-- TIẾN ĐỘ THEO CHƯƠNG -->
		<div>
			<h2 class="mb-4 text-base font-semibold text-slate-800" style="font-family:'Sora',sans-serif;">
				Chương trình học
			</h2>

			<div class="space-y-3">
				{#each overview.chapters as chapter (chapter.id)}
					{@const status = chapterStatus(chapter)}
					{@const percent = Math.round((chapter.completed_lessons / chapter.total_lessons) * 100)}
					<button
						onclick={() =>
							chapter.first_incomplete_lesson_id &&
							goto(`/course/${overview.course.id}/lesson/${chapter.first_incomplete_lesson_id}`)}
						class="group flex w-full items-center gap-4 rounded-2xl border border-slate-200/70 bg-white p-5 text-left shadow-sm shadow-slate-200/50 transition-all hover:-translate-y-0.5 hover:shadow-md"
					>
						<div
							class={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl
								${status === 'done' ? 'bg-emerald-50 text-emerald-600' : status === 'in_progress' ? 'bg-indigo-50 text-indigo-600' : 'bg-slate-100 text-slate-400'}`}
						>
							{#if status === 'done'}
								<CheckCircle2 class="h-5 w-5" />
							{:else if status === 'in_progress'}
								<Target class="h-5 w-5" />
							{:else}
								<Lock class="h-4 w-4" />
							{/if}
						</div>

						<div class="min-w-0 flex-1">
							<div class="flex items-center justify-between gap-3">
								<p class="truncate text-sm font-semibold text-slate-800">{chapter.title}</p>
								<div class="flex shrink-0 items-center gap-2">
									{#if chapter.pending_assignments > 0}
										<span class="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-600">
											{chapter.pending_assignments} bài tập chưa làm
										</span>
									{/if}
									{#if chapter.average_score !== null}
										<span class={`rounded-full px-2.5 py-1 text-xs font-semibold ${scoreTone(chapter.average_score)}`}>
											{chapter.average_score.toFixed(1)} điểm
										</span>
									{/if}
								</div>
							</div>

							<div class="mt-2 flex items-center gap-3">
								<div class="h-1.5 flex-1 overflow-hidden rounded-full bg-slate-100">
									<div
										class={`h-full rounded-full transition-all duration-500 ${status === 'done' ? 'bg-emerald-500' : 'bg-indigo-500'}`}
										style={`width: ${percent}%`}
									></div>
								</div>
								<span class="shrink-0 text-xs text-slate-400">
									{chapter.completed_lessons}/{chapter.total_lessons} bài
								</span>
							</div>
						</div>

						<ChevronRight class="h-4 w-4 shrink-0 text-slate-300 transition-transform group-hover:translate-x-0.5" />
					</button>
				{/each}
			</div>
		</div>
	</main>

	<Chatbot userName="" />
</div>