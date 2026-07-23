<script lang="ts">
	import { goto, invalidateAll } from '$app/navigation';
	import {
		Home,
		ChevronRight,
		ChevronLeft,
		Send,
		PlayCircle,
		FileText,
		Download,
		Paperclip,
		BookOpen
	} from 'lucide-svelte';
	import type { PageData } from './$types';
	import type { Chapter, Comment, Lesson, LessonDetail } from '$lib/api/entities';
	import Chatbot from '$lib/components/Chatbot.svelte';
	import { postComment, postCompleteLesson, toggleCommentRight } from '$lib/api/calledAPI';
	import { showToast } from '$lib/stores/toast.svelte';
	import axios from 'axios';
	import Avatar from '$lib/components/Avatar.svelte';
	import MarkRightButton from '$lib/components/MarkRightButton.svelte';

	let { data }: { data: PageData } = $props();
	let course_tree = $derived(data.course_tree);
	let user = $derived(data.user);
	let lesson = $derived(data.lesson as LessonDetail);
	let comments = $derived(data.comments);

	const activeChapter = $derived(
		course_tree.chapters.find((ch: Chapter) => ch.lessons.some((ls) => ls.id === lesson.id))
	);

	const lessonIndex = $derived(
		activeChapter ? activeChapter.lessons.findIndex((ls: Lesson) => ls.id === lesson.id) : -1
	);

	const prevLesson = $derived(
		activeChapter && lessonIndex > 0 ? activeChapter.lessons[lessonIndex - 1] : null
	);

	const nextLesson = $derived(
		activeChapter && lessonIndex >= 0 && lessonIndex < activeChapter.lessons.length - 1
			? activeChapter.lessons[lessonIndex + 1]
			: null
	);

	const currentLessonInTree = $derived(
		activeChapter?.lessons.find((ls: Lesson) => ls.id === lesson.id) ?? null
	);
	let newComment = $state('');
	let isSubmittingComment = $state(false);

	const topLevelComments = $derived(comments.filter((c) => c.parent === null));

	function getReplies(parentId: number): Comment[] {
		return (comments as Comment[]).filter((c) => c.parent === parentId);
	}

	function formatCommentDate(iso: string): string {
		return new Date(iso).toLocaleString('vi-VN', {
			day: '2-digit',
			month: '2-digit',
			year: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	async function submitComment() {
		if (!newComment.trim() || isSubmittingComment) return;

		isSubmittingComment = true;
		try {
			await postComment(lesson.id, newComment.trim());
			await invalidateAll();
			newComment = '';
		} catch (err: unknown) {
			const message = axios.isAxiosError(err)
				? (err.response?.data?.message ?? 'Gửi bình luận không thành công.')
				: 'Đã xảy ra lỗi.';
			showToast(message, 'error');
		} finally {
			isSubmittingComment = false;
		}
	}

	let replyingToId = $state<number | null>(null);
	let replyContent = $state('');
	let isSubmittingReply = $state(false);

	function toggleReplyBox(commentId: number) {
		replyingToId = replyingToId === commentId ? null : commentId;
		replyContent = '';
	}

	async function submitReply(parentId: number) {
		if (!replyContent.trim() || isSubmittingReply) return;

		isSubmittingReply = true;
		try {
			await postComment(lesson.id, replyContent.trim(), parentId);
			await invalidateAll();
			replyContent = '';
			replyingToId = null;
		} catch (err: unknown) {
			const message = axios.isAxiosError(err)
				? (err.response?.data?.message ?? 'Gửi phản hồi không thành công.')
				: 'Đã xảy ra lỗi.';
			showToast(message, 'error');
		} finally {
			isSubmittingReply = false;
		}
	}

	let markingRightId = $state<number | null>(null);
	const isTutor = $derived(user?.role === 'Tutor');

	async function toggleMarkRight(comment: Comment) {
		if (markingRightId !== null) return;

		markingRightId = comment.id;
		try {
			await toggleCommentRight(comment.id);
			await invalidateAll();
		} catch (err: unknown) {
			const message = axios.isAxiosError(err)
				? (err.response?.data?.message ?? 'Cập nhật không thành công.')
				: 'Đã xảy ra lỗi.';
			showToast(message, 'error');
		} finally {
			markingRightId = null;
		}
	}

	let isHandlingComplete = $state(false);
	async function handleComplete() {
		if (isHandlingComplete) return;

		isHandlingComplete = true;

		try {
			await postCompleteLesson(lesson.id);
			await invalidateAll();
			showToast('Đã hoàn thành bài học', 'success');
		} catch (err: unknown) {
			const message = axios.isAxiosError(err)
				? (err.response?.data?.message ?? 'Lưu không thành công.')
				: 'Đã xảy ra lỗi.';

			showToast(message, 'error');
		} finally {
			isHandlingComplete = false;
		}
	}

	const resources = $derived(lesson.resources ?? []);

	function toYoutubeEmbed(url: string): string {
		try {
			const u = new URL(url);
			const videoId = u.searchParams.get('v');
			if (videoId) return `https://www.youtube.com/embed/${videoId}`;
			if (u.hostname.includes('youtu.be')) {
				return `https://www.youtube.com/embed/${u.pathname.replace('/', '')}`;
			}
			return url;
		} catch {
			return url;
		}
	}

	function fileExt(url: string | null): string {
		if (!url) return '';
		const clean = url.split('?')[0];
		const parts = clean.split('.');
		return parts.length > 1 ? parts[parts.length - 1].toUpperCase() : '';
	}
</script>

<svelte:head>
	<link rel="preconnect" href="https://fonts.googleapis.com" />
	<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="" />
	<link
		href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700;800&family=Inter:wght@400;500;600&family=Sora:wght@600;700;800&display=swap"
		rel="stylesheet"
	/>
	<title>{lesson.title}</title>
</svelte:head>

<div class="flex h-full min-h-0 flex-1 flex-col" style="font-family:'Inter',sans-serif;">
	<!-- MAIN -->
	<header
		class="flex items-center justify-between gap-4 border-b border-slate-200/70 bg-white/80 px-8 py-4 backdrop-blur"
	>
		<nav class="flex min-w-0 flex-1 items-center gap-2 text-sm text-slate-500">
			<span class="shrink-0 font-medium text-slate-700">{course_tree.name}</span>
			{#if activeChapter}
				<ChevronRight class="h-3.5 w-3.5 shrink-0 text-slate-300" />
				<span class="min-w-0 truncate font-medium text-slate-700">{activeChapter.title}</span>
			{/if}
			<ChevronRight class="h-3.5 w-3.5 shrink-0 text-slate-300" />
			<span class="min-w-0 truncate font-semibold text-[#0C1550]">{lesson.title}</span>
		</nav>

		<a
			href="/stu-dashboard"
			class="flex shrink-0 items-center gap-2 rounded-full bg-[#0C1550] px-4 py-2 text-sm font-medium text-white hover:bg-indigo-900"
		>
			<Home class="h-4 w-4" />
			Trang chủ
		</a>
	</header>

	<main class="flex-1 overflow-y-auto px-8 py-8">
		<h1
			class="mb-6 text-center text-xl font-bold uppercase tracking-tight text-slate-900"
			style="font-family:'Sora',sans-serif;"
		>
			{lesson.title}
		</h1>

		<div class="mb-8 space-y-5">
			{#each resources as res (res.id)}
				{#if res.resource_type === 'VIDEO_URL' && res.video_url}
					<div
						class="rounded-2xl border border-slate-200/70 bg-white p-6 shadow-sm shadow-slate-200/50"
					>
						<div class="mb-4 flex items-center gap-3">
							<div
								class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600"
							>
								<PlayCircle class="h-5 w-5" />
							</div>
							<div class="min-w-0">
								<h2
									class="text-sm font-semibold text-slate-800"
									style="font-family:'Sora',sans-serif;"
								>
									{res.title}
								</h2>
								{#if res.content}
									<p class="text-xs text-slate-500">{res.content}</p>
								{/if}
							</div>
						</div>
						<div
							class="mx-auto aspect-video w-full max-w-5xl overflow-hidden rounded-xl bg-slate-100"
						>
							<iframe
								class="h-full w-full"
								src={toYoutubeEmbed(res.video_url)}
								title={res.title}
								allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
								allowfullscreen
							></iframe>
						</div>
					</div>
				{:else if res.resource_type === 'PDF_FILE' && res.file_url}
					<div
						class="rounded-2xl border border-slate-200/70 bg-white p-6 shadow-sm shadow-slate-200/50"
					>
						<div class="mb-4 flex items-center justify-between gap-3">
							<div class="flex min-w-0 items-center gap-3">
								<div
									class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-teal-50 text-teal-600"
								>
									<FileText class="h-5 w-5" />
								</div>
								<div class="min-w-0">
									<h2
										class="text-sm font-semibold text-slate-800"
										style="font-family:'Sora',sans-serif;"
									>
										{res.title}
									</h2>
									{#if res.content}
										<p class="text-xs text-slate-500">{res.content}</p>
									{/if}
								</div>
							</div>
							<a
								href={res.file_url}
								download
								class="flex shrink-0 items-center gap-1.5 rounded-full bg-slate-100 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-200"
							>
								<Download class="h-3.5 w-3.5" />
								Tải PDF
							</a>
						</div>
						<div
							class="h-180 w-full overflow-hidden rounded-xl border border-slate-100 bg-slate-50"
						>
							<iframe class="h-full w-full" src={res.file_url} title={res.title}></iframe>
						</div>
					</div>
				{:else if res.resource_type === 'TEXT' && res.content}
					<!-- BÀI ĐỌC DẠNG TEXT: nội dung do gia sư soạn, hiển thị trực tiếp -->
					<div
						class="rounded-2xl border border-slate-200/70 bg-white p-6 shadow-sm shadow-slate-200/50"
					>
						<div class="mb-4 flex items-center gap-3">
							<div
								class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-violet-50 text-violet-600"
							>
								<BookOpen class="h-5 w-5" />
							</div>
							<h2
								class="text-sm font-semibold text-slate-800"
								style="font-family:'Sora',sans-serif;"
							>
								{res.title}
							</h2>
						</div>
						<div
							class="max-h-150 overflow-y-auto whitespace-pre-line rounded-xl bg-slate-50 p-4 text-sm leading-relaxed text-slate-700"
						>
							{res.content}
						</div>
					</div>
				{:else if res.file_url}
					<div
						class="rounded-2xl border border-slate-200/70 bg-white p-6 shadow-sm shadow-slate-200/50"
					>
						<div class="mb-3 flex items-center gap-3">
							<div
								class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-amber-50 text-amber-600"
							>
								<Paperclip class="h-5 w-5" />
							</div>
							<h2
								class="text-sm font-semibold text-slate-800"
								style="font-family:'Sora',sans-serif;"
							>
								Tài liệu bổ sung
							</h2>
						</div>
						<div
							class="flex items-center justify-between gap-3 rounded-xl border border-slate-100 bg-slate-50 p-3"
						>
							<div class="flex min-w-0 items-center gap-3">
								<span
									class="shrink-0 rounded-md bg-white px-2 py-1 text-[10px] font-bold text-slate-500 shadow-sm"
								>
									{fileExt(res.file_url)}
								</span>
								<div class="min-w-0">
									<p class="truncate text-sm font-medium text-slate-700">{res.title}</p>
									{#if res.content}
										<p class="truncate text-xs text-slate-500">{res.content}</p>
									{/if}
								</div>
							</div>
							<a
								href={res.file_url}
								download
								class="flex shrink-0 items-center gap-1.5 rounded-full bg-white px-3 py-1.5 text-xs font-medium text-slate-600 shadow-sm hover:bg-slate-100"
							>
								<Download class="h-3.5 w-3.5" />
								Tải về
							</a>
						</div>
					</div>
				{/if}
			{/each}

			{#if resources.length === 0}
				<div
					class="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-8 text-center text-sm text-slate-400"
				>
					Bài học này chưa có tài liệu đính kèm.
				</div>
			{/if}
		</div>

		<!-- ĐIỀU HƯỚNG BÀI TRƯỚC / SAU -->
		<div class="mb-8 grid grid-cols-3 items-center gap-4">
			<div class="flex justify-start">
				{#if prevLesson}
					<button
						onclick={() => goto(`/course/${course_tree.id}/lesson/${prevLesson.id}`)}
						class="flex items-center gap-2 rounded-full border border-slate-200 bg-white px-5 py-2.5 text-sm font-medium text-slate-600 hover:bg-slate-50"
					>
						<ChevronLeft class="h-4 w-4" />
						{prevLesson.title}
					</button>
				{/if}
			</div>

			<div class="flex justify-center">
				{#if currentLessonInTree?.is_completed}
					<span
						class="flex items-center gap-2 rounded-full bg-emerald-600 px-6 py-2.5 text-sm font-semibold text-emerald-900"
					>
						Đã hoàn thành
					</span>
				{:else}
					<button
						onclick={handleComplete}
						disabled={isHandlingComplete}
						class="rounded-full bg-[#0C1550] px-6 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-indigo-900 disabled:opacity-60"
					>
						{isHandlingComplete ? 'Đang lưu...' : 'Hoàn thành'}
					</button>
				{/if}
			</div>

			<div class="flex justify-end">
				{#if nextLesson}
					<button
						onclick={() => goto(`/course/${course_tree.id}/lesson/${nextLesson.id}`)}
						class="flex items-center gap-2 rounded-full bg-[#0C1550] px-5 py-2.5 text-sm font-medium text-white hover:bg-indigo-900"
					>
						{nextLesson.title}
						<ChevronRight class="h-4 w-4" />
					</button>
				{/if}
			</div>
		</div>

		<!-- BÌNH LUẬN -->
		<div
			class="rounded-2xl border border-slate-200/70 bg-white p-6 pb-24 shadow-sm shadow-slate-200/50"
		>
			<h2 class="mb-4 text-sm font-semibold text-slate-800" style="font-family:'Sora',sans-serif;">
				Bình luận
			</h2>

			<div class="space-y-5">
				{#each topLevelComments as comment (comment.id)}
					<div>
						<!-- COMMENT GỐC -->
						<div class="flex items-start justify-between gap-3">
							<div class="flex items-start gap-3">
								<Avatar
									src={comment.created_by.avatar}
									name={comment.created_by.full_name}
									size="md"
								/>
								<div class="min-w-0 flex-1">
									<div class="flex items-center gap-2">
										<p class="text-xs font-semibold text-slate-700">
											{comment.created_by.full_name}
										</p>
									</div>
									<p class="text-sm text-slate-600">{comment.content}</p>
									<div class="mt-1 flex items-center gap-3">
										<p class="text-[11px] text-slate-400">
											{formatCommentDate(comment.created_at)}
										</p>
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
								canEdit={isTutor}
								isLoading={markingRightId === comment.id}
								onToggle={() => toggleMarkRight(comment)}
							/>
						</div>

						<!-- FORM TRẢ LỜI -->
						{#if replyingToId === comment.id}
							<div class="mt-3 ml-11 flex items-center gap-2">
								<input
									type="text"
									bind:value={replyContent}
									onkeydown={(e) => e.key === 'Enter' && submitReply(comment.id)}
									placeholder="Viết phản hồi..."
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

						<!-- CÁC REPLY -->
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
												<div class="flex items-center gap-2">
													<p class="text-xs font-semibold text-slate-700">
														{reply.created_by.full_name}
													</p>
												</div>
												<p class="text-sm text-slate-600">{reply.content}</p>
												<p class="mt-1 text-[11px] text-slate-400">
													{formatCommentDate(reply.created_at)}
												</p>
											</div>
										</div>

										<MarkRightButton
											isRight={reply.is_right}
											canEdit={isTutor}
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
					<p class="text-center text-sm text-slate-400">Chưa có bình luận nào.</p>
				{/if}
			</div>

			<div
				class="mt-5 flex w-full items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 py-2 pl-4 pr-4 transition-colors focus-within:border-indigo-300 focus-within:bg-white focus-within:ring-4 focus-within:ring-indigo-50"
			>
				<input
					type="text"
					bind:value={newComment}
					onkeydown={(e) => e.key === 'Enter' && submitComment()}
					placeholder="Nhập bình luận..."
					disabled={isSubmittingComment}
					class="min-w-0 flex-1 border-none bg-transparent text-sm text-slate-700 placeholder-slate-400 outline-none focus:ring-0"
				/>
				<button
					onclick={submitComment}
					disabled={!newComment.trim() || isSubmittingComment}
					class="flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-blue-600 transition-colors hover:bg-blue-50 disabled:opacity-40 disabled:hover:bg-transparent"
				>
					<Send class="h-4 w-4" />
				</button>
			</div>
		</div>
	</main>

	<!-- TRỢ LÝ AI NỔI -->
	<Chatbot userName={user?.full_name} />
</div>
