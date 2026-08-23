<script lang="ts">
	import { goto } from '$app/navigation';
	import { askAI, getCourseTree, logoutApi } from '$lib/api/calledAPI';
	import { getApiErrorMessage } from '$lib/api/errors';
	import type { Chapter } from '$lib/api/entities';
	import { auth } from '$lib/stores/auth.svelte';
	import type { PageProps } from './$types';
	import {
		History,
		Home,
		KeyRound,
		LogOut,
		Menu,
		MessageCircle,
		Search,
		Sparkles,
		User
	} from 'lucide-svelte';

	type ChatRole = 'user' | 'ai';

	interface ChatMessage {
		id: number;
		role: ChatRole;
		text: string;
		time: string;
		sourceLesson?: string;
	}

	type QuestionType = 'MULTIPLE_CHOICE' | 'FILL_IN_BLANK' | 'ESSAY';

	interface GeneratedQuestion {
		id: number;
		content: string;
		type: QuestionType;
		answers: GeneratedAnswer[];
		explanation: string;
		added?: boolean;
		reported?: boolean;
	}

	interface GeneratedAnswer {
		id: number;
		content: string;
		isCorrect: boolean;
	}

	type Mode = 'qa' | 'exercise';

	let studentName = $state(auth.user?.full_name);
	let avatarUrl = $state(auth.user?.avatar);
	let showUserMenu = $state(false);
	let sidebarCollapsed = $state(false);
	let isLoggingOut = false;

	let navItems = $state([
		{ id: 'home', label: 'Trang chủ', icon: Home, href: '/stu-dashboard' },
		{ id: 'chatbot', label: 'Trợ lý ảo AI', icon: MessageCircle, badge: true, href: '/chatbot' },
		{ id: 'history', label: 'Lịch sử làm bài', icon: History, href: '/history' }
	]);
	let activeNav = $state('chatbot');

	function navigateTo(item: (typeof navItems)[number]) {
		activeNav = item.id;
		goto(item.href);
	}

	async function handleLogout() {
		if (isLoggingOut) return;
		isLoggingOut = true;
		try {
			await logoutApi();
		} catch (err) {
			console.error(err);
		} finally {
			isLoggingOut = false;
			await goto('/login');
		}
	}

	let { data }: PageProps = $props();

	let courses = $derived(data.courses);

	let mode = $state<Mode>('qa');
	let selectedCourseId = $state<number | null>(null);
	let selectedLessonId = $state<number | null>(null);
	let chapters = $state<Chapter[]>([]);

	$effect(() => {
		selectedCourseId = data.courses[0]?.id ?? null;
		chapters = data.firstTree?.chapters ?? [];
	});

	let selectedCourse = $derived(courses.find((c) => c.id === selectedCourseId) ?? null);
	let allLessons = $derived(chapters.flatMap((c) => c.lessons));
	let selectedLesson = $derived(allLessons.find((l) => l.id === selectedLessonId) ?? null);
	let contextLabel = $derived(
		selectedLesson ? selectedLesson.title : `Toàn bộ khóa học: ${selectedCourse?.name ?? ''}`
	);

	async function loadChapters(courseId: number | null) {
		selectedLessonId = null;
		if (!courseId) {
			chapters = [];
			return;
		}
		try {
			chapters = (await getCourseTree(courseId)).chapters;
		} catch (err) {
			chapters = [];
			pushSystemMessage(getApiErrorMessage(err, 'Không tải được nội dung khóa học.'));
		}
	}

	let messages = $state<ChatMessage[]>([
		{
			id: 1,
			role: 'ai',
			text: `Chào ${studentName ?? 'bạn'} 👋 Chọn khóa học/bài học ở trên rồi đặt câu hỏi, mình sẽ trả lời dựa trên nội dung bài học đã học.`,
			time: '09:12'
		}
	]);
	let draft = $state('');
	let isThinking = $state(false);
	let scrollEl = $state<HTMLDivElement | null>(null);
	let hasConversation = $derived(messages.length > 1);

	const suggestedPrompts = [
		'Giải thích lại phần lý thuyết trong bài này',
		'Cho em ví dụ minh hoạ dễ hiểu hơn',
		'Tóm tắt nội dung bài học thành gạch đầu dòng',
		'Bài này thường ra dạng câu hỏi nào trong đề thi?'
	];

	$effect(() => {
		void messages.length;
		void isThinking;
		void mode;

		if (scrollEl) {
			scrollEl.scrollTo({
				top: scrollEl.scrollHeight,
				behavior: 'smooth'
			});
		}
	});

	function nowTime(): string {
		const d = new Date();
		return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
	}

	function pushSystemMessage(text: string) {
		messages.push({ id: Date.now(), role: 'ai', text, time: nowTime() });
	}

	async function sendPrompt(text?: string): Promise<void> {
		const content = (text ?? draft).trim();
		if (!content || isThinking) return;

		if (!selectedCourseId) {
			pushSystemMessage('Bạn cần chọn một khóa học trước khi đặt câu hỏi.');
			return;
		}

		messages.push({ id: Date.now(), role: 'user', text: content, time: nowTime() });
		draft = '';
		isThinking = true;

		try {
			const res = await askAI(content, selectedCourseId, selectedLesson?.id);
			messages.push({
				id: Date.now() + 1,
				role: 'ai',
				text: res.answer,
				time: nowTime(),
				sourceLesson: selectedLesson?.title
			});
		} catch (err) {
			pushSystemMessage(getApiErrorMessage(err, 'Trợ lý AI chưa trả lời được, bạn thử lại nhé.'));
		} finally {
			isThinking = false;
		}
	}

	function handleKeydown(e: KeyboardEvent): void {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			sendPrompt();
		}
	}

	function newConversation(): void {
		messages = [
			{
				id: Date.now(),
				role: 'ai',
				text: 'Bắt đầu cuộc trò chuyện mới. Bạn cần hỏi gì?',
				time: nowTime()
			}
		];
	}

	let exerciseType = $state<QuestionType>('MULTIPLE_CHOICE');
	let exerciseCount = $state(3);
	let isGenerating = $state(false);
	let generatedQuestions = $state<GeneratedQuestion[]>([]);
	let reportingId = $state<number | null>(null);
	let reportNote = $state('');

	const typeLabel: Record<QuestionType, string> = {
		MULTIPLE_CHOICE: 'Trắc nghiệm',
		FILL_IN_BLANK: 'Điền khuyết',
		ESSAY: 'Tự luận'
	};

	async function mockGenerateQuestions(): Promise<void> {
		isGenerating = true;
		generatedQuestions = [];
		await new Promise((r) => setTimeout(r, 1200));
		generatedQuestions = Array.from({ length: exerciseCount }, (_, i) => {
			const correctAnswer = Math.floor(Math.random() * 4);

			return {
				id: Date.now() + i,
				type: exerciseType,
				content: `Câu ${i + 1} (${typeLabel[exerciseType]}) — nội dung mẫu dựa trên "${contextLabel}"`,
				answers:
					exerciseType === 'MULTIPLE_CHOICE'
						? [
								{
									id: 1,
									content: 'A. Hàm số đồng biến trên khoảng xác định',
									isCorrect: correctAnswer === 0
								},
								{
									id: 2,
									content: 'B. Hàm số luôn nhận giá trị dương',
									isCorrect: correctAnswer === 1
								},
								{
									id: 3,
									content: 'C. Đạo hàm của hàm số bằng 0 tại mọi điểm',
									isCorrect: correctAnswer === 2
								},
								{
									id: 4,
									content: 'D. Đồ thị hàm số luôn đi qua gốc tọa độ',
									isCorrect: correctAnswer === 3
								}
							]
						: [],
				explanation: 'Lời giải chi tiết minh hoạ cho câu hỏi này sẽ hiển thị ở đây.'
			};
		});
		isGenerating = false;
	}

	function addToAssignment(q: GeneratedQuestion): void {
		q.added = true;
	}

	function openReport(q: GeneratedQuestion): void {
		reportingId = q.id;
		reportNote = '';
	}

	function submitReport(q: GeneratedQuestion): void {
		q.reported = true;
		reportingId = null;
	}
