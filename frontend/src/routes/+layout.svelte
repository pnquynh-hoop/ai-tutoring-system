<script lang="ts">
	import './layout.css';
	import favicon from '$lib/assets/favicon.svg';
	import { auth } from '$lib/stores/auth.svelte';
	import ToastContainer from '$lib/components/ToastContainer.svelte';

	let { data, children } = $props();

	$effect(() => {
		auth.user = data.user;
	});
</script>

<svelte:head><link rel="icon" href={favicon} /></svelte:head>
{@render children()}
<ToastContainer />
