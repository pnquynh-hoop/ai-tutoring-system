<script lang="ts">
	import { Bot } from 'lucide-svelte';

	interface Props {
		userName?: string;
		greeting?: string;
		onclick?: () => void;
	}

	let {
		userName = '',
		greeting = `Chào ${userName}! Mình giúp gì được bạn? 👋`,
		onclick
	}: Props = $props();
</script>

<div class="fixed bottom-8 right-8 z-50">
	<div class="group relative">
		<div
			class="pointer-events-none absolute bottom-full right-0 mb-3 whitespace-nowrap rounded-2xl border border-indigo-100 bg-white px-5 py-3 text-sm font-bold text-indigo-600 opacity-0 shadow-xl shadow-indigo-100/50 transition-opacity duration-200 group-hover:opacity-100"
		>
			{greeting}
		</div>

		<button
			{onclick}
			class="flex h-16 w-16 items-center justify-center rounded-full bg-blue-700 text-white shadow-xl shadow-indigo-900/40 transition-all hover:scale-110 hover:bg-blue-800"
		>
			<Bot class="h-8 w-8 animate-bounce" />
		</button>
	</div>
</div>