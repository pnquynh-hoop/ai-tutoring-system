<script lang="ts">
	import { goto } from '$app/navigation';
	import { logoutApi } from '$lib/api/calledAPI';
	import { auth } from '$lib/stores/auth.svelte';
	import { showToast } from '$lib/stores/toast.svelte';
	import Avatar from '$lib/components/Avatar.svelte';
	import MarkRightButton from '$lib/components/MarkRightButton.svelte';
	import {
		Menu,
		LogOut,
		ChevronRight,
		ChevronDown,
		Plus,
		Pencil,
		Trash2,
		Check,
		X,
		PlayCircle,
		FileText,
		Paperclip,
		Send
	} from 'lucide-svelte';

	// ============================================================
	// Gia sư quản lý cây khóa học: Chapter <-> Lesson <-> LearningResource
	// + trả lời/đánh dấu đúng Comment của học sinh dưới mỗi bài học.
	// Toàn bộ field đúng theo model thật, mock data trước, gắn API sau.
	// ============================================================

	type ResourceType = 'VIDEO_URL' | 'PDF_FILE' | 'OTHERS';

	interface ResourceItem {
		id: number;
		title: string;
		resource_type: ResourceType;
		content: string | null;
		video_url: string | null;
		file_url: string | null;
	}

	interface LessonItem {
		id: number;
		title: string;
		order: number;
		resources: ResourceItem[];
	}

	interface ChapterItem {
		id: number;
		title: string;
		order: number;
		lessons: LessonItem[];
	}

	interface CommentAuthor {
		id: number;
		full_name: string;
		avatar: string | null;
	}

	interface CommentItem {
		id: number;
		content: string;
		is_right: boolean;
		lesson_id: number;
		created_by: CommentAuthor;
		parent: number | null;
		created_at: string;
	}

	// --- User thật (gia sư) ---
	let tutorName = $derived(auth.user?.full_name);
	let avatarUrl = $derived(auth.user?.avatar);
	let showUserMenu = $state(false);
	let isLoggingOut = false;

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

	// --- MOCK: cây khóa học (Course giả định đã chọn từ trang danh sách khóa học) ---
	const courseName = 'Luyện Thi THPT QG Toán Học 2026';
	let sidebarCollapsed = $state(false);

	let chapters = $state<ChapterItem[]>([
		{
			id: 11,
			title: 'Chương 1: Phương trình - Bất phương trình',
			order: 1,
			lessons: [
				{
					id: 111,
					title: 'Bài 1: Phương trình mũ',
					order: 1,
					resources: [
						{
							id: 1,
							title: 'Video giảng lý thuyết',
							resource_type: 'VIDEO_URL',
							content: null,
							video_url: 'https://youtube.com/watch?v=abc123',
							file_url: null
						},
						{
							id: 2,
							title: 'Slide bài giảng',
							resource_type: 'PDF_FILE',
							content: null,
							video_url: null,
							file_url: 'https://res.cloudinary.com/demo/bai1.pdf'
						}
					]
				},
				{ id: 112, title: 'Bài 2: Phương trình logarit', order: 2, resources: [] }
			]
		},
		{
			id: 12,
			title: 'Chương 2: Hàm số',
			order: 2,
			lessons: [{ id: 121, title: 'Bài 1: Khảo sát hàm số', order: 1, resources: [] }]
		}
	]);

	let expandedChapterId = $state<number | null>(11);
	let selectedLessonId = $state<number | null>(111);

	let allLessons = $derived(chapters.flatMap((c) => c.lessons));
	let selectedLesson = $derived(allLessons.find((l) => l.id === selectedLessonId) ?? null);
	let selectedChapter = $derived(
		chapters.find((c) => c.lessons.some((l) => l.id === selectedLessonId)) ?? null
	);

	function selectLesson(lessonId: number) {
		selectedLessonId = lessonId;
	}

	// --- CRUD Chương ---
	let addingChapter = $state(false);
	let newChapterTitle = $state('');
	let editingChapterId = $state<number | null>(null);
	let editChapterTitle = $state('');

	function startAddChapter() {
		addingChapter = true;
		newChapterTitle = '';
	}

	function confirmAddChapter() {
		if (!newChapterTitle.trim()) return;
		// TODO: POST /api/chapters/ { course, title, order }
		chapters.push({
			id: Date.now(),
			title: newChapterTitle.trim(),
			order: chapters.length + 1,
			lessons: []
		});
		addingChapter = false;
		showToast('Đã thêm chương', 'success');
	}

	function startEditChapter(ch: ChapterItem) {
		editingChapterId = ch.id;
		editChapterTitle = ch.title;
	}

	function confirmEditChapter(ch: ChapterItem) {
		if (!editChapterTitle.trim()) return;
		// TODO: PATCH /api/chapters/{id}/ { title }
		ch.title = editChapterTitle.trim();
		editingChapterId = null;
	}

	function deleteChapter(ch: ChapterItem) {
		if (!window.confirm(`Xoá chương "${ch.title}"? Toàn bộ bài học bên trong cũng sẽ bị xoá.`)) return;
		// TODO: DELETE /api/chapters/{id}/
		chapters = chapters.filter((c) => c.id !== ch.id);
		if (selectedLesson && ch.lessons.some((l) => l.id === selectedLesson!.id)) {
			selectedLessonId = null;
		}
		showToast('Đã xoá chương', 'success');
	}

	// --- CRUD Bài học ---
	let addingLessonChapterId = $state<number | null>(null);
	let newLessonTitle = $state('');
	let editingLessonId = $state<number | null>(null);
	let editLessonTitle = $state('');

	function startAddLesson(chapterId: number) {
		addingLessonChapterId = chapterId;
		newLessonTitle = '';
	}

	function confirmAddLesson(ch: ChapterItem) {
		if (!newLessonTitle.trim()) return;
		// TODO: POST /api/lessons/ { chapter, title, order }
		ch.lessons.push({
			id: Date.now(),
			title: newLessonTitle.trim(),
			order: ch.lessons.length + 1,
			resources: []
		});
		addingLessonChapterId = null;
		showToast('Đã thêm bài học', 'success');
	}

	function startEditLesson(lesson: LessonItem) {
		editingLessonId = lesson.id;
		editLessonTitle = lesson.title;
	}

	function confirmEditLesson(lesson: LessonItem) {
		if (!editLessonTitle.trim()) return;
		// TODO: PATCH /api/lessons/{id}/ { title }
		lesson.title = editLessonTitle.trim();
		editingLessonId = null;
	}

	function deleteLesson(ch: ChapterItem, lesson: LessonItem) {
		if (!window.confirm(`Xoá bài học "${lesson.title}"?`)) return;
		// TODO: DELETE /api/lessons/{id}/
		ch.lessons = ch.lessons.filter((l) => l.id !== lesson.id);
		if (selectedLessonId === lesson.id) selectedLessonId = null;
		showToast('Đã xoá bài học', 'success');
	}

	// --- CRUD Tài nguyên bài học ---
	let addingResource = $state(false);
	let newResource = $state<{
		title: string;
		resource_type: ResourceType;
		content: string;
		video_url: string;
		file_url: string;
	}>({ title: '', resource_type: 'VIDEO_URL', content: '', video_url: '', file_url: '' });

	const resourceTypeLabel: Record<ResourceType, string> = {
		VIDEO_URL: 'Video',
		PDF_FILE: 'Tệp PDF',
		OTHERS: 'Khác'
	};

	function startAddResource() {
		addingResource = true;
		newResource = { title: '', resource_type: 'VIDEO_URL', content: '', video_url: '', file_url: '' };
	}

	function confirmAddResource() {
		if (!selectedLesson || !newResource.title.trim()) return;
		// TODO: POST /api/learning-resources/ { lesson, title, resource_type, content/video_url/file_url }
		selectedLesson.resources.push({
			id: Date.now(),
			title: newResource.title.trim(),
			resource_type: newResource.resource_type,
			content: newResource.content || null,
			video_url: newResource.resource_type === 'VIDEO_URL' ? newResource.video_url || null : null,
			file_url: newResource.resource_type === 'PDF_FILE' ? newResource.file_url || null : null
		});
		addingResource = false;
		showToast('Đã thêm tài nguyên', 'success');
	}

	function deleteResource(resource: ResourceItem) {
		if (!selectedLesson) return;
		if (!window.confirm(`Xoá tài nguyên "${resource.title}"?`)) return;
		// TODO: DELETE /api/learning-resources/{id}/
		selectedLesson.resources = selectedLesson.resources.filter((r) => r.id !== resource.id);
		showToast('Đã xoá tài nguyên', 'success');
	}

	// --- Bình luận (copy logic từ trang học sinh, canEdit luôn true vì đây là gia sư) ---
	let comments = $state<CommentItem[]>([
		{
			id: 1,
			content: 'Thầy ơi cho em hỏi vì sao 2^x=8 lại ra x=3 vậy ạ?',
			is_right: false,
			lesson_id: 111,
			created_by: { id: 5, full_name: 'Trần Thị Bích', avatar: null },
			parent: null,
			created_at: '2026-07-20T10:00:00'
		},
		{
			id: 2,
			content: 'Vì 8 = 2^3, nên khi cùng cơ số 2 thì số mũ bằng nhau: x = 3 nhé em.',
			is_right: true,
			lesson_id: 111,
			created_by: { id: 1, full_name: 'Thầy Nguyễn Văn A', avatar: null },
			parent: 1,
			created_at: '2026-07-20T10:15:00'
		}
	]);

	let topLevelComments = $derived(
		comments.filter((c) => c.lesson_id === selectedLessonId && c.parent === null)
	);

	function getReplies(parentId: number): CommentItem[] {
		return comments.filter((c) => c.parent === parentId);
	}

	function formatCommentDate(iso: string): string {
		return new Date(iso).toLocaleString('vi-VN', {
			day: '2-digit',
			month: '2-digit',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	let replyingToId = $state<number | null>(null);
	let replyContent = $state('');
	let isSubmittingReply = $state(false);

	function toggleReplyBox(commentId: number) {
		replyingToId = replyingToId === commentId ? null : commentId;
		replyContent = '';
	}

	async function submitReply(parentId: number) {
		if (!replyContent.trim() || isSubmittingReply || !selectedLessonId) return;
		isSubmittingReply = true;
		try {
			// TODO: POST /api/comments/ { lesson, content, parent }
			await new Promise((r) => setTimeout(r, 400));
			comments.push({
				id: Date.now(),
				content: replyContent.trim(),
				is_right: false,
				lesson_id: selectedLessonId,
				created_by: { id: 1, full_name: tutorName ?? 'Gia sư', avatar: avatarUrl ?? null },
				parent: parentId,
				created_at: new Date().toISOString()
			});
			replyContent = '';
			replyingToId = null;
		} finally {
			isSubmittingReply = false;
		}
	}

	let markingRightId = $state<number | null>(null);
	async function toggleMarkRight(comment: CommentItem) {
		if (markingRightId !== null) return;
		markingRightId = comment.id;
		try {
			// TODO: PATCH /api/comments/{id}/mark-right/
			await new Promise((r) => setTimeout(r, 400));
			comment.is_right = !comment.is_right;
		} finally {
			markingRightId = null;
		}
	}
</script>

<svelte:head>
	<link rel="preconnect" href="https://fonts.googleapis.com" />
	<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="" />
	<link
		href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700;800&family=Inter:wght@400;500;600&family=Sora:wght@600;700;800&display=swap"
		rel="stylesheet"
	/>
	<title>Quản lý khóa học</title>
</svelte:head>

<div class="flex h-screen w-full bg-[#F5F6FA]" style="font-family:'Inter',sans-serif;">
	<!-- SIDEBAR: cây khóa học có CRUD -->
	<aside
		class={`relative flex h-full shrink-0 flex-col overflow-hidden bg-[#0C1550] text-white transition-all duration-300 ${sidebarCollapsed ? 'w-16' : 'w-80'}`}
	>
		<div
			class={`flex items-center border-b border-white/10 py-6 ${sidebarCollapsed ? 'justify-center px-0' : 'justify-between px-5'}`}
		>
			{#if !sidebarCollapsed}
				<span class="truncate font-semibold tracking-tight" style="font-family:'Sora',sans-serif;">
					{courseName}
				</span>
			{/if}
			<button
				onclick={() => (sidebarCollapsed = !sidebarCollapsed)}
				class="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-white/10 hover:bg-white/20"
			>
				<Menu class="h-4 w-4 text-indigo-100/60" />
			</button>
		</div>

		{#if !sidebarCollapsed}
			<div class="flex-1 overflow-y-auto px-3 py-4">
				<button
					onclick={startAddChapter}
					class="mb-3 flex w-full items-center justify-center gap-2 rounded-xl border border-dashed border-white/20 py-2 text-xs font-semibold text-indigo-100/70 hover:border-white/40 hover:text-white"
				>
					<Plus class="h-3.5 w-3.5" />
					Thêm chương
				</button>

				{#if addingChapter}
					<div class="mb-3 flex items-center gap-1.5 px-1">
						<input
							class="min-w-0 flex-1 rounded-lg bg-white/10 px-3 py-1.5 text-xs text-white placeholder-indigo-100/40 outline-none focus:bg-white/15"
							placeholder="Tên chương mới..."
							bind:value={newChapterTitle}
							onkeydown={(e) => e.key === 'Enter' && confirmAddChapter()}
						/>
						<button onclick={confirmAddChapter} class="rounded-lg bg-emerald-500/80 p-1.5 hover:bg-emerald-500">
							<Check class="h-3.5 w-3.5" />
						</button>
						<button onclick={() => (addingChapter = false)} class="rounded-lg bg-white/10 p-1.5 hover:bg-white/20">
							<X class="h-3.5 w-3.5" />
						</button>
					</div>
				{/if}

				<nav class="space-y-1">
					{#each chapters as chapter (chapter.id)}
						<div>
							<div
								class={`group flex items-center gap-1 rounded-xl px-2 py-1.5 transition-all ${
									expandedChapterId === chapter.id ? 'bg-white/10' : 'hover:bg-white/5'
								}`}
							>
								{#if editingChapterId === chapter.id}
									<input
										class="min-w-0 flex-1 rounded-lg bg-white/10 px-2 py-1 text-xs text-white outline-none"
										bind:value={editChapterTitle}
										onkeydown={(e) => e.key === 'Enter' && confirmEditChapter(chapter)}
									/>
									<button onclick={() => confirmEditChapter(chapter)} class="rounded-lg p-1 hover:bg-white/10">
										<Check class="h-3.5 w-3.5 text-emerald-400" />
									</button>
									<button onclick={() => (editingChapterId = null)} class="rounded-lg p-1 hover:bg-white/10">
										<X class="h-3.5 w-3.5 text-indigo-100/50" />
									</button>
								{:else}
									<button
										onclick={() =>
											(expandedChapterId = expandedChapterId === chapter.id ? null : chapter.id)}
										class="flex min-w-0 flex-1 items-center gap-2 text-left text-sm font-medium text-indigo-100/80"
									>
										{#if expandedChapterId === chapter.id}
											<ChevronDown class="h-3.5 w-3.5 shrink-0 opacity-60" />
										{:else}
											<ChevronRight class="h-3.5 w-3.5 shrink-0 opacity-60" />
										{/if}
										<span class="truncate">{chapter.title}</span>
									</button>
									<button
										onclick={() => startEditChapter(chapter)}
										class="shrink-0 rounded-lg p-1 opacity-0 hover:bg-white/10 group-hover:opacity-100"
									>
										<Pencil class="h-3 w-3 text-indigo-100/60" />
									</button>
									<button
										onclick={() => deleteChapter(chapter)}
										class="shrink-0 rounded-lg p-1 opacity-0 hover:bg-rose-500/20 group-hover:opacity-100"
									>
										<Trash2 class="h-3 w-3 text-rose-300" />
									</button>
								{/if}
							</div>

							{#if expandedChapterId === chapter.id}
								<div class="relative ml-5 mt-1 space-y-0.5 pl-4">
									<div class="absolute left-0 top-0 bottom-2 w-px bg-white/10"></div>
									{#each chapter.lessons as lesson (lesson.id)}
										<div
											class={`group flex items-center gap-1 rounded-lg px-2 py-1.5 ${
												selectedLessonId === lesson.id ? 'bg-white/10' : 'hover:bg-white/5'
											}`}
										>
											{#if editingLessonId === lesson.id}
												<input
													class="min-w-0 flex-1 rounded-lg bg-white/10 px-2 py-1 text-xs text-white outline-none"
													bind:value={editLessonTitle}
													onkeydown={(e) => e.key === 'Enter' && confirmEditLesson(lesson)}
												/>
												<button onclick={() => confirmEditLesson(lesson)} class="rounded-lg p-1 hover:bg-white/10">
													<Check class="h-3.5 w-3.5 text-emerald-400" />
												</button>
												<button onclick={() => (editingLessonId = null)} class="rounded-lg p-1 hover:bg-white/10">
													<X class="h-3.5 w-3.5 text-indigo-100/50" />
												</button>
											{:else}
												<button
													onclick={() => selectLesson(lesson.id)}
													class={`min-w-0 flex-1 truncate text-left text-[13px] ${
														selectedLessonId === lesson.id
															? 'font-semibold text-white'
															: 'text-indigo-100/60'
													}`}
												>
													{lesson.title}
												</button>
												<button
													onclick={() => startEditLesson(lesson)}
													class="shrink-0 rounded-lg p-1 opacity-0 hover:bg-white/10 group-hover:opacity-100"
												>
													<Pencil class="h-3 w-3 text-indigo-100/60" />
												</button>
												<button
													onclick={() => deleteLesson(chapter, lesson)}
													class="shrink-0 rounded-lg p-1 opacity-0 hover:bg-rose-500/20 group-hover:opacity-100"
												>
													<Trash2 class="h-3 w-3 text-rose-300" />
												</button>
											{/if}
										</div>
									{/each}

									{#if addingLessonChapterId === chapter.id}
										<div class="flex items-center gap-1.5 px-2 py-1">
											<input
												class="min-w-0 flex-1 rounded-lg bg-white/10 px-2 py-1 text-xs text-white placeholder-indigo-100/40 outline-none"
												placeholder="Tên bài học mới..."
												bind:value={newLessonTitle}
												onkeydown={(e) => e.key === 'Enter' && confirmAddLesson(chapter)}
											/>
											<button
												onclick={() => confirmAddLesson(chapter)}
												class="rounded-lg bg-emerald-500/80 p-1 hover:bg-emerald-500"
											>
												<Check class="h-3.5 w-3.5" />
											</button>
											<button
												onclick={() => (addingLessonChapterId = null)}
												class="rounded-lg bg-white/10 p-1 hover:bg-white/20"
											>
												<X class="h-3.5 w-3.5" />
											</button>
										</div>
									{:else}
										<button
											onclick={() => startAddLesson(chapter.id)}
											class="flex w-full items-center gap-1.5 rounded-lg px-2 py-1.5 text-[12px] text-indigo-100/40 hover:bg-white/5 hover:text-indigo-100/70"
										>
											<Plus class="h-3 w-3" />
											Thêm bài học
										</button>
									{/if}
								</div>
							{/if}
						</div>
					{/each}
				</nav>
			</div>
		{/if}

		<div class={`border-t border-white/10 py-4 ${sidebarCollapsed ? 'px-0' : 'px-3'}`}>
			<div
				class={`flex items-center rounded-xl py-2 hover:bg-white/5 ${sidebarCollapsed ? 'justify-center px-0' : 'gap-3 px-2'}`}
			>
				<Avatar src={avatarUrl} name={tutorName ?? ''} size="lg" />
				{#if !sidebarCollapsed}
					<div class="min-w-0 flex-1">
						<p class="truncate text-sm font-medium text-white">{tutorName}</p>
						<p class="truncate text-xs text-indigo-100/50">Gia sư</p>
					</div>
				{/if}
			</div>
		</div>
	</aside>

	<!-- MAIN -->
	<div class="flex flex-1 flex-col min-w-0">
		<header
			class="flex items-center justify-end border-b border-slate-200/70 bg-white/80 px-8 py-4 backdrop-blur"
		>
			<div class="relative">
				<button
					onclick={() => (showUserMenu = !showUserMenu)}
					class="flex items-center gap-2.5 rounded-full py-1 pl-3 pr-1 hover:bg-slate-100"
				>
					<span class="text-sm font-medium text-slate-700">{tutorName}</span>
					<Avatar src={avatarUrl} name={tutorName ?? ''} size="lg" />
				</button>
				{#if showUserMenu}
					<button class="fixed inset-0 z-40 cursor-default" onclick={() => (showUserMenu = false)}>===</button>
					<div
						class="absolute right-0 top-12 z-50 w-56 overflow-hidden rounded-2xl border border-slate-200/70 bg-white py-2 shadow-xl shadow-slate-200/70"
					>
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
		</header>

		<main class="flex-1 overflow-y-auto px-8 py-8">
			{#if !selectedLesson}
				<div class="flex h-full items-center justify-center text-center text-slate-400">
					<p>Chọn một bài học ở cây bên trái để chỉnh sửa.</p>
				</div>
			{:else}
				<div class="mx-auto max-w-4xl space-y-6">
					<!-- THÔNG TIN BÀI HỌC -->
					<div class="rounded-2xl border border-slate-200/70 bg-white p-6 shadow-sm shadow-slate-200/50">
						<p class="text-xs text-slate-400">{selectedChapter?.title}</p>
						<div class="mt-1 flex items-center gap-2">
							{#if editingLessonId === selectedLesson.id}
								<input
									class="flex-1 rounded-xl border border-slate-200 px-3 py-1.5 text-lg font-bold text-slate-900 outline-none focus:border-indigo-300"
									bind:value={editLessonTitle}
								/>
								<button
									onclick={() => confirmEditLesson(selectedLesson!)}
									class="rounded-xl bg-emerald-500 px-3 py-1.5 text-white hover:bg-emerald-600"
								>
									<Check class="h-4 w-4" />
								</button>
							{:else}
								<h1 class="flex-1 text-xl font-bold text-slate-900" style="font-family:'Sora',sans-serif;">
									{selectedLesson.title}
								</h1>
								<button
									onclick={() => startEditLesson(selectedLesson!)}
									class="flex items-center gap-1.5 rounded-xl border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50"
								>
									<Pencil class="h-3.5 w-3.5" />
									Đổi tên
								</button>
							{/if}
						</div>
					</div>

					<!-- TÀI NGUYÊN BÀI HỌC -->
					<div class="rounded-2xl border border-slate-200/70 bg-white p-6 shadow-sm shadow-slate-200/50">
						<div class="mb-4 flex items-center justify-between">
							<h2 class="text-sm font-semibold text-slate-800" style="font-family:'Sora',sans-serif;">
								Tài nguyên bài học
							</h2>
							<button
								onclick={startAddResource}
								class="flex items-center gap-1.5 rounded-xl bg-[#0C1550] px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-600"
							>
								<Plus class="h-3.5 w-3.5" />
								Thêm tài nguyên
							</button>
						</div>

						{#if addingResource}
							<div class="mb-4 space-y-3 rounded-xl border border-slate-200 bg-slate-50 p-4">
								<div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
									<input
										class="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm outline-none focus:border-indigo-300"
										placeholder="Tên tài nguyên"
										bind:value={newResource.title}
									/>
									<select
										class="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm outline-none focus:border-indigo-300"
										bind:value={newResource.resource_type}
									>
										<option value="VIDEO_URL">Video</option>
										<option value="PDF_FILE">Tệp PDF</option>
										<option value="OTHERS">Khác</option>
									</select>
								</div>
								{#if newResource.resource_type === 'VIDEO_URL'}
									<input
										class="w-full rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm outline-none focus:border-indigo-300"
										placeholder="Đường dẫn video (YouTube...)"
										bind:value={newResource.video_url}
									/>
								{:else if newResource.resource_type === 'PDF_FILE'}
									<input
										class="w-full rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm outline-none focus:border-indigo-300"
										placeholder="Đường dẫn tệp PDF"
										bind:value={newResource.file_url}
									/>
								{:else}
									<textarea
										rows="2"
										class="w-full resize-none rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm outline-none focus:border-indigo-300"
										placeholder="Nội dung văn bản"
										bind:value={newResource.content}
									></textarea>
								{/if}
								<div class="flex justify-end gap-2">
									<button
										onclick={() => (addingResource = false)}
										class="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-white"
									>
										Huỷ
									</button>
									<button
										onclick={confirmAddResource}
										class="rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-700"
									>
										Lưu tài nguyên
									</button>
								</div>
							</div>
						{/if}

						<div class="space-y-2">
							{#each selectedLesson.resources as res (res.id)}
								<div class="flex items-center justify-between gap-3 rounded-xl border border-slate-100 bg-slate-50 p-3">
									<div class="flex min-w-0 items-center gap-3">
										<div
											class={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${
												res.resource_type === 'VIDEO_URL'
													? 'bg-indigo-50 text-indigo-600'
													: res.resource_type === 'PDF_FILE'
														? 'bg-teal-50 text-teal-600'
														: 'bg-amber-50 text-amber-600'
											}`}
										>
											{#if res.resource_type === 'VIDEO_URL'}
												<PlayCircle class="h-4 w-4" />
											{:else if res.resource_type === 'PDF_FILE'}
												<FileText class="h-4 w-4" />
											{:else}
												<Paperclip class="h-4 w-4" />
											{/if}
										</div>
										<div class="min-w-0">
											<p class="truncate text-sm font-medium text-slate-700">{res.title}</p>
											<p class="truncate text-xs text-slate-400">
												{resourceTypeLabel[res.resource_type]}
												{#if res.video_url} • {res.video_url}{/if}
												{#if res.file_url} • {res.file_url}{/if}
											</p>
										</div>
									</div>
									<button
										onclick={() => deleteResource(res)}
										class="shrink-0 rounded-lg p-1.5 text-slate-400 hover:bg-rose-50 hover:text-rose-500"
									>
										<Trash2 class="h-4 w-4" />
									</button>
								</div>
							{/each}

							{#if selectedLesson.resources.length === 0 && !addingResource}
								<p class="py-6 text-center text-sm text-slate-400">Bài học này chưa có tài nguyên nào.</p>
							{/if}
						</div>
					</div>

					<!-- BÌNH LUẬN HỌC SINH -->
					<div class="rounded-2xl border border-slate-200/70 bg-white p-6 shadow-sm shadow-slate-200/50">
						<h2 class="mb-4 text-sm font-semibold text-slate-800" style="font-family:'Sora',sans-serif;">
							Bình luận học sinh
						</h2>

						<div class="space-y-5">
							{#each topLevelComments as comment (comment.id)}
								<div>
									<div class="flex items-start justify-between gap-3">
										<div class="flex items-start gap-3">
											<Avatar src={comment.created_by.avatar} name={comment.created_by.full_name} size="md" />
											<div class="min-w-0 flex-1">
												<p class="text-xs font-semibold text-slate-700">{comment.created_by.full_name}</p>
												<p class="text-sm text-slate-600">{comment.content}</p>
												<div class="mt-1 flex items-center gap-3">
													<p class="text-[11px] text-slate-400">{formatCommentDate(comment.created_at)}</p>
													<button
														onclick={() => toggleReplyBox(comment.id)}
														class="text-[11px] font-medium text-slate-500 hover:text-indigo-600"
													>
														Trả lời
													</button>
												</div>
											</div>
										</div>
										<MarkRightButton
											isRight={comment.is_right}
											canEdit={true}
											isLoading={markingRightId === comment.id}
											onToggle={() => toggleMarkRight(comment)}
										/>
									</div>

									{#if replyingToId === comment.id}
										<div class="mt-3 ml-11 flex items-center gap-2">
											<input
												type="text"
												bind:value={replyContent}
												onkeydown={(e) => e.key === 'Enter' && submitReply(comment.id)}
												placeholder="Trả lời học sinh..."
												disabled={isSubmittingReply}
												class="min-w-0 flex-1 rounded-full border border-slate-200 bg-white px-4 py-2 text-sm text-slate-700 outline-none focus:border-indigo-300"
											/>
											<button
												onclick={() => submitReply(comment.id)}
												disabled={!replyContent.trim() || isSubmittingReply}
												class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-blue-600 hover:bg-blue-50 disabled:opacity-40"
											>
												<Send class="h-4 w-4" />
											</button>
										</div>
									{/if}

									{#if getReplies(comment.id).length > 0}
										<div class="mt-3 ml-11 space-y-3 border-l-2 border-slate-100 pl-4">
											{#each getReplies(comment.id) as reply (reply.id)}
												<div class="flex items-start justify-between gap-3">
													<div class="flex items-start gap-3">
														<Avatar
															src={reply.created_by.avatar}
															name={reply.created_by.full_name}
															size="sm"
															fromColor="from-indigo-400"
															toColor="to-sky-300"
														/>
														<div class="min-w-0 flex-1">
															<p class="text-xs font-semibold text-slate-700">{reply.created_by.full_name}</p>
															<p class="text-sm text-slate-600">{reply.content}</p>
															<p class="mt-1 text-[11px] text-slate-400">{formatCommentDate(reply.created_at)}</p>
														</div>
													</div>
													<MarkRightButton
														isRight={reply.is_right}
														canEdit={true}
														isLoading={markingRightId === reply.id}
														onToggle={() => toggleMarkRight(reply)}
													/>
												</div>
											{/each}
										</div>
									{/if}
								</div>
							{/each}

							{#if topLevelComments.length === 0}
								<p class="text-center text-sm text-slate-400">Bài học này chưa có bình luận nào.</p>
							{/if}
						</div>
					</div>
				</div>
			{/if}
		</main>
	</div>
</div>