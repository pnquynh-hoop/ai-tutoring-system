<script lang="ts">
	import { BadgeCheck } from 'lucide-svelte';

	interface Props {
		isRight: boolean;
		canEdit: boolean;
		isLoading: boolean;
		onToggle: () => void;
	}

	let { isRight, canEdit, isLoading, onToggle }: Props = $props();

	const circleClass = $derived(
		isRight ? 'bg-sky-600 text-white shadow-sm shadow-sky-200' : 'bg-slate-100 text-slate-400'
	);
</script>

{#if canEdit}
	<button
		onclick={onToggle}
		disabled={isLoading}
		class={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full transition-colors disabled:opacity-40 ${circleClass} ${!isRight ? 'hover:bg-slate-200' : ''}`}
		title="Đánh dấu đóng góp đúng"
	>
		<BadgeCheck class="h-4 w-4" />
	</button>
{:else}
	<span
		class={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full ${circleClass}`}
		title={isRight ? 'Đã được gia sư xác nhận đúng' : ''}
	>
		<BadgeCheck class="h-4 w-4" />
	</span>
{/if}
