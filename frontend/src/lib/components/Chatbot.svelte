<script lang="ts">
	import { page } from '$app/state';
	import { askAI } from '$lib/api/calledAPI';
	import { getApiErrorMessage } from '$lib/api/errors';
	import type { RagSource } from '$lib/api/entities';
	import { formatSourceLabel, resolveChatContext } from '$lib/utils/chat';
	import { Bot, FileText, Send, Sparkles, X } from 'lucide-svelte';
	import AiMessage from './AiMessage.svelte';
	import FieldError from './FieldError.svelte';
	import { FIELD_LIMITS, textError } from '$lib/utils/validation';

	interface ChatMessage {
		id: number;
		role: 'user' | 'ai';
		text: string;
		sources?: RagSource[];
		grounded?: boolean;
	}

	interface Props {
		userName?: string;
	}

	let { userName = '' }: Props = $props();

	let isOpen = $state(false);
	let draft = $state('');
	let isThinking = $state(false);
	let draftError = $state('');
	let scrollEl = $state<HTMLDivElement | null>(null);

	let context = $derived(resolveChatContext(page.params));

	let messages = $state<ChatMessage[]>([]);

	const MIN_PANEL_WIDTH = 448;
	const PANEL_WIDTH_KEY = 'chat-panel-width';

	let panelWidth = $state(MIN_PANEL_WIDTH);
	let isResizing = $state(false);

	function clampPanelWidth(width: number) {
		const halfScreen = Math.round(window.innerWidth / 2);
		const maxWidth = Math.max(MIN_PANEL_WIDTH, halfScreen);
		return Math.min(Math.max(width, MIN_PANEL_WIDTH), maxWidth);
	}

	function resizePanel(event: PointerEvent) {
		panelWidth = clampPanelWidth(window.innerWidth - event.clientX);
	}

	function stopResizing() {
		isResizing = false;
		window.removeEventListener('pointermove', resizePanel);
		window.removeEventListener('pointerup', stopResizing);

		try {
			localStorage.setItem(PANEL_WIDTH_KEY, String(panelWidth));
		} catch {
			return;
		}
	}

	function startResizing(event: PointerEvent) {
		event.preventDefault();
		isResizing = true;
		window.addEventListener('pointermove', resizePanel);
		window.addEventListener('pointerup', stopResizing);
	}

	function storedPanelWidth() {
		try {
			return Number(localStorage.getItem(PANEL_WIDTH_KEY)) || MIN_PANEL_WIDTH;
		} catch {
			return MIN_PANEL_WIDTH;
		}
	}

	$effect(() => {
		panelWidth = clampPanelWidth(storedPanelWidth());

		const keepInsideScreen = () => {
			panelWidth = clampPanelWidth(panelWidth);
		};

		window.addEventListener('resize', keepInsideScreen);
		return () => window.removeEventListener('resize', keepInsideScreen);
	});

	const MOTIVATION_QUOTE = 'Một ngày mới, một cơ hội mới để tiến bộ. Bắt đầu thôi nào!';

	function greeting(): ChatMessage {
		return {
			id: Date.now(),
			role: 'ai',
			text: `Chào ${userName || 'bạn'} 👋 Mình là trợ lý học tập của trung tâm, sẵn sàng hỗ trợ bạn với những nội dung đang học. Bạn muốn hỏi gì hôm nay?`
		};
	}

	function toggleOpen() {
		isOpen = !isOpen;
		if (isOpen && messages.length === 0) messages = [greeting()];
	}

	function pushAi(text: string, sources?: RagSource[], grounded = true) {
		messages.push({
			id: Date.now() + Math.floor(performance.now()),
			role: 'ai',
			text,
			sources,
			grounded
		});
	}

	$effect(() => {
		void messages.length;
		void isThinking;
		scrollEl?.scrollTo({ top: scrollEl.scrollHeight, behavior: 'smooth' });
	});

	async function send(text?: string) {
		const content = (text ?? draft).trim();
		if (isThinking) return;

		draftError = textError(content, FIELD_LIMITS.aiQuestion, 'Câu hỏi');
		if (draftError) return;

		if (!context.courseId) {
			pushAi('Bạn chọn một khóa học trước để mình tìm đúng tài liệu nhé.');
			return;
		}

		messages.push({ id: Date.now(), role: 'user', text: content });
		draft = '';
		isThinking = true;

		try {
			const res = await askAI(content, context.courseId, context.lessonId ?? undefined);
			pushAi(res.answer, res.sources, res.grounded);
		} catch (err) {
			pushAi(getApiErrorMessage(err, 'Trợ lý AI chưa trả lời được, bạn thử lại nhé.'));
		} finally {
			isThinking = false;
		}
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter' && !event.shiftKey) {
			event.preventDefault();
			send();
		}
	}
</script>

