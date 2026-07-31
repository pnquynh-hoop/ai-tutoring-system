<script lang="ts">
	import { CheckCircle, CircleAlert, Info } from 'lucide-svelte';
	import { getToasts } from '$lib/stores/toast.svelte';

	const toasts = getToasts();

	const styles = {
		success: {
			bg: 'bg-emerald-600',
			icon: CheckCircle
		},
		error: {
			bg: 'bg-red-600',
			icon: CircleAlert
		},
		info: {
			bg: 'bg-sky-600',
			icon: Info
		}
	};
</script>

<div class="fixed right-5 top-5 z-50 space-y-3">
	{#each toasts as toast (toast.id)}
		{@const style = styles[toast.type]}
		<div
			class={`flex min-w-80 items-center gap-3 rounded-xl px-4 py-3 text-white shadow-xl ${style.bg}`}
		>
			<style.icon class="h-5 w-5 shrink-0" />
			<p class="flex-1 text-sm">{toast.message}</p>
		</div>
	{/each}
</div>
