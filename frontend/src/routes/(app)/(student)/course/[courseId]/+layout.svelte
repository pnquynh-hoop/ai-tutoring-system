<script lang="ts">
	import Sidebar from "$lib/components/Sidebar.svelte";

	let { data, children } = $props();
</script>

<div class="flex h-screen overflow-hidden bg-[#F5F6FA]">
	<Sidebar
		course={data.course_tree}
		student={data.user}
		activeLessonId={null}
	/>
	<div class="flex min-w-0 flex-1">
		{@render children()}
	</div>
</div>