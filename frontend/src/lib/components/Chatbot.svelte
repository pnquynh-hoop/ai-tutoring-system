<script lang="ts">
	import { page } from '$app/state';
	import { askAI, getListCourses } from '$lib/api/calledAPI';
	import { getApiErrorMessage } from '$lib/api/errors';
	import type { Course, RagSource } from '$lib/api/entities';
	import { formatSourceLabel, resolveChatContext } from '$lib/utils/chat';
	import { Bot, Send, Sparkles, X } from 'lucide-svelte';

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
	let scrollEl = $state<HTMLDivElement | null>(null);

	let routeCourseId = $derived(Number(page.params.courseId) || null);

	let courses = $state<Course[]>([]);
	let pickedCourseId = $state<number | null>(null);
	let context = $derived(resolveChatContext(page.params, pickedCourseId));

	let messages = $state<ChatMessage[]>([]);

	const suggestions = [
		'Tóm tắt nội dung bài học này',
		'Giải thích lại phần lý thuyết cho dễ hiểu',
		'Cho mình một ví dụ minh hoạ'
	];

	function greeting(): ChatMessage {
		return {
			id: Date.now(),
			role: 'ai',
			text: `Chào ${userName || 'bạn'} 👋 Mình trả lời dựa trên tài liệu bài học và sách giáo khoa của khóa học. Bạn muốn hỏi gì?`
		};
	}

	async function toggleOpen() {
		isOpen = !isOpen;
		if (!isOpen) return;

		if (messages.length === 0) messages = [greeting()];

		if (!routeCourseId && courses.length === 0) {
			try {
				courses = await getListCourses();
				pickedCourseId = courses[0]?.id ?? null;
			} catch (err) {
				pushAi(getApiErrorMessage(err, 'Không tải được danh sách khóa học.'));
			}
		}
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
		if (!content || isThinking) return;

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
				Chào {userName || 'bạn'}! Mình giúp gì được bạn? 👋
			</div>

			<button
				onclick={toggleOpen}
				aria-label="Mở trợ lý AI"
				class="flex h-16 w-16 items-center justify-center rounded-full bg-blue-700 text-white shadow-xl shadow-brand-900/40 transition-all hover:scale-110 hover:bg-blue-800"
			>
				<Bot class="h-8 w-8 animate-bounce" />
			</button>
		</div>
	</div>
{/if}

{#if isOpen}
	<aside
		class="fixed right-0 top-0 z-40 flex h-full w-full max-w-md flex-col border-l border-slate-200 bg-white shadow-2xl shadow-slate-300/50"
		style="font-family:'Inter',sans-serif;"
	>
		<header class="flex items-center gap-3 border-b border-slate-100 px-5 py-4">
			<div class="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-950 text-white">
				<Sparkles class="h-5 w-5" />
			</div>
			<div class="min-w-0 flex-1">
				<p class="text-sm font-bold text-slate-800" style="font-family:'Sora',sans-serif;">
					Trợ lý AI
				</p>
				<p class="truncate text-xs text-slate-400">
					{context.lessonId ? 'Đang hỏi theo bài học hiện tại' : 'Đang hỏi theo cả khóa học'}
				</p>
			</div>
			<button
				onclick={() => (isOpen = false)}
				aria-label="Đóng"
				class="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
			>
				<X class="h-4 w-4" />
			</button>
		</header>

		{#if !routeCourseId}
			<div class="border-b border-slate-100 px-5 py-3">
				<label class="block">
					<span class="mb-1 block text-xs font-medium text-slate-500">Khóa học</span>
					<select
						bind:value={pickedCourseId}
						class="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-sm outline-none focus:border-brand-300"
					>
						{#each courses as course (course.id)}
							<option value={course.id}>{course.name}</option>
						{/each}
					</select>
				</label>
				{#if courses.length === 0}
					<p class="mt-2 text-xs text-amber-600">
						Bạn chưa ghi danh khóa học nào nên trợ lý chưa có tài liệu để trả lời.
					</p>
				{/if}
			</div>
		{/if}

		<div bind:this={scrollEl} class="flex-1 space-y-4 overflow-y-auto bg-slate-50 px-5 py-4">
			{#each messages as message (message.id)}
				<div class={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
					<div
						class={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm ${
							message.role === 'user'
								? 'bg-brand-950 text-white'
								: 'border border-slate-200/70 bg-white text-slate-700'
						}`}
					>
						<p class="whitespace-pre-wrap">{message.text}</p>

						{#if message.role === 'ai' && message.grounded === false}
							<p
								class="mt-2 rounded-lg bg-amber-50 px-2 py-1 text-[11px] font-medium text-amber-700"
							>
								Kiến thức chung, không trích từ tài liệu khóa học
							</p>
						{/if}

						{#if message.sources?.length}
							<div class="mt-2 border-t border-slate-100 pt-2">
								<p class="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
									Nguồn tham khảo
								</p>
								{#each message.sources as source (source.title + source.page)}
									<p class="text-[11px] text-slate-500">{formatSourceLabel(source)}</p>
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
			<div class="flex flex-wrap gap-2 border-t border-slate-100 px-5 py-3">
				{#each suggestions as suggestion (suggestion)}
					<button
						onclick={() => send(suggestion)}
						class="rounded-full border border-slate-200 px-3 py-1 text-xs text-slate-600 hover:bg-slate-50"
					>
						{suggestion}
					</button>
				{/each}
			</div>
		{/if}

		<div class="flex items-end gap-2 border-t border-slate-100 px-5 py-4">
			<textarea
				rows="1"
				bind:value={draft}
				onkeydown={handleKeydown}
				placeholder="Nhập câu hỏi của bạn..."
				class="max-h-28 min-h-[38px] flex-1 resize-none rounded-2xl border border-slate-200 px-4 py-2 text-sm outline-none focus:border-brand-300"
			></textarea>
			<button
				onclick={() => send()}
				disabled={!draft.trim() || isThinking}
				aria-label="Gửi câu hỏi"
				class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-brand-950 text-white transition-colors hover:bg-brand-800 disabled:opacity-40"
			>
				<Send class="h-4 w-4" />
			</button>
		</div>
	</aside>
{/if}
