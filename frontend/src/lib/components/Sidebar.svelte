<script lang="ts">
	import { goto } from '$app/navigation';
	import type { CourseTree, Student } from '$lib/api/entities';
	import { BookOpen, ChevronRight, Menu, Star } from 'lucide-svelte';
	import Avatar from './Avatar.svelte';

	interface Props {
		course: CourseTree;
		student: Student;
		activeLessonId: number | null;
	}
	let { course, student, activeLessonId }: Props = $props();

	let sidebarCollapsed = $state(false);
	let expandedChapterId = $state<number | null>(null);
</script>

<aside
	class={`flex h-full shrink-0 flex-col overflow-hidden bg-[#0C1550] text-white transition-all duration-300 ${sidebarCollapsed ? 'w-16' : 'w-72'}`}
>
	<div
		class={`flex items-center border-b border-white/10 py-6 ${sidebarCollapsed ? 'justify-center px-0' : 'justify-between px-5'}`}
	>
		{#if !sidebarCollapsed}
			<span class="truncate font-semibold tracking-tight" style="font-family:'Sora',sans-serif;">
				{course.name}
			</span>
		{/if}
		<button
			onclick={() => (sidebarCollapsed = !sidebarCollapsed)}
			class="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-white/10 hover:bg-white/20"
		>
			<Menu class="h-4 w-4 text-indigo-100/60" />
		</button>
	</div>

	{#if sidebarCollapsed}
		<div class="flex-1"></div>
	{:else}
		<nav class="flex-1 space-y-1 overflow-y-auto px-3 py-4">
			<!-- FIX: thêm key (chapter.id) -->
			{#each course.chapters as chapter (chapter.id)}
				<div>
					<button
						onclick={() =>
							(expandedChapterId = expandedChapterId === chapter.id ? null : chapter.id)}
						class={`flex w-full items-center gap-3 rounded-full px-4 py-2.5 text-sm transition-all
	                        ${expandedChapterId === chapter.id ? 'bg-white/10 font-semibold text-white' : 'text-indigo-100/55 hover:bg-white/5 hover:text-white'}`}
					>
						<BookOpen class="h-4 w-4 shrink-0 opacity-60" />
						<span class="flex-1 text-left">{chapter.title}</span>
						{#if chapter.lessons.length > 0}
							<ChevronRight
								class={`h-4 w-4 shrink-0 text-indigo-100/40 transition-transform ${expandedChapterId === chapter.id ? 'rotate-90' : ''}`}
							/>
						{/if}
					</button>

					{#if expandedChapterId === chapter.id && chapter.lessons.length > 0}
						<div class="relative ml-6 mt-1 space-y-0.5 pl-4">
							<div class="absolute left-0 top-0 bottom-2 w-px bg-white/10"></div>
							{#each chapter.lessons as lesson (lesson.id)}
								<button
									onclick={() => goto(`/course/${course.id}/lesson/${lesson.id}`)}
									class={`flex w-full items-center gap-2 rounded-full py-2 pl-3 pr-2 text-sm transition-all
                        ${activeLessonId === lesson.id ? 'bg-white/10 font-semibold text-white' : 'text-indigo-100/50 hover:bg-white/5 hover:text-white'}`}
								>
									{#if lesson.is_completed}
										<Star class="h-3.5 w-3.5 shrink-0 fill-amber-400 text-amber-400" />
									{/if}
									<span class="min-w-0 flex-1 truncate text-left">{lesson.title}</span>
									{#if activeLessonId === lesson.id}
										<ChevronRight class="ml-auto h-4 w-4 shrink-0 text-indigo-100/50" />
									{/if}
								</button>
							{/each}
						</div>
					{/if}
				</div>
			{/each}
		</nav>
	{/if}

	<div class={`border-t border-white/10 py-4 ${sidebarCollapsed ? 'px-0' : 'px-3'}`}>
		<div
			class={`flex items-center rounded-xl py-2 hover:bg-white/5 ${sidebarCollapsed ? 'justify-center px-0' : 'gap-3 px-2'}`}
		>
			<Avatar src={student.avatar} name={student.full_name} size="lg" />
			{#if !sidebarCollapsed}
				<div class="min-w-0 flex-1">
					<p class="truncate text-sm font-medium text-white">{student.full_name}</p>
					<p class="truncate text-xs text-indigo-100/50">Học sinh {student.grade}</p>
				</div>
			{/if}
		</div>
	</div>
</aside>
