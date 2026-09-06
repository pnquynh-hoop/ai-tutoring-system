<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import {
		createResource,
		deleteResource,
		getLessonResources,
		getListComments,
		postComment,
		ingestResource,
		publishResource,
		toggleCommentRight,
		updateLesson
	} from '$lib/api/calledAPI';
	import { getApiErrorMessage } from '$lib/api/errors';
	import type { Comment, RagStatus, ResourceType, TutorLessonResource } from '$lib/api/entities';
	import { treeSelection } from '$lib/stores/courseTree.svelte';
	import { confirmAction } from '$lib/stores/confirm.svelte';
	import { showToast } from '$lib/stores/toast.svelte';
	import { fileNameFromUrl } from '$lib/utils/resource';
	import Avatar from '$lib/components/Avatar.svelte';
	import MarkRightButton from '$lib/components/MarkRightButton.svelte';
	import FieldError from '$lib/components/FieldError.svelte';
	import {
		DOCUMENT_EXTENSIONS,
		documentFileError,
		FIELD_LIMITS,
		hasError,
		MAX_DOCUMENT_MB,
		textError
	} from '$lib/utils/validation';
	import type { PageProps } from './$types';
	import {
		Check,
		FileText,
		Globe,
		Warehouse,
		Paperclip,
		Pencil,
		PlayCircle,
		Plus,
		Send,
		Trash2
	} from 'lucide-svelte';

	let { data }: PageProps = $props();

	let chapters = $derived(data.tree.chapters);

	let selectedLessonId = $derived(treeSelection.lessonId);
	let selectedLesson = $derived(
		chapters
			.flatMap((chapter) => chapter.lessons)
			.find((lesson) => lesson.id === selectedLessonId) ?? null
	);
	let selectedChapter = $derived(
		chapters.find((chapter) => chapter.lessons.some((lesson) => lesson.id === selectedLessonId)) ??
			null
	);

	let isRenaming = $state(false);
	let renameTitle = $state('');
	let isSavingRename = $state(false);
	let renameError = $state('');

	function startRename() {
		if (!selectedLesson) return;
		renameTitle = selectedLesson.title;
		renameError = '';
		isRenaming = true;
	}

	async function confirmRename() {
		if (!selectedLesson || isSavingRename) return;

		renameError = textError(renameTitle, FIELD_LIMITS.title, 'Tên bài học');
		if (renameError) return;

		isSavingRename = true;
		try {
			await updateLesson(selectedLesson.id, { title: renameTitle.trim() });
			await invalidateAll();
			isRenaming = false;
		} catch (err) {
			showToast(getApiErrorMessage(err, 'Đổi tên bài học không thành công.'), 'error');
		} finally {
			isSavingRename = false;
		}
	}

	let resources = $state<TutorLessonResource[]>([]);
	let addingResource = $state(false);
	let isSavingResource = $state(false);
	let resourceErrors = $state<Record<string, string>>({});

	function clearResourceError(field: string) {
		resourceErrors = { ...resourceErrors, [field]: '' };
	}

	function validateResource(): boolean {
		const errors: Record<string, string> = {
			title: textError(newResource.title, FIELD_LIMITS.title, 'Tên tài nguyên'),
			video_url: '',
			file_url: '',
			content: ''
		};

		if (newResource.resource_type === 'VIDEO_URL') {
			errors.video_url = textError(newResource.video_url, FIELD_LIMITS.url, 'Đường dẫn video');
		} else if (newResource.resource_type === 'PDF_FILE') {
			errors.file_url = documentFileError(newResource.file_url, 'Tệp tài liệu');
		} else {
			errors.content = textError(newResource.content, FIELD_LIMITS.resourceContent, 'Nội dung');
		}

		resourceErrors = errors;
		return !hasError(errors);
	}
	let newResource = $state<{
		title: string;
		resource_type: ResourceType;
		content: string;
		video_url: string;
		file_url: File | null;
	}>({ title: '', resource_type: 'VIDEO_URL', content: '', video_url: '', file_url: null });

	function pickResourceFile(event: Event) {
		const input = event.currentTarget as HTMLInputElement;
		newResource.file_url = input.files?.[0] ?? null;
		clearResourceError('file_url');
	}

	const resourceTypeLabel: Record<ResourceType, string> = {
		VIDEO_URL: 'Video',
		PDF_FILE: 'Tệp PDF',
		OTHERS: 'Khác'
	};

	function startAddResource() {
		addingResource = true;
		resourceErrors = {};
		newResource = {
			title: '',
			resource_type: 'VIDEO_URL',
			content: '',
			video_url: '',
			file_url: null
		};
	}

	async function confirmAddResource() {
		if (!selectedLessonId || isSavingResource) return;
		if (!validateResource()) return;

		isSavingResource = true;
		try {
			await createResource({
				lesson: selectedLessonId,
				title: newResource.title.trim(),
				resource_type: newResource.resource_type,
				content: newResource.resource_type === 'OTHERS' ? newResource.content || null : null,
				video_url: newResource.resource_type === 'VIDEO_URL' ? newResource.video_url || null : null,
				file_url: newResource.resource_type === 'PDF_FILE' ? newResource.file_url : null
			});
			resources = await getLessonResources(selectedLessonId);
			addingResource = false;
			showToast('Đã thêm tài nguyên', 'success');
		} catch (err) {
			showToast(getApiErrorMessage(err, 'Thêm tài nguyên không thành công.'), 'error');
		} finally {
			isSavingResource = false;
		}
	}

	async function confirmPublishResource(resource: TutorLessonResource) {
		const agreed = await confirmAction({
			title: 'Công khai tài nguyên cho học sinh?',
			message: `Học sinh trong khóa sẽ xem được "${resource.title}". Đã công khai thì không đưa về lại bản nháp được.`,
			confirmLabel: 'Công khai',
			tone: 'warning'
		});
		if (!agreed) return;

		try {
			await publishResource(resource.id);
			if (selectedLessonId) {
				resources = await getLessonResources(selectedLessonId);
			}
			showToast('Đã công khai tài nguyên', 'success');
		} catch (err) {
			showToast(getApiErrorMessage(err, 'Công khai tài nguyên không thành công.'), 'error');
		}
	}

	const ragStatusLabel: Record<RagStatus, string> = {
		PENDING: 'Chưa nạp',
		PROCESSING: 'Đang nạp',
		INDEXED: 'Đã nạp',
		FAILED: 'Nạp lỗi'
	};

	const ragStatusStyle: Record<RagStatus, string> = {
		PENDING: 'bg-slate-100 text-slate-500',
		PROCESSING: 'bg-sky-50 text-sky-600',
		INDEXED: 'bg-emerald-50 text-emerald-600',
		FAILED: 'bg-rose-50 text-rose-600'
	};

	function canIngest(resource: TutorLessonResource): boolean {
		if (resource.rag_status === 'PROCESSING') return false;
		return Boolean(resource.content) || Boolean(resource.file_url);
	}

	async function confirmIngestResource(resource: TutorLessonResource) {
		const isReload = resource.rag_status === 'INDEXED';
		const agreed = await confirmAction({
			title: isReload ? 'Nạp lại tài nguyên vào trợ lý AI?' : 'Nạp tài nguyên vào trợ lý AI?',
			message:
				`Hệ thống sẽ đọc lại toàn bộ "${resource.title}", cắt thành từng đoạn rồi gọi API nhúng ` +
				'vector của Gemini. Tài liệu nhiều trang có thể mất vài phút và tính vào hạn mức gọi API trong ngày.' +
				(isReload ? ' Tài nguyên này đã nạp rồi, nạp lại sẽ cập nhật theo nội dung mới nhất.' : ''),
			confirmLabel: 'Nạp vào trợ lý AI',
			tone: 'warning'
		});
		if (!agreed) return;

		try {
			await ingestResource(resource.id);
			await refreshResources();
			showToast('Đã đưa tài nguyên vào hàng đợi nạp', 'success');
		} catch (err) {
			showToast(getApiErrorMessage(err, 'Nạp tài nguyên không thành công.'), 'error');
		}
	}

	async function refreshResources() {
		if (!selectedLessonId) return;
		resources = await getLessonResources(selectedLessonId);
	}

	$effect(() => {
		if (!resources.some((resource) => resource.rag_status === 'PROCESSING')) return;

		const timer = setInterval(() => {
			refreshResources().catch(() => {});
		}, 5000);
		return () => clearInterval(timer);
	});

	async function removeResource(resource: TutorLessonResource) {
		const agreed = await confirmAction({
			title: 'Xoá tài nguyên này?',
			message: `Tài nguyên "${resource.title}" sẽ bị gỡ khỏi bài học. Thao tác này không hoàn tác được.`,
			confirmLabel: 'Xoá tài nguyên',
			tone: 'danger'
		});
		if (!agreed) return;

		try {
			await deleteResource(resource.id);
			resources = resources.filter((item) => item.id !== resource.id);
			showToast('Đã xoá tài nguyên', 'success');
		} catch (err) {
			showToast(getApiErrorMessage(err, 'Xoá tài nguyên không thành công.'), 'error');
		}
	}

	let comments = $state<Comment[]>([]);

	let topLevelComments = $derived(comments.filter((comment) => comment.parent === null));

	function getReplies(parentId: number): Comment[] {
		return comments.filter((comment) => comment.parent === parentId);
	}

	$effect(() => {
		const lessonId = selectedLessonId;
		if (!lessonId) {
			resources = [];
			comments = [];
			return;
		}

		let cancelled = false;
		Promise.all([getLessonResources(lessonId), getListComments(lessonId)])
			.then(([resourceList, commentList]) => {
				if (cancelled) return;
				resources = resourceList;
				comments = commentList;
			})
			.catch((err) => {
				if (!cancelled)
					showToast(getApiErrorMessage(err, 'Không tải được nội dung bài học.'), 'error');
			});

		return () => {
			cancelled = true;
		};
	});

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
	let replyError = $state('');
	let isSubmittingReply = $state(false);

	let newComment = $state('');
	let commentError = $state('');
	let isSubmittingComment = $state(false);

	function toggleReplyBox(commentId: number) {
		replyingToId = replyingToId === commentId ? null : commentId;
		replyContent = '';
	}

	async function submitComment() {
		if (isSubmittingComment || !selectedLessonId) return;

		commentError = textError(newComment, FIELD_LIMITS.comment, 'Bình luận');
		if (commentError) return;

		isSubmittingComment = true;
		try {
			const created = await postComment(selectedLessonId, newComment.trim());
			comments = [...comments, created];
			newComment = '';
		} catch (err) {
			showToast(getApiErrorMessage(err, 'Gửi bình luận không thành công.'), 'error');
		} finally {
			isSubmittingComment = false;
		}
	}

	async function submitReply(parentId: number) {
		if (isSubmittingReply || !selectedLessonId) return;

		replyError = textError(replyContent, FIELD_LIMITS.comment, 'Phản hồi');
		if (replyError) return;

		isSubmittingReply = true;
		try {
			const created = await postComment(selectedLessonId, replyContent.trim(), parentId);
			comments = [...comments, created];
			replyContent = '';
			replyingToId = null;
		} catch (err) {
			showToast(getApiErrorMessage(err, 'Gửi phản hồi không thành công.'), 'error');
		} finally {
			isSubmittingReply = false;
		}
	}

	let markingRightId = $state<number | null>(null);
	async function toggleMarkRight(comment: Comment) {
		if (markingRightId !== null) return;
		markingRightId = comment.id;
		try {
			const updated = await toggleCommentRight(comment.id);
			comment.is_right = updated.is_right;
		} catch (err) {
			showToast(getApiErrorMessage(err, 'Cập nhật không thành công.'), 'error');
		} finally {
			markingRightId = null;
		}
	}
