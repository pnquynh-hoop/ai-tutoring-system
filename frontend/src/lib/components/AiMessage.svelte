<script lang="ts">
	import { renderMarkdown } from '$lib/utils/markdown';

	interface Props {
		text: string;
	}

	let { text }: Props = $props();
	let html = $derived(renderMarkdown(text));
</script>

<div class="ai-markdown overflow-x-auto text-sm leading-relaxed text-slate-700">
	<!-- eslint-disable-next-line svelte/no-at-html-tags -->
	{@html html}
</div>

<style>
	.ai-markdown :global(p),
	.ai-markdown :global(ul),
	.ai-markdown :global(ol),
	.ai-markdown :global(blockquote),
	.ai-markdown :global(pre),
	.ai-markdown :global(table) {
		margin: 0.625rem 0;
	}

	.ai-markdown :global(> :first-child) {
		margin-top: 0;
	}

	.ai-markdown :global(> :last-child) {
		margin-bottom: 0;
	}

	.ai-markdown :global(h1),
	.ai-markdown :global(h2),
	.ai-markdown :global(h3),
	.ai-markdown :global(h4),
	.ai-markdown :global(h5),
	.ai-markdown :global(h6) {
		margin: 0.875rem 0 0.35rem;
		font-family: var(--font-heading);
		font-weight: 700;
		color: var(--color-slate-900);
		font-size: 0.875rem;
	}

	.ai-markdown :global(h1) {
		font-size: 1rem;
	}

	.ai-markdown :global(h2) {
		font-size: 0.9375rem;
	}

	.ai-markdown :global(strong) {
		font-weight: 600;
		color: var(--color-slate-900);
	}

	.ai-markdown :global(em) {
		font-style: italic;
	}

	.ai-markdown :global(a) {
		color: var(--color-brand-600);
		font-weight: 500;
		text-decoration: underline;
		text-underline-offset: 2px;
	}

	.ai-markdown :global(a:hover) {
		color: var(--color-brand-700);
	}

	.ai-markdown :global(ul),
	.ai-markdown :global(ol) {
		list-style: none;
		padding: 0;
	}

	.ai-markdown :global(li) {
		margin: 0.375rem 0;
	}

	.ai-markdown :global(ul > li) {
		position: relative;
		padding-left: 1rem;
	}

	.ai-markdown :global(ul > li)::before {
		content: '';
		position: absolute;
		left: 0;
		top: 0.55rem;
		height: 0.375rem;
		width: 0.375rem;
		border-radius: 9999px;
		background: var(--color-brand-400);
	}

	.ai-markdown :global(ol) {
		counter-reset: item;
	}

	.ai-markdown :global(ol > li) {
		counter-increment: item;
		position: relative;
		padding-left: 1.75rem;
	}

	.ai-markdown :global(ol > li)::before {
		content: counter(item);
		position: absolute;
		left: 0;
		top: 0.1rem;
		display: flex;
		height: 1.25rem;
		width: 1.25rem;
		align-items: center;
		justify-content: center;
		border-radius: 9999px;
		background: var(--color-brand-50);
		color: var(--color-brand-700);
		font-size: 11px;
		font-weight: 600;
	}

	.ai-markdown :global(li > ul),
	.ai-markdown :global(li > ol) {
		margin: 0.375rem 0 0;
		padding-left: 0.5rem;
	}

	.ai-markdown :global(blockquote) {
		border-left: 2px solid var(--color-brand-200);
		padding-left: 0.75rem;
		color: var(--color-slate-600);
		font-style: italic;
	}

	.ai-markdown :global(code) {
		border-radius: 0.25rem;
		background: var(--color-slate-100);
		padding: 0.1rem 0.25rem;
		font-family: ui-monospace, monospace;
		font-size: 0.85em;
		color: var(--color-brand-700);
		overflow-wrap: break-word;
	}

	.ai-markdown :global(pre) {
		overflow-x: auto;
		border-radius: 0.5rem;
		background: var(--color-slate-900);
		padding: 0.625rem 0.75rem;
	}

	.ai-markdown :global(pre code) {
		background: transparent;
		padding: 0;
		font-size: 12px;
		color: var(--color-slate-100);
	}

	.ai-markdown :global(table) {
		width: 100%;
		table-layout: auto;
		border-collapse: collapse;
		font-size: 12px;
	}

	.ai-markdown :global(th),
	.ai-markdown :global(td) {
		border: 1px solid var(--color-slate-200);
		padding: 0.35rem 0.5rem;
		text-align: left;
		overflow-wrap: break-word;
	}

	.ai-markdown :global(th) {
		background: var(--color-slate-50);
		font-weight: 600;
		color: var(--color-slate-700);
	}

	.ai-markdown :global(hr) {
		margin: 0.75rem 0;
		border: 0;
		border-top: 1px solid var(--color-slate-200);
	}
</style>
