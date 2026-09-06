<script lang="ts">
	import katex from 'katex';
	import 'katex/dist/katex.min.css';
	import { parseMarkdown, type InlineToken } from '$lib/utils/markdown';

	interface Props {
		text: string;
	}

	let { text }: Props = $props();
	let blocks = $derived(parseMarkdown(text));

	const HTML_ESCAPES: Record<string, string> = {
		'&': '&amp;',
		'<': '&lt;',
		'>': '&gt;',
		'"': '&quot;',
		"'": '&#39;'
	};

	function renderMath(formula: string, display: boolean): string {
		try {
			return katex.renderToString(formula, { displayMode: display, throwOnError: false });
		} catch {
			return formula.replace(/[&<>"']/g, (character) => HTML_ESCAPES[character]);
		}
	}

	const headingSize: Record<number, string> = {
		1: 'text-base',
		2: 'text-[15px]',
		3: 'text-sm',
		4: 'text-sm',
		5: 'text-sm',
		6: 'text-sm'
	};
</script>

{#snippet inline(tokens: InlineToken[])}
	{#each tokens as token, index (index)}
		{#if token.kind === 'bold'}
			<strong class="font-semibold text-slate-900">{token.text}</strong>
		{:else if token.kind === 'italic'}
			<em class="italic">{token.text}</em>
		{:else if token.kind === 'code'}
			<code
				class="rounded bg-slate-100 px-1 py-0.5 font-mono text-[0.85em] text-brand-700 wrap-break-word"
			>
				{token.text}
			</code>
		{:else if token.kind === 'math'}
			{@html renderMath(token.text, token.display)}
		{:else}
			{token.text}
		{/if}
	{/each}
{/snippet}

<div class="space-y-2.5 text-sm leading-relaxed text-slate-700">
	{#each blocks as block, index (index)}
		{#if block.kind === 'heading'}
			<p class={`font-heading font-bold text-slate-900 ${headingSize[block.level] ?? 'text-sm'}`}>
				{@render inline(block.content)}
			</p>
		{:else if block.kind === 'bullets'}
			<ul class="ml-1 space-y-1.5">
				{#each block.items as item, itemIndex (itemIndex)}
					<li class="flex gap-2">
						<span class="mt-[0.45rem] h-1.5 w-1.5 shrink-0 rounded-full bg-brand-400"></span>
						<span class="min-w-0 flex-1">{@render inline(item)}</span>
					</li>
				{/each}
			</ul>
		{:else if block.kind === 'numbers'}
			<ol class="ml-1 space-y-1.5">
				{#each block.items as item, itemIndex (itemIndex)}
					<li class="flex gap-2">
						<span
							class="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-brand-50 text-[11px] font-semibold text-brand-700"
						>
							{itemIndex + 1}
						</span>
						<span class="min-w-0 flex-1">{@render inline(item)}</span>
					</li>
				{/each}
			</ol>
		{:else if block.kind === 'quote'}
			<blockquote class="border-l-2 border-brand-200 pl-3 text-slate-600 italic">
				{@render inline(block.content)}
			</blockquote>
		{:else if block.kind === 'code'}
			<pre
				class="overflow-x-auto rounded-lg bg-slate-900 px-3 py-2.5 font-mono text-xs leading-relaxed text-slate-100">{block.text}</pre>
		{:else if block.kind === 'rule'}
			<hr class="border-slate-200" />
		{:else}
			<p>{@render inline(block.content)}</p>
		{/if}
	{/each}
</div>

<style>
	:global(.katex-display) {
		margin: 0.35rem 0;
		overflow-x: auto;
		overflow-y: hidden;
	}
</style>