</script>

<svelte:head>
	<link rel="preconnect" href="https://fonts.googleapis.com" />
	<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="" />
	<link
		href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700;800&family=Inter:wght@400;500;600&display=swap"
		rel="stylesheet"
	/>
	<title>Trợ lý ảo AI</title>
</svelte:head>

<div
	class="flex h-screen w-full bg-slate-50 text-slate-900"
	style="font-family:'Inter',sans-serif;"
>
	<aside
		class={`relative flex flex-col bg-brand-950 text-white transition-all duration-300 ${sidebarCollapsed ? 'w-20' : 'w-64'}`}
	>
		<div class="flex items-center gap-3 px-5 py-6">
			<div
				class="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-linear-to-tr from-brand-500 to-brand-500 shadow-lg shadow-brand-900/40"
			>
				<Sparkles class="h-5 w-5 text-white" />
			</div>
			{#if !sidebarCollapsed}
				<span class="truncate font-semibold tracking-tight" style="font-family:'Sora',sans-serif;">
					Gia sư AI CaSiu
				</span>
			{/if}
		</div>

		<nav class="mt-2 flex-1 space-y-1 px-3">
			{#each navItems as item (item.id)}
				<button
					onclick={() => navigateTo(item)}
					class={`group flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all
						${
							activeNav === item.id
								? 'bg-white/10 text-white shadow-inner'
								: 'text-brand-100/60 hover:bg-white/5 hover:text-white'
						}`}
				>
					<span class="relative shrink-0">
						<item.icon class="h-4.5 w-4.5" />
						{#if item.badge}
							<span
								class="absolute -right-0.5 -top-0.5 h-1.5 w-1.5 animate-pulse rounded-full bg-teal-400"
							></span>
						{/if}
					</span>
					{#if !sidebarCollapsed}
						<span class="truncate">{item.label}</span>
					{/if}
					{#if activeNav === item.id && !sidebarCollapsed}
						<span class="ml-auto h-1.5 w-1.5 rounded-full bg-brand-400"></span>
					{/if}
				</button>
			{/each}
		</nav>

		<button
			onclick={() => (sidebarCollapsed = !sidebarCollapsed)}
			class="mx-3 mb-2 flex items-center gap-2 rounded-xl px-3 py-2 text-xs text-brand-100/40 hover:bg-white/5 hover:text-white"
		>
			<Menu class="h-4 w-4" />
			{#if !sidebarCollapsed}Thu gọn{/if}
		</button>
	</aside>

	<div class="flex flex-1 flex-col min-w-0">
		<header
			class="flex items-center justify-between border-b border-slate-200/70 bg-white/80 px-8 py-4 backdrop-blur"
		>
			<div class="flex w-full max-w-md items-center gap-2 rounded-full bg-slate-100 px-4 py-2">
				<Search class="h-4 w-4 text-slate-400" />
				<input
					type="text"
					placeholder="Tìm khóa học, bài tập..."
					class="w-full bg-transparent text-sm text-slate-600 placeholder-slate-400 outline-none"
				/>
			</div>
			<div class="flex items-center gap-4">
				<div class="relative">
					<button
						onclick={() => (showUserMenu = !showUserMenu)}
						class="flex items-center gap-2.5 rounded-full py-1 pl-3 pr-1 hover:bg-slate-100"
						aria-label="Mở menu tài khoản"
					>
						<span class="text-sm font-medium text-slate-700">{studentName}</span>

						{#if avatarUrl}
							<img
								src={avatarUrl}
								alt={studentName}
								class="h-9 w-9 shrink-0 rounded-full object-cover"
							/>
						{:else}
							<span
								class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-linear-to-tr from-rose-400 to-orange-300 text-sm font-bold text-white"
							>
								{studentName}
							</span>
						{/if}
					</button>

					{#if showUserMenu}
						<button
							class="fixed inset-0 z-40 cursor-default"
							onclick={() => (showUserMenu = false)}
							aria-label="Đóng menu"
						></button>

						<div
							class="absolute right-0 top-12 z-50 w-56 overflow-hidden rounded-2xl border border-slate-200/70 bg-white py-2 shadow-xl shadow-slate-200/70"
						>
							<button
								class="flex w-full items-center gap-3 px-4 py-2.5 text-sm text-slate-600 hover:bg-slate-50"
							>
								<User class="h-4 w-4" />
								Xem hồ sơ
							</button>
							<button
								class="flex w-full items-center gap-3 px-4 py-2.5 text-sm text-slate-600 hover:bg-slate-50"
							>
								<KeyRound class="h-4 w-4" />
								Đổi mật khẩu
							</button>

							<div class="my-1 border-t border-slate-100"></div>

							<button
								class="flex w-full items-center gap-3 px-4 py-2.5 text-sm text-rose-600 hover:bg-rose-50"
								onclick={handleLogout}
							>
								<LogOut class="h-4 w-4" />
								Đăng xuất
							</button>
						</div>
					{/if}
				</div>
			</div>
		</header>

		<div class="flex items-center justify-between px-8 py-5 bg-white border-b border-slate-100">
			<div>
				<h1 class="text-xl font-extrabold m-0" style="font-family:'Sora',sans-serif;">
					Trợ lý ảo AI
				</h1>
				<p class="text-[13px] text-slate-400 mt-0.5">
					Đặt câu hỏi hoặc nhờ AI tạo bài tập theo bài học
				</p>
			</div>
			<button
				class="bg-slate-100 hover:bg-slate-200 text-slate-600 text-[13px] font-semibold rounded-[10px] px-3.5 py-2"
				onclick={newConversation}
			>
				+ Cuộc trò chuyện mới
			</button>
		</div>

		<div class="bg-white border-b border-slate-100 px-8 py-3 flex flex-wrap items-center gap-3">
			<select
				class="text-[13px] border border-slate-200 rounded-lg px-3 py-1.5 bg-slate-50 focus:outline-none focus:ring-2 focus:ring-brand-400"
				bind:value={selectedCourseId}
				onchange={() => loadChapters(selectedCourseId)}
			>
				{#each courses as c (c.id)}
					<option value={c.id}>{c.name}</option>
				{/each}
			</select>

			<select
				class="text-[13px] border border-slate-200 rounded-lg px-3 py-1.5 bg-slate-50 focus:outline-none focus:ring-2 focus:ring-brand-400"
				bind:value={selectedLessonId}
			>
				<option value={null}>Toàn bộ khóa học</option>
				{#each chapters as ch (ch.id)}
					<optgroup label={ch.title}>
						{#each ch.lessons as l (l.id)}
							<option value={l.id}>{l.title}</option>
						{/each}
					</optgroup>
				{/each}
			</select>

			{#if courses.length === 0}
				<span
					class="text-[12px] text-amber-600 bg-amber-50 border border-amber-200 rounded-full px-2.5 py-1"
				>
					⚠ Bạn chưa ghi danh khóa học nào nên trợ lý AI chưa có tài liệu để trả lời
				</span>
			{/if}

			<div
				class="ml-auto flex items-center bg-slate-100 rounded-full p-1 text-[13px] font-semibold"
			>
				<button
					class="px-3.5 py-1.5 rounded-full transition {mode === 'qa'
						? 'bg-white shadow text-brand-600'
						: 'text-slate-500'}"
					onclick={() => (mode = 'qa')}
				>
					Hỏi đáp
				</button>
				<button
					class="px-3.5 py-1.5 rounded-full transition {mode === 'exercise'
						? 'bg-white shadow text-brand-600'
						: 'text-slate-500'}"
					onclick={() => (mode = 'exercise')}
				>
					Sinh bài tập
				</button>
			</div>
		</div>

		{#if mode === 'qa'}
			<section class="flex-1 flex flex-col min-h-0 max-w-215 w-full mx-auto px-6 box-border">
				<div bind:this={scrollEl} class="flex-1 overflow-y-auto py-7 px-1 flex flex-col gap-4.5">
					{#if !hasConversation}
						<div class="m-auto text-center max-w-95 text-slate-500">
							<div
								class="w-14 h-14 rounded-2xl bg-linear-to-br from-brand-500 to-brand-500 flex items-center justify-center text-2xl mx-auto mb-3.5 shadow-lg shadow-brand-900/20"
							>
								<Sparkles class="h-6 w-6 text-white" />
							</div>
							<h2
								class="text-lg font-semibold text-slate-900 mb-1.5"
								style="font-family:'Sora',sans-serif;"
							>
								Hỏi mình bất cứ điều gì
							</h2>
							<p class="text-[13.5px] leading-relaxed">
								Đang hỏi trong ngữ cảnh: <span class="font-medium text-slate-700"
									>{contextLabel}</span
								>
							</p>
						</div>
					{/if}

					{#each messages as msg (msg.id)}
						<div class="flex items-end gap-2.5 {msg.role === 'user' ? 'justify-end' : ''}">
							{#if msg.role === 'ai'}
								<div
									class="w-7.5 h-7.5 rounded-full shrink-0 flex items-center justify-center text-white bg-linear-to-br from-brand-500 to-brand-500"
								>
									<Sparkles class="h-4 w-4" />
								</div>
							{/if}
							<div
								class="max-w-[70%] rounded-2xl px-4 py-3 shadow-sm {msg.role === 'user'
									? 'bg-brand-950 text-white rounded-br-sm'
									: 'bg-white border border-slate-100 rounded-bl-sm'}"
							>
								{#if msg.sourceLesson}
									<span class="block text-[10.5px] font-medium text-brand-500 mb-1">
										📎 Nguồn: {msg.sourceLesson}
									</span>
								{/if}
								<p class="text-sm leading-relaxed whitespace-pre-wrap m-0">{msg.text}</p>
								<span
									class="block mt-1.5 text-[10.5px] {msg.role === 'user'
										? 'text-slate-300'
										: 'text-slate-400'}"
								>
									{msg.time}
								</span>
							</div>
							{#if msg.role === 'user'}
								{#if avatarUrl}
									<img
										src={avatarUrl}
										alt={studentName}
										class="w-7.5 h-7.5 rounded-full object-cover shrink-0"
									/>
								{:else}
									<div
										class="w-7.5 7.5 rounded-full shrink-0 flex items-center justify-center text-[13px] font-bold text-white bg-linear-to-tr from-rose-400 to-orange-300"
									>
										{studentName}
									</div>
								{/if}
							{/if}
						</div>
					{/each}

					{#if isThinking}
						<div class="flex items-end gap-2.5">
							<div
								class="w-7.5 h-7.5 rounded-full shrink-0 flex items-center justify-center text-white bg-linear-to-br from-brand-500 to-brand-500"
							>
								<Sparkles class="h-4 w-4" />
							</div>
							<div
								class="flex items-center gap-1.5 bg-white border border-slate-100 rounded-2xl px-4.5 py-3.5"
							>
								<span
									class="w-1.5 h-1.5 rounded-full bg-slate-300 animate-bounce [animation-delay:0ms]"
								></span>
								<span
									class="w-1.5 h-1.5 rounded-full bg-slate-300 animate-bounce [animation-delay:150ms]"
								></span>
								<span
									class="w-1.5 h-1.5 rounded-full bg-slate-300 animate-bounce [animation-delay:300ms]"
								></span>
							</div>
						</div>
					{/if}
				</div>

				{#if !hasConversation}
					<div class="flex flex-wrap gap-2 justify-center pb-4">
						{#each suggestedPrompts as s (s)}
							<button
								class="bg-white border border-slate-200 rounded-full px-3.5 py-2 text-[12.5px] text-slate-600 hover:border-brand-400 hover:text-brand-600"
								onclick={() => sendPrompt(s)}
							>
								{s}
							</button>
						{/each}
					</div>
				{/if}

				<div
					class="flex items-end gap-2.5 bg-white border border-slate-200 rounded-2xl px-4 py-2.5 mb-1.5 shadow-sm shadow-slate-200/50"
				>
					<textarea
						rows="1"
						placeholder="Nhập câu hỏi của bạn..."
						class="flex-1 resize-none border-none outline-none text-sm py-1.5 max-h-30"
						bind:value={draft}
						onkeydown={handleKeydown}></textarea>
					<button
						class="w-9.5 h-9.5 rounded-xl text-white text-[15px] shrink-0 disabled:bg-slate-300 disabled:cursor-not-allowed bg-brand-950 hover:bg-brand-600 transition-colors"
						disabled={!draft.trim() || isThinking}
						onclick={() => sendPrompt()}
					>
						➤
					</button>
				</div>
				<p class="text-center text-[11px] text-slate-400 mb-4">
					AI có thể mắc lỗi. Hãy kiểm tra lại các thông tin quan trọng.
				</p>
			</section>
		{:else}
			<section class="flex-1 overflow-y-auto max-w-215 w-full mx-auto px-6 py-7 box-border">
				<div class="bg-white border border-slate-100 rounded-2xl p-5 shadow-sm shadow-slate-200/50">
					<h2 class="text-[15px] font-bold mb-1" style="font-family:'Sora',sans-serif;">
						Tạo câu hỏi luyện tập
					</h2>
					<p class="text-[13px] text-slate-500 mb-4">
						AI sẽ soạn câu hỏi dựa trên: <span class="font-medium text-slate-700"
							>{contextLabel}</span
						>
					</p>

					<div class="flex flex-wrap items-end gap-4">
						<div>
							<label for="exercise-type" class="block text-[12px] font-medium text-slate-500 mb-1"
								>Loại câu hỏi</label
							>
							<select
								id="exercise"
								class="text-[13px] border border-slate-200 rounded-lg px-3 py-1.5 bg-slate-50"
								bind:value={exerciseType}
							>
								<option value="MULTIPLE_CHOICE">Trắc nghiệm</option>
								<option value="FILL_IN_BLANK">Điền khuyết</option>
								<option value="ESSAY">Tự luận</option>
							</select>
						</div>
						<div>
							<label for="exercise-count" class="block text-[12px] font-medium text-slate-500 mb-1"
								>Số lượng câu hỏi</label
							>
							<input
								id="exercise-count"
								type="number"
								min="1"
								max="10"
								class="w-20 text-[13px] border border-slate-200 rounded-lg px-3 py-1.5 bg-slate-50"
								bind:value={exerciseCount}
							/>
						</div>
						<button
							class="ml-auto bg-brand-600 hover:bg-brand-700 text-white text-[13px] font-semibold rounded-[10px] px-5 py-2 disabled:opacity-50"
							disabled={isGenerating}
							onclick={mockGenerateQuestions}
						>
							{isGenerating ? 'Đang tạo...' : '✨ Tạo câu hỏi'}
						</button>
					</div>
				</div>

				<div class="flex flex-col gap-3 mt-5">
					{#if isGenerating}
						{#each Array(exerciseCount) as i (i)}
							<div class="bg-white border border-slate-100 rounded-2xl p-5 animate-pulse">
								<div class="h-3.5 bg-slate-100 rounded w-3/4 mb-3"></div>
								<div class="h-3 bg-slate-100 rounded w-1/2"></div>
							</div>
						{/each}
					{/if}

					{#each generatedQuestions as q (q.id)}
						<div
							class="bg-white border border-slate-100 rounded-2xl p-5 shadow-sm shadow-slate-200/50"
						>
							<div class="flex items-start justify-between gap-3">
								<span
									class="text-[11px] font-semibold text-brand-600 bg-brand-50 rounded-full px-2.5 py-1"
								>
									{typeLabel[q.type]}
								</span>
								{#if q.added}
									<span
										class="text-[11px] font-semibold text-emerald-600 bg-emerald-50 rounded-full px-2.5 py-1"
									>
										✓ Đã thêm vào bài tập
									</span>
								{/if}
							</div>
							<p class="text-sm font-medium text-slate-800 mt-3 mb-2">{q.content}</p>

							{#if q.type === 'MULTIPLE_CHOICE'}
								<ul class="flex flex-col gap-1.5 mb-2">
									{#each q.answers as a (a.id)}
										<li
											class="text-[13px] px-3 py-1.5 rounded-lg border {a.isCorrect
												? 'border-emerald-300 bg-emerald-50 text-emerald-700 font-medium'
												: 'border-slate-100 text-slate-600'}"
										>
											{a.content}{a.isCorrect ? ' ✓' : ''}
										</li>
									{/each}
								</ul>
							{/if}

							<p class="text-[12.5px] text-slate-500 mb-3">
								<span class="font-medium text-slate-600">Giải thích:</span>
								{q.explanation}
							</p>

							<div class="flex items-center gap-2 pt-2 border-t border-slate-100">
								<button
									class="text-[12.5px] font-semibold text-white bg-brand-950 hover:bg-brand-600 transition-colors rounded-lg px-3 py-1.5 disabled:opacity-50"
									disabled={q.added}
									onclick={() => addToAssignment(q)}
								>
									+ Thêm vào bài tập
								</button>
								{#if q.reported}
									<span class="text-[12.5px] text-amber-600">🚩 Đã báo lỗi, chờ gia sư xem xét</span
									>
								{:else}
									<button
										class="text-[12.5px] font-medium text-slate-500 hover:text-red-500"
										onclick={() => openReport(q)}
									>
										🚩 Báo lỗi câu hỏi
									</button>
								{/if}
							</div>

							{#if reportingId === q.id}
								<div class="mt-3 flex gap-2">
									<input
										class="flex-1 text-[13px] border border-slate-200 rounded-lg px-3 py-1.5"
										placeholder="Mô tả lỗi (ví dụ: đáp án sai, câu hỏi không rõ nghĩa...)"
										bind:value={reportNote}
									/>
									<button
										class="text-[12.5px] font-semibold text-white bg-red-500 hover:bg-red-600 rounded-lg px-3 py-1.5"
										onclick={() => submitReport(q)}
									>
										Gửi
									</button>
								</div>
							{/if}
						</div>
					{/each}

					{#if !isGenerating && generatedQuestions.length === 0}
						<div class="text-center text-[13px] text-slate-400 py-10">
							Chưa có câu hỏi nào. Nhấn "Tạo câu hỏi" để bắt đầu.
						</div>
					{/if}
				</div>
			</section>
		{/if}
	</div>
</div>
