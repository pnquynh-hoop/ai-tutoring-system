<script lang="ts">
	import { goto } from '$app/navigation';
	import Avatar from '$lib/components/Avatar.svelte';
	import { ArrowLeft, BarChart3, BookOpen, ClipboardCheck, Users } from 'lucide-svelte';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	let courseId = $derived(data.courseId);
	let stats = $derived(data.stats);

	let gradedTotal = $derived(stats.assignments.reduce((sum, a) => sum + a.graded_count, 0));
	let pendingTotal = $derived(stats.assignments.reduce((sum, a) => sum + a.pending_count, 0));

	let quickStats = $derived([
		{ label: 'Học sinh đang học', value: String(stats.total_students), icon: Users, tone: 'navy' },
		{
			label: 'Bài học trong khóa',
			value: String(stats.total_lessons),
			icon: BookOpen,
			tone: 'slate'
		},
		{ label: 'Bài chờ chấm', value: String(pendingTotal), icon: ClipboardCheck, tone: 'amber' }
	]);

	function formatDate(iso: string): string {
		return new Date(iso).toLocaleDateString('vi-VN', {
			day: '2-digit',
			month: '2-digit',
			year: 'numeric'
		});
	}
</script>

<svelte:head>
	<link rel="preconnect" href="https://fonts.googleapis.com" />
	<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="" />
	<link
		href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Sora:wght@600;700;800&display=swap"
		rel="stylesheet"
	/>
	<title>Thống kê khóa học</title>
</svelte:head>

<div class="min-h-screen bg-slate-50" style="font-family:'Inter',sans-serif;">
	<header
		class="flex items-center justify-between border-b border-slate-200/70 bg-white/80 px-8 py-4 backdrop-blur"
	>
		<button
			onclick={() => goto(`/course-mgt/${courseId}`)}
			class="flex items-center gap-2 rounded-full bg-slate-100 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-200"
		>
			<ArrowLeft class="h-4 w-4" />
			Về cây khóa học
		</button>
		<span class="flex items-center gap-1.5 text-sm font-medium text-slate-500">
			<BarChart3 class="h-4 w-4" />
			{data.course.name}
		</span>
	</header>

	<main class="px-8 py-8">
		<div class="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
			{#each quickStats as stat (stat.label)}
				<div
					class="flex items-center gap-4 rounded-2xl border border-slate-200/70 bg-white p-5 shadow-sm shadow-slate-200/50"
				>
					<div
						class={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl
							${stat.tone === 'navy' ? 'bg-brand-950/5 text-brand-950' : ''}
							${stat.tone === 'slate' ? 'bg-slate-100 text-slate-600' : ''}
							${stat.tone === 'amber' ? 'bg-amber-50 text-amber-600' : ''}`}
					>
						<stat.icon class="h-5 w-5" />
					</div>
					<div>
						<p class="text-lg font-bold text-slate-900">{stat.value}</p>
						<p class="text-xs text-slate-500">{stat.label}</p>
					</div>
				</div>
			{/each}
		</div>

		<div
			class="mb-8 rounded-2xl border border-slate-200/70 bg-white p-6 shadow-sm shadow-slate-200/50"
		>
			<h2 class="mb-4 text-sm font-semibold text-slate-800" style="font-family:'Sora',sans-serif;">
				Tiến độ học sinh
			</h2>

			<div class="space-y-3">
				{#each stats.students as student (student.id)}
					<div class="flex items-center gap-4 rounded-xl border border-slate-100 bg-slate-50 p-3">
						<Avatar src={student.avatar} name={student.full_name} size="md" />
						<div class="min-w-0 flex-1">
							<p class="truncate text-sm font-medium text-slate-700">{student.full_name}</p>
							<div class="mt-1.5 flex items-center gap-3">
								<div class="h-1.5 w-40 overflow-hidden rounded-full bg-slate-200">
									<div
										class="h-full rounded-full bg-brand-950"
										style={`width:${student.progress}%`}
									></div>
								</div>
								<span class="text-xs text-slate-500">
									{student.completed_lessons}/{student.total_lessons} bài · {student.progress}%
								</span>
							</div>
						</div>
						<div class="shrink-0 text-right">
							<p class="text-sm font-bold text-slate-800">
								{student.average_score ?? '--'}
							</p>
							<p class="text-[11px] text-slate-400">Điểm TB</p>
						</div>
					</div>
				{/each}

				{#if stats.students.length === 0}
					<p class="py-10 text-center text-sm text-slate-400">
						Chưa có học sinh nào ghi danh khóa học này.
					</p>
				{/if}
			</div>
		</div>

		<div class="rounded-2xl border border-slate-200/70 bg-white p-6 shadow-sm shadow-slate-200/50">
			<div class="mb-4 flex items-center justify-between">
				<h2 class="text-sm font-semibold text-slate-800" style="font-family:'Sora',sans-serif;">
					Bài tập theo chương
				</h2>
				<span class="text-xs text-slate-400">Đã chấm {gradedTotal} bài</span>
			</div>

			<div class="overflow-x-auto">
				<table class="w-full min-w-[640px] text-left text-sm">
					<thead>
						<tr class="border-b border-slate-100 text-xs uppercase tracking-wider text-slate-400">
							<th class="pb-2 font-medium">Bài tập</th>
							<th class="pb-2 font-medium">Chương</th>
							<th class="pb-2 font-medium">Hạn nộp</th>
							<th class="pb-2 text-center font-medium">Đã nộp</th>
							<th class="pb-2 text-center font-medium">Chờ chấm</th>
							<th class="pb-2 text-right font-medium">Điểm TB</th>
						</tr>
					</thead>
					<tbody>
						{#each stats.assignments as assignment (assignment.id)}
							<tr class="border-b border-slate-50 last:border-0">
								<td class="py-3 font-medium text-slate-700">{assignment.title}</td>
								<td class="py-3 text-slate-500">{assignment.chapter_title}</td>
								<td class="py-3 text-slate-500">{formatDate(assignment.due_date)}</td>
								<td class="py-3 text-center text-slate-600">{assignment.submitted_count}</td>
								<td class="py-3 text-center">
									{#if assignment.pending_count > 0}
										<span
											class="rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-700"
										>
											{assignment.pending_count}
										</span>
									{:else}
										<span class="text-xs text-slate-400">0</span>
									{/if}
								</td>
								<td class="py-3 text-right font-semibold text-slate-800">
									{assignment.average_score ?? '--'}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>

				{#if stats.assignments.length === 0}
					<p class="py-10 text-center text-sm text-slate-400">Khóa học chưa có bài tập nào.</p>
				{/if}
			</div>
		</div>
	</main>
</div>
