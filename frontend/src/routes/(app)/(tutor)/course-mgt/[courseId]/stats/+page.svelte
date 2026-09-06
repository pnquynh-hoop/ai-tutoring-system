<script lang="ts">
	import Avatar from '$lib/components/Avatar.svelte';
	import { BookOpen, ClipboardCheck, Users } from 'lucide-svelte';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	let stats = $derived(data.stats);

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
	<title>Thống kê khóa học</title>
</svelte:head>

<div class="px-8 py-8">
	<div class="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
		{#each quickStats as stat (stat.label)}
			<div
				class="flex items-center gap-4 rounded-2xl border border-slate-200/70 bg-white p-5 shadow-sm shadow-slate-200/50"
			>
				<div
					class={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl
							${stat.tone === 'navy' ? 'bg-brand-50 text-brand-600' : ''}
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
		<h2 class="mb-4 text-sm font-semibold text-slate-800 font-heading">Tiến độ học sinh</h2>

		<div class="space-y-3">
			{#each stats.students as student (student.id)}
				<div class="flex items-center gap-4 rounded-xl border border-slate-200 bg-white p-3">
					<Avatar src={student.avatar} name={student.full_name} size="md" />
					<div class="min-w-0 flex-1">
						<p class="truncate text-sm font-medium text-slate-700">{student.full_name}</p>
						<div class="mt-1.5 flex items-center gap-3">
							<div class="h-1.5 w-40 overflow-hidden rounded-full bg-slate-200">
								<div
									class="h-full rounded-full bg-brand-600"
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
			<h2 class="text-sm font-semibold text-slate-800 font-heading">Bài tập theo chương</h2>
		</div>

		<div class="overflow-x-auto">
			<table class="w-full min-w-160 text-left text-sm">
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
</div>
