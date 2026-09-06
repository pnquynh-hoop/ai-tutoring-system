<script lang="ts">
	import { page } from '$app/state';
	import Sidebar from '$lib/components/Sidebar.svelte';

	let { data, children } = $props();

	let onTakingAttempt = $derived(page.url.pathname.endsWith('/taking'));
	let activeLessonId = $derived(page.params.lessonId ? Number(page.params.lessonId) : null);
</script>

<div class="flex h-screen overflow-hidden bg-slate-50">
	<Sidebar
		course={data.course_tree}
		student={data.user}
		{activeLessonId}
		forceCollapsed={onTakingAttempt}
	/>
	<div class="flex min-w-0 flex-1">
		{@render children()}
	</div>
</div>
