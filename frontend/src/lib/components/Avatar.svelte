<script lang="ts">
	interface Props {
		src?: string | null;
		name: string;
		size?: 'sm' | 'md' | 'lg' | 'xl';
		fromColor?: string;
		toColor?: string;
	}

	let {
		src = null,
		name,
		size = 'md',
		fromColor = 'from-rose-400',
		toColor = 'to-orange-300'
	}: Props = $props();

	let imgError = $state(false);

	const sizeClasses: Record<NonNullable<Props['size']>, string> = {
		sm: 'h-7 w-7 text-[11px]',
		md: 'h-8 w-8 text-xs',
		lg: 'h-9 w-9 text-sm',
		xl: 'h-20 w-20 text-2xl'
	};

	const initial = $derived(name?.[0]?.toUpperCase() ?? '?');
	const showImage = $derived(!!src && !imgError);
</script>

{#if showImage}
	<img
		{src}
		alt={name}
		onerror={() => (imgError = true)}
		class={`${sizeClasses[size]} shrink-0 rounded-full object-cover`}
	/>
{:else}
	<div
		class={`flex ${sizeClasses[size]} shrink-0 items-center justify-center rounded-full bg-linear-to-tr ${fromColor} ${toColor} font-bold text-white`}
	>
		{initial}
	</div>
{/if}
