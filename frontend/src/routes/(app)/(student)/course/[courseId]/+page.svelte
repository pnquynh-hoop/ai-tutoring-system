<script lang="ts">
	import { goto } from '$app/navigation';
	import {
		Home,
		ChevronRight,
		Target,
		ClipboardCheck,
		AlertTriangle,
		BadgeCheck,
		Lock,
		CheckCircle2
	} from 'lucide-svelte';
	import Avatar from '$lib/components/Avatar.svelte';
	import Chatbot from '$lib/components/Chatbot.svelte';
	import type { PageData } from './$types';
	import type { ChapterStat } from '$lib/api/types';
	let { data }: { data: PageData } = $props();

	let course = $derived(data.course);
	let overview = $derived(data.course_overview);
	let chapterStats = $derived(data.chapter_stats);

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
	<title>{course.name}</title>
</svelte:head>

<div class="flex h-full min-h-0 flex-1 flex-col" style="font-family:'Inter',sans-serif;">
	<header
		class="flex items-center justify-between gap-4 border-b border-slate-200/70 bg-white/80 px-8 py-4 backdrop-blur"
	>
		<nav class="flex min-w-0 flex-1 items-center gap-2 text-sm text-slate-500">
			<span class="min-w-0 truncate font-semibold text-[#0C1550]">{course.name}</span>
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
							{course.subject_name}
						</span>
						<span class="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
							Khối {course.grade}
						</span>
					</div>

					<h1 class="mb-2 text-2xl font-bold text-slate-900" style="font-family:'Sora',sans-serif;">
						{course.name}
					</h1>

					<p class="mb-3 text-sm leading-relaxed text-slate-500">
						{course.description}
					</p>

					{#if course.tutor}
						<div
							class="mt-4 flex items-start gap-3 rounded-xl border border-slate-200/70 bg-slate-50/60 p-3"
						>
							<Avatar src={course.tutor.avatar} name={course.tutor.full_name} size="lg" />

							<div class="min-w-0">
								<div class="flex flex-wrap items-center gap-2">
									<p class="text-sm font-semibold text-slate-900">{course.tutor.full_name}</p>
									{#if course.tutor.tutor_profile?.is_verified}
										<span
											class="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-semibold text-emerald-600"
										>
											<BadgeCheck class="h-3 w-3" />
											Đã xác minh
										</span>
									{/if}
								</div>

								<p class="mt-0.5 text-xs text-slate-500">
									{course.tutor.tutor_profile?.qualification ?? 'Gia sư phụ trách'}
									{#if course.tutor.tutor_profile?.experience_years}
										· {course.tutor.tutor_profile.experience_years} năm kinh nghiệm
									{/if}
								</p>

								{#if course.tutor.tutor_profile?.bio}
									<p class="mt-1.5 text-xs leading-relaxed text-slate-500">
										{course.tutor.tutor_profile.bio}
									</p>
								{/if}
							</div>
						</div>
					{:else}
						<p class="mt-4 text-xs text-slate-400">Chưa phân công gia sư phụ trách</p>
					{/if}
				</div>
			</div>

			<div class="relative mt-6">
				<div class="mb-1.5 flex items-center justify-between text-xs">
					<span class="font-medium text-slate-600">Tiến độ khóa học</span>
					<span class="font-semibold text-[#0C1550]">
						{overview.progress.completed_lessons}/{overview.progress.total_lessons} bài · {overview
							.progress.progress_percent}%
					</span>
				</div>
				<div class="h-2 w-full overflow-hidden rounded-full bg-slate-100">
					<div
						class="h-full rounded-full bg-linear-to-r from-indigo-500 to-violet-500 transition-all duration-500"
						style={`width: ${overview.progress.progress_percent}%`}
					></div>
				</div>
			</div>
		</div>

		<!-- THỐNG KÊ RIÊNG CỦA KHÓA HỌC NÀY -->
		<div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
			<div
				class="flex items-center gap-4 rounded-2xl border border-slate-200/70 bg-white p-5 shadow-sm shadow-slate-200/50"
			>
				<div
					class="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600"
				>
					<ClipboardCheck class="h-5 w-5" />
				</div>
				<div>
					<p class="text-lg font-bold text-slate-900">
						{overview.average_score !== null ? overview.average_score.toFixed(1) : '—'}
					</p>
					<p class="text-xs text-slate-500">Điểm TB bài tập khóa này</p>
				</div>
			</div>

			<div
				class="flex items-center gap-4 rounded-2xl border border-slate-200/70 bg-white p-5 shadow-sm shadow-slate-200/50"
			>
				<div
					class="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-amber-50 text-amber-600"
				>
					<AlertTriangle class="h-5 w-5" />
				</div>
				<div>
					<p class="text-lg font-bold text-slate-900">{overview.pending_assignments_count}</p>
					<p class="text-xs text-slate-500">Bài tập chưa nộp trong khóa</p>
				</div>
			</div>
		</div>

		<!-- GỢI Ý ÔN TẬP — chỉ hiện khi có chương yếu -->
		<!-- {#if weakestChapter && weakestChapter.score !== null && weakestChapter.score < 6}
			<div class="flex items-start gap-4 rounded-2xl border border-amber-200 bg-amber-50 p-5">
				<div
					class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-amber-100 text-amber-600"
				>
					<Lightbulb class="h-5 w-5" />
				</div>
				<div class="min-w-0 flex-1">
					<p class="text-sm font-semibold text-amber-900">Gợi ý ôn tập</p>
					<p class="mt-0.5 text-sm text-amber-800">
						Điểm trung bình <span class="font-semibold">{weakestChapter.title}</span> hiện đang là
						<span class="font-semibold">{weakestChapter.score.toFixed(1)}</span> — thấp hơn các
						chương khác. Hãy xem lại lý thuyết và làm thêm bài tập ôn luyện ở chương này.
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
		{/if} -->

		<!-- TIẾN ĐỘ THEO CHƯƠNG -->
		<div>
			<h2
				class="mb-4 text-base font-semibold text-slate-800"
				style="font-family:'Sora',sans-serif;"
			>
				Chương trình học
			</h2>

			<div class="space-y-3">
				{#each chapterStats as chapter (chapter.id)}
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
										<span
											class="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-600"
										>
											{chapter.pending_assignments} bài tập chưa làm
										</span>
									{/if}
									{#if chapter.score !== null}
										<span
											class={`rounded-full px-2.5 py-1 text-xs font-semibold ${scoreTone(chapter.score)}`}
										>
											{chapter.score.toFixed(1)} điểm
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
						<ChevronRight
							class="h-4 w-4 shrink-0 text-slate-300 transition-transform group-hover:translate-x-0.5"
						/>
					</button>
				{/each}
			</div>
		</div>
	</main>

	<Chatbot userName="" />
</div>
