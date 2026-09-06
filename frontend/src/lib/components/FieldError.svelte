<script lang="ts">
	interface Props {
		message?: string;
		tone?: 'light' | 'dark';
	}

	let { message = '', tone = 'light' }: Props = $props();
</script>

{#if message}
	<p class={`mt-1 text-xs ${tone === 'dark' ? 'text-rose-300' : 'text-rose-600'}`}>
		{message}
	</p>
{/if}