</script>

<svelte:head>
	<title>Quản lý khóa học</title>
</svelte:head>

<div class="px-8 py-8">
	{#if !selectedLesson}
		<div class="flex h-full items-center justify-center py-20 text-center text-slate-400">
			<p>Chọn một bài học ở cây bên trái để chỉnh sửa.</p>
		</div>
	{:else}
		<div class="mx-auto max-w-4xl space-y-6">
			<div
				class="rounded-2xl border border-slate-200/70 bg-white p-6 shadow-sm shadow-slate-200/50"
			>
				<p class="text-xs text-slate-400">
					{selectedChapter?.title}
				</p>
				<div class="mt-1 flex items-center gap-2">
					{#if isRenaming}
						<input
							class="flex-1 rounded-xl border border-slate-200 px-3 py-1.5 text-lg font-bold text-slate-900 outline-none focus:border-brand-300"
							bind:value={renameTitle}
							onkeydown={(e) => e.key === 'Enter' && confirmRename()}
						/>
						<button
							onclick={confirmRename}
							class="rounded-xl bg-brand-600 px-3 py-1.5 text-white hover:bg-brand-700"
						>
							<Check class="h-4 w-4" />
						</button>
					{:else}
						<h1 class="flex-1 text-xl font-bold text-slate-900 font-heading">
							{selectedLesson.title}
						</h1>
						<button
							onclick={startRename}
							class="flex items-center gap-1.5 rounded-xl border border-brand-200 bg-brand-50 px-3 py-1.5 text-xs font-semibold text-brand-700 hover:bg-brand-100"
						>
							<Pencil class="h-3.5 w-3.5" />
							Đổi tên
						</button>
					{/if}
				</div>
				<FieldError message={renameError} />
			</div>

			<div
				class="rounded-2xl border border-slate-200/70 bg-white p-6 shadow-sm shadow-slate-200/50"
			>
				<div class="mb-4 flex items-center justify-between">
					<h2 class="text-sm font-semibold text-slate-800 font-heading">Tài nguyên bài học</h2>
					<button
						onclick={startAddResource}
						class="flex items-center gap-1.5 rounded-xl bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand-700"
					>
						<Plus class="h-3.5 w-3.5" />
						Thêm tài nguyên
					</button>
				</div>

				{#if addingResource}
					<div class="mb-4 space-y-3 rounded-xl border border-slate-200 bg-slate-50 p-4">
						<div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
							<input
								oninput={() => clearResourceError('title')}
								class="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm outline-none focus:border-brand-300"
								placeholder="Tên tài nguyên"
								bind:value={newResource.title}
							/>
							<FieldError message={resourceErrors.title} />
							<select
								class="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm outline-none focus:border-brand-300"
								bind:value={newResource.resource_type}
							>
								<option value="VIDEO_URL">Video</option>
								<option value="PDF_FILE">Tệp PDF</option>
								<option value="OTHERS">Khác</option>
							</select>
						</div>
						{#if newResource.resource_type === 'VIDEO_URL'}
							<input
								oninput={() => clearResourceError('video_url')}
								class="w-full rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm outline-none focus:border-brand-300"
								placeholder="Đường dẫn video (YouTube...)"
								bind:value={newResource.video_url}
							/>
							<FieldError message={resourceErrors.video_url} />
						{:else if newResource.resource_type === 'PDF_FILE'}
							<input
								type="file"
								accept={DOCUMENT_EXTENSIONS.join(',')}
								onchange={pickResourceFile}
								class="w-full rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm outline-none file:mr-3 file:rounded-lg file:border-0 file:bg-brand-600 file:px-3 file:py-1.5 file:text-xs file:font-semibold file:text-white hover:file:bg-brand-700 focus:border-brand-300"
							/>
							<p class="mt-1 text-xs text-slate-400">
								Chọn tệp từ máy ({DOCUMENT_EXTENSIONS.join(', ')}), tối đa {MAX_DOCUMENT_MB} MB. Hệ thống
								tự tải lên Cloudinary khi lưu.
							</p>
							<FieldError message={resourceErrors.file_url} />
						{:else}
							<textarea
								oninput={() => clearResourceError('content')}
								rows="2"
								class="w-full resize-none rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm outline-none focus:border-brand-300"
								placeholder="Nội dung văn bản"
								bind:value={newResource.content}></textarea>
							<FieldError message={resourceErrors.content} />
						{/if}
						<div class="flex justify-end gap-2">
							<button
								onclick={() => (addingResource = false)}
								class="rounded-lg bg-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-300"
							>
								Huỷ
							</button>
							<button
								onclick={confirmAddResource}
								class="rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand-700"
							>
								Lưu tài nguyên
							</button>
						</div>
					</div>
				{/if}

				<div class="space-y-2">
					{#each resources as res (res.id)}
						<div
							class="flex items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white p-3"
						>
							<div class="flex min-w-0 items-center gap-3">
								<div
									class={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${
										res.resource_type === 'VIDEO_URL'
											? 'bg-brand-50 text-brand-600'
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
										{#if res.video_url}
											• {res.video_url}{/if}
										{#if fileNameFromUrl(res.file_url)}
											• {fileNameFromUrl(res.file_url)}{/if}
									</p>
								</div>
							</div>
							<div class="flex shrink-0 items-center gap-1">
								{#if canIngest(res) || res.rag_status === 'PROCESSING'}
									<span
										class={`rounded-full px-2 py-0.5 text-[11px] font-medium ${ragStatusStyle[res.rag_status]}`}
									>
										{ragStatusLabel[res.rag_status]}
										{#if res.rag_status === 'INDEXED' && res.rag_progress}
											· {res.rag_progress} đoạn
										{/if}
									</span>
								{/if}
								{#if canIngest(res)}
									<button
										onclick={() => confirmIngestResource(res)}
										title={res.rag_status === 'INDEXED'
											? 'Nạp lại tài nguyên vào trợ lý AI'
											: 'Nạp tài nguyên vào trợ lý AI'}
										class="rounded-lg p-1.5 text-slate-400 hover:bg-sky-50 hover:text-sky-600"
									>
										<Warehouse class="h-4 w-4" />
									</button>
								{/if}
								{#if res.is_published}
									<span
										class="rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-emerald-600"
									>
										Đã công khai
									</span>
								{:else}
									<button
										onclick={() => confirmPublishResource(res)}
										title="Công khai tài nguyên cho học sinh"
										class="rounded-lg p-1.5 text-slate-400 hover:bg-emerald-50 hover:text-emerald-600"
									>
										<Globe class="h-4 w-4" />
									</button>
								{/if}
								<button
									onclick={() => removeResource(res)}
									class="rounded-lg p-1.5 text-slate-400 hover:bg-rose-50 hover:text-rose-500"
								>
									<Trash2 class="h-4 w-4" />
								</button>
							</div>
						</div>
					{/each}

					{#if resources.length === 0 && !addingResource}
						<p class="py-6 text-center text-sm text-slate-400">
							Bài học này chưa có tài nguyên nào.
						</p>
					{/if}

					{#if resources.length > 0}
						<p class="pt-2 text-[11px] leading-relaxed text-slate-400">
							Tài nguyên cần được nạp thì trợ lý học tập mới dùng được nội dung của nó. Tài nguyên
							đang ở trạng thái Nạp lỗi thì bấm nạp lại là được.
						</p>
					{/if}
				</div>
			</div>

			<div
				class="rounded-2xl border border-slate-200/70 bg-white p-6 shadow-sm shadow-slate-200/50"
			>
				<h2 class="mb-4 text-sm font-semibold text-slate-800 font-heading">
					Diễn đàn thảo luận
				</h2>

				<div class="space-y-5">
					{#each topLevelComments as comment (comment.id)}
						<div>
							<div class="flex items-start justify-between gap-3">
								<div class="flex items-start gap-3">
									<Avatar
										src={comment.created_by.avatar}
										name={comment.created_by.full_name}
										size="md"
									/>
									<div class="min-w-0 flex-1">
										<p class="text-xs font-semibold text-slate-700">
											{comment.created_by.full_name}
										</p>
										<p class="text-sm text-slate-600">{comment.content}</p>
										<div class="mt-1 flex items-center gap-3">
											<p class="text-[11px] text-slate-400">
												{formatCommentDate(comment.created_at)}
											</p>
											<button
												onclick={() => toggleReplyBox(comment.id)}
												class="text-[11px] font-medium text-slate-500 hover:text-brand-600"
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
								<div class="ml-11 mt-3">
									<div class="flex items-center gap-2">
										<input
											type="text"
											bind:value={replyContent}
											oninput={() => (replyError = '')}
											onkeydown={(e) => e.key === 'Enter' && submitReply(comment.id)}
											placeholder="Trả lời học sinh..."
											disabled={isSubmittingReply}
											class="min-w-0 flex-1 rounded-full border border-slate-200 bg-white px-4 py-2 text-sm text-slate-700 outline-none focus:border-brand-300"
										/>
										<button
											onclick={() => submitReply(comment.id)}
											disabled={!replyContent.trim() || isSubmittingReply}
											class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-blue-600 hover:bg-blue-50 disabled:opacity-40"
										>
											<Send class="h-4 w-4" />
										</button>
									</div>
									<FieldError message={replyError} />
								</div>
							{/if}

							{#if getReplies(comment.id).length > 0}
								<div class="ml-11 mt-3 space-y-3 border-l-2 border-slate-100 pl-4">
									{#each getReplies(comment.id) as reply (reply.id)}
										<div class="flex items-start justify-between gap-3">
											<div class="flex items-start gap-3">
												<Avatar
													src={reply.created_by.avatar}
													name={reply.created_by.full_name}
													size="sm"
													fromColor="from-brand-400"
													toColor="to-sky-300"
												/>
												<div class="min-w-0 flex-1">
													<p class="text-xs font-semibold text-slate-700">
														{reply.created_by.full_name}
													</p>
													<p class="text-sm text-slate-600">{reply.content}</p>
													<p class="mt-1 text-[11px] text-slate-400">
														{formatCommentDate(reply.created_at)}
													</p>
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

				<div
					class="mt-5 flex w-full items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 py-2 pl-4 pr-4 transition-colors focus-within:border-brand-300 focus-within:bg-white focus-within:ring-4 focus-within:ring-brand-50"
				>
					<input
						type="text"
						bind:value={newComment}
						oninput={() => (commentError = '')}
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
				<FieldError message={commentError} />
			</div>
		</div>
	{/if}
</div>