{#if !isOpen}
	<div class="fixed bottom-8 right-8 z-50">
		<div class="group relative">
			<div
				class="pointer-events-none absolute bottom-full right-0 mb-3 whitespace-nowrap rounded-2xl border border-brand-100 bg-white px-5 py-3 text-sm font-bold text-brand-600 opacity-0 shadow-xl shadow-brand-100/50 transition-opacity duration-200 group-hover:opacity-100"
			>
				Chào {userName || 'bạn'}! Mỗi câu hỏi bạn đặt ra là một bước tiến trên hành trình học tập
				đấy.? 👋
			</div>

			<button
				onclick={toggleOpen}
				aria-label="Mở trợ lý AI"
				class="flex h-16 w-16 items-center justify-center rounded-full bg-linear-to-br from-indigo-400 to-indigo-700 text-white shadow-xl shadow-indigo-500/45 ring-1 ring-white/15 transition-all duration-300 hover:scale-110 hover:shadow-2xl hover:shadow-indigo-500/60"
			>
				<Bot class="h-8 w-8 animate-bounce" />
			</button>
		</div>
	</div>
{/if}

{#if isOpen}
	<aside
		style={`width: ${panelWidth}px`}
		class={`fixed right-0 top-0 z-40 flex h-full max-w-full flex-col border-l border-slate-200 bg-white shadow-2xl shadow-slate-300/50 ${
			isResizing ? 'select-none' : ''
		}`}
	>
		<div
			role="separator"
			aria-orientation="vertical"
			aria-label="Kéo để đổi bề rộng khung chat"
			onpointerdown={startResizing}
			class={`absolute left-0 top-0 h-full w-1.5 cursor-col-resize transition-colors hover:bg-brand-300 ${
				isResizing ? 'bg-brand-400' : 'bg-transparent'
			}`}
		></div>

		<header class="flex items-center gap-3 border-b border-slate-100 px-5 py-4">
			<div class="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-600 text-white">
				<Sparkles class="h-5 w-5" />
			</div>
			<div class="min-w-0 flex-1">
				<p class="text-sm font-bold text-slate-800 font-heading">Trợ lý AI</p>
				<p class="truncate text-xs text-slate-400">Đi chậm vẫn tốt hơn đứng yên.</p>
			</div>
			<button
				onclick={() => (isOpen = false)}
				aria-label="Đóng"
				class="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
			>
				<X class="h-4 w-4" />
			</button>
		</header>

		<div bind:this={scrollEl} class="flex-1 space-y-4 overflow-y-auto bg-slate-50 px-5 py-4">
			{#each messages as message (message.id)}
				<div class={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
					<div
						class={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm ${
							message.role === 'user'
								? 'bg-brand-600 text-white'
								: 'border border-slate-200/70 bg-white text-slate-700'
						}`}
					>
						{#if message.role === 'user'}
							<p class="whitespace-pre-wrap">{message.text}</p>
						{:else}
							<AiMessage text={message.text} />
						{/if}

						{#if message.role === 'ai' && message.grounded === false}
							<p
								class="mt-2.5 rounded-lg bg-amber-50 px-2 py-1 text-[11px] font-medium text-amber-700"
							>
								Kiến thức chung, không trích từ tài liệu khóa học
							</p>
						{/if}

						{#if message.sources?.length}
							<div class="mt-2.5 space-y-1 border-t border-slate-100 pt-2">
								<p class="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
									Nguồn tham khảo
								</p>
								{#each message.sources as source (source.title + source.page)}
									<p class="flex items-start gap-1.5 text-[11px] text-slate-500">
										<FileText class="mt-px h-3 w-3 shrink-0 text-slate-400" />
										<span class="min-w-0 flex-1">{formatSourceLabel(source)}</span>
									</p>
								{/each}
							</div>
						{/if}
					</div>
				</div>
			{/each}

			{#if isThinking}
				<div class="flex justify-start">
					<div
						class="rounded-2xl border border-slate-200/70 bg-white px-4 py-2.5 text-sm text-slate-400"
					>
						Đang tra cứu tài liệu...
					</div>
				</div>
			{/if}
		</div>

		{#if messages.length <= 1}
			<div class="border-t border-slate-100 px-5 py-3">
				<p class="text-center text-xs italic text-slate-500">
					“{MOTIVATION_QUOTE}”
				</p>
			</div>
		{/if}

		<div class="flex items-end gap-2 border-t border-slate-100 px-5 py-4">
			<textarea
				rows="1"
				bind:value={draft}
				oninput={() => (draftError = '')}
				onkeydown={handleKeydown}
				placeholder="Nhập câu hỏi của bạn..."
				class="max-h-28 min-h-9.5 flex-1 resize-none rounded-2xl border border-slate-200 px-4 py-2 text-sm outline-none focus:border-brand-300"
			></textarea>
			<button
				onclick={() => send()}
				disabled={!draft.trim() || isThinking}
				aria-label="Gửi câu hỏi"
				class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-brand-600 text-white transition-colors hover:bg-brand-700 disabled:opacity-40"
			>
				<Send class="h-4 w-4" />
			</button>
		</div>
		<div class="px-5 pb-3"><FieldError message={draftError} /></div>
	</aside>
{/if}
