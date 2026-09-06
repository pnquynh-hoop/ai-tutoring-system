<script lang="ts">
	import { goto, invalidateAll } from '$app/navigation';
	import { page } from '$app/state';
	import { untrack } from 'svelte';
	import {
		createChapter,
		createLesson,
		deleteChapter,
		deleteLesson,
		publishChapter,
		publishLesson,
		updateChapter,
		updateLesson
	} from '$lib/api/calledAPI';
	import { getApiErrorMessage } from '$lib/api/errors';
	import type { Chapter, Lesson } from '$lib/api/entities';
	import { nextOrder } from '$lib/utils/order';
	import { auth } from '$lib/stores/auth.svelte';
	import { treeSelection } from '$lib/stores/courseTree.svelte';
	import { confirmAction } from '$lib/stores/confirm.svelte';
	import { showToast } from '$lib/stores/toast.svelte';
	import Avatar from '$lib/components/Avatar.svelte';
	import FieldError from '$lib/components/FieldError.svelte';
	import {
		capError,
		ENTITY_CAPS,
		FIELD_LIMITS,
		isNearCap,
		quotaLabel,
		textError
	} from '$lib/utils/validation';
	import type { LayoutProps } from './$types';
	import {
		BarChart3,
		Check,
		ChevronDown,
		ChevronRight,
		ClipboardCheck,
		ClipboardEdit,
		Globe,
		GlobeLock,
		Home,
		Menu,
		Network,
		Pencil,
		Plus,
		Trash2,
		X
	} from 'lucide-svelte';

	let { data, children }: LayoutProps = $props();

	let courseId = $derived(data.courseId);
	let courseName = $derived(data.tree.name);
	let chapters = $derived(data.tree.chapters);
	let chapterQuota = $derived(quotaLabel(chapters.length, ENTITY_CAPS.chaptersPerCourse));
	let chapterNearCap = $derived(isNearCap(chapters.length, ENTITY_CAPS.chaptersPerCourse, 5));

	let tutorName = $derived(auth.user?.full_name);
	let avatarUrl = $derived(auth.user?.avatar);

	let treeUrl = $derived(`/course-mgt/${courseId}`);
	let statsUrl = $derived(`/course-mgt/${courseId}/stats`);
	let gradingUrl = $derived(`/course-mgt/${courseId}/grading`);

	let onTree = $derived(page.url.pathname === treeUrl);
	let onStats = $derived(page.url.pathname === statsUrl);
	let onGrading = $derived(page.url.pathname === gradingUrl);
	let onAssignment = $derived(page.url.pathname.endsWith('/assignment-mgt'));

	let sidebarCollapsed = $state(false);

	$effect(() => {
		sidebarCollapsed = onGrading;
	});
	let treeExpanded = $state(false);

	$effect(() => {
		if (onStats || onGrading) treeExpanded = false;
	});

	let expandedChapterId = $state<number | null>(null);

	$effect(() => {
		const tree = chapters;
		untrack(() => {
			const lessonIds = tree.flatMap((chapter) => chapter.lessons).map((lesson) => lesson.id);
			if (treeSelection.lessonId === null || !lessonIds.includes(treeSelection.lessonId)) {
				treeSelection.lessonId = tree[0]?.lessons[0]?.id ?? null;
			}

			const chapterIds = tree.map((chapter) => chapter.id);
			if (expandedChapterId === null || !chapterIds.includes(expandedChapterId)) {
				expandedChapterId = tree[0]?.id ?? null;
			}
		});
	});

	function openTree() {
		if (onTree) {
			treeExpanded = !treeExpanded;
			return;
		}
		treeExpanded = true;
		goto(treeUrl);
	}

	function selectLesson(lessonId: number) {
		treeSelection.lessonId = lessonId;
		if (!onTree) goto(treeUrl);
	}

	function openChapterAssignment(chapterId: number) {
		goto(`/course-mgt/${courseId}/assignment-mgt?chapter=${chapterId}`, { invalidateAll: true });
	}

	let addingChapter = $state(false);
	let newChapterTitle = $state('');
	let editingChapterId = $state<number | null>(null);
	let editChapterTitle = $state('');
	let isSavingTree = $state(false);
	let treeErrors = $state<Record<string, string>>({});

	function setTreeError(field: string, message: string) {
		treeErrors = { ...treeErrors, [field]: message };
		return message === '';
	}

	function startAddChapter() {
		addingChapter = true;
		newChapterTitle = '';
		setTreeError('newChapter', '');
	}

	async function confirmAddChapter() {
		if (isSavingTree) return;
		if (!setTreeError('newChapter', textError(newChapterTitle, FIELD_LIMITS.title, 'Tên chương')))
			return;
		if (
			!setTreeError(
				'newChapter',
				capError(chapters.length, ENTITY_CAPS.chaptersPerCourse, 'Mỗi khóa học chỉ có số chương')
			)
		)
			return;

		isSavingTree = true;
		try {
			await createChapter({
				course: courseId,
				title: newChapterTitle.trim(),
				order: nextOrder(chapters)
			});
			await invalidateAll();
			addingChapter = false;
			showToast('Đã thêm chương', 'success');
		} catch (err) {
			showToast(getApiErrorMessage(err, 'Thêm chương không thành công.'), 'error');
		} finally {
			isSavingTree = false;
		}
	}

	function startEditChapter(chapter: Chapter) {
		editingChapterId = chapter.id;
		editChapterTitle = chapter.title;
		setTreeError('editChapter', '');
	}

	async function confirmEditChapter(chapter: Chapter) {
		if (isSavingTree) return;
		if (!setTreeError('editChapter', textError(editChapterTitle, FIELD_LIMITS.title, 'Tên chương')))
			return;

		isSavingTree = true;
		try {
			await updateChapter(chapter.id, { title: editChapterTitle.trim() });
			await invalidateAll();
			editingChapterId = null;
		} catch (err) {
			showToast(getApiErrorMessage(err, 'Đổi tên chương không thành công.'), 'error');
		} finally {
			isSavingTree = false;
		}
	}

	async function removeChapter(chapter: Chapter) {
		const agreed = await confirmAction({
			title: 'Xoá chương này?',
			message: `Chương "${chapter.title}" và toàn bộ bài học bên trong sẽ bị xoá. Thao tác này không hoàn tác được.`,
			confirmLabel: 'Xoá chương',
			tone: 'danger'
		});
		if (!agreed) return;

		try {
			await deleteChapter(chapter.id);
			await invalidateAll();
			showToast('Đã xoá chương', 'success');
		} catch (err) {
			showToast(getApiErrorMessage(err, 'Xoá chương không thành công.'), 'error');
		}
	}

	async function confirmPublishChapter(chapter: Chapter) {
		const agreed = await confirmAction({
			title: 'Công khai chương cho học sinh?',
			message: `Học sinh trong khóa sẽ thấy chương "${chapter.title}". Đã công khai thì không đưa về lại bản nháp được.`,
			confirmLabel: 'Công khai',
			tone: 'warning'
		});
		if (!agreed) return;

		try {
			await publishChapter(chapter.id);
			await invalidateAll();
			showToast('Đã công khai chương', 'success');
		} catch (err) {
			showToast(getApiErrorMessage(err, 'Công khai chương không thành công.'), 'error');
		}
	}

	let addingLessonChapterId = $state<number | null>(null);
	let newLessonTitle = $state('');
	let editingLessonId = $state<number | null>(null);
	let editLessonTitle = $state('');

	function startAddLesson(chapterId: number) {
		addingLessonChapterId = chapterId;
		newLessonTitle = '';
		setTreeError('newLesson', '');
	}

	async function confirmAddLesson(chapter: Chapter) {
		if (isSavingTree) return;
		if (!setTreeError('newLesson', textError(newLessonTitle, FIELD_LIMITS.title, 'Tên bài học')))
			return;
		if (
			!setTreeError(
				'newLesson',
				capError(
					chapter.lessons.length,
					ENTITY_CAPS.lessonsPerChapter,
					'Mỗi chương chỉ có số bài học'
				)
			)
		)
			return;

		isSavingTree = true;
		try {
			await createLesson({
				chapter: chapter.id,
				title: newLessonTitle.trim(),
				order: nextOrder(chapter.lessons)
			});
			await invalidateAll();
			addingLessonChapterId = null;
			showToast('Đã thêm bài học', 'success');
		} catch (err) {
			showToast(getApiErrorMessage(err, 'Thêm bài học không thành công.'), 'error');
		} finally {
			isSavingTree = false;
		}
	}

	function startEditLesson(lesson: Lesson) {
		editingLessonId = lesson.id;
		editLessonTitle = lesson.title;
		setTreeError('editLesson', '');
	}

	async function confirmEditLesson(lesson: Lesson) {
		if (isSavingTree) return;
		if (!setTreeError('editLesson', textError(editLessonTitle, FIELD_LIMITS.title, 'Tên bài học')))
			return;

		isSavingTree = true;
		try {
			await updateLesson(lesson.id, { title: editLessonTitle.trim() });
			await invalidateAll();
			editingLessonId = null;
		} catch (err) {
			showToast(getApiErrorMessage(err, 'Đổi tên bài học không thành công.'), 'error');
		} finally {
			isSavingTree = false;
		}
	}

	async function removeLesson(lesson: Lesson) {
		const agreed = await confirmAction({
			title: 'Xoá bài học này?',
			message: `Bài học "${lesson.title}" cùng tài nguyên và thảo luận bên trong sẽ bị xoá. Thao tác này không hoàn tác được.`,
			confirmLabel: 'Xoá bài học',
			tone: 'danger'
		});
		if (!agreed) return;

		try {
			await deleteLesson(lesson.id);
			if (treeSelection.lessonId === lesson.id) treeSelection.lessonId = null;
			await invalidateAll();
			showToast('Đã xoá bài học', 'success');
		} catch (err) {
			showToast(getApiErrorMessage(err, 'Xoá bài học không thành công.'), 'error');
		}
	}

	async function confirmPublishLesson(lesson: Lesson) {
		const agreed = await confirmAction({
			title: 'Công khai bài học cho học sinh?',
			message: `Học sinh trong khóa sẽ thấy bài học "${lesson.title}". Đã công khai thì không đưa về lại bản nháp được.`,
			confirmLabel: 'Công khai',
			tone: 'warning'
		});
		if (!agreed) return;

		try {
			await publishLesson(lesson.id);
			await invalidateAll();
			showToast('Đã công khai bài học', 'success');
		} catch (err) {
			showToast(getApiErrorMessage(err, 'Công khai bài học không thành công.'), 'error');
		}
	}
</script>

<div class="flex h-screen w-full bg-slate-50">
	<aside
		class={`relative flex h-full shrink-0 flex-col overflow-hidden bg-brand-800 text-white transition-all duration-300 ${sidebarCollapsed ? 'w-16' : 'w-80'}`}
	>
		<div
			class={`flex items-center border-b border-white/10 py-6 ${sidebarCollapsed ? 'justify-center px-0' : 'justify-between px-5'}`}
		>
			{#if !sidebarCollapsed}
				<span class="truncate font-semibold tracking-tight font-heading">
					{courseName}
				</span>
			{/if}
			<button
				onclick={() => (sidebarCollapsed = !sidebarCollapsed)}
				class="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-white/10 hover:bg-white/20"
			>
				<Menu class="h-4 w-4 text-brand-100/60" />
			</button>
		</div>

		{#if sidebarCollapsed}
			<div class="flex-1"></div>
		{:else}
			<nav class="sidebar-nav flex-1 space-y-1 overflow-y-auto px-3 py-4">
				<button
					onclick={openTree}
					class={`flex w-full items-center gap-2.5 rounded-xl px-3 py-2.5 text-sm transition-all ${
						onTree
							? 'bg-white/10 font-semibold text-white'
							: 'text-brand-100/60 hover:bg-white/5 hover:text-white'
					}`}
				>
					<Network class="h-4 w-4 shrink-0 opacity-70" />
					<span class="flex-1 text-left">Cây khóa học</span>
					{#if treeExpanded}
						<ChevronDown class="h-3.5 w-3.5 shrink-0 opacity-50" />
					{:else}
						<ChevronRight class="h-3.5 w-3.5 shrink-0 opacity-50" />
					{/if}
				</button>

				{#if treeExpanded}
					<div class="relative ml-4 space-y-1 pl-3">
						<div class="absolute bottom-2 left-0 top-0 w-px bg-white/10"></div>

						<button
							onclick={startAddChapter}
							class="flex w-full items-center justify-center gap-2 rounded-xl border border-dashed border-white/20 py-2 text-xs font-semibold text-brand-100/70 hover:border-white/40 hover:text-white"
						>
							<Plus class="h-3.5 w-3.5" />
							Thêm chương
							<span class={chapterNearCap ? 'text-amber-300' : 'text-brand-100/40'}>
								· {chapterQuota}
							</span>
						</button>

						{#if addingChapter}
							<div class="flex items-center gap-1.5 px-1">
								<input
									class="min-w-0 flex-1 rounded-lg bg-white/10 px-3 py-1.5 text-xs text-white placeholder-brand-100/40 outline-none focus:bg-white/15"
									placeholder="Tên chương mới..."
									bind:value={newChapterTitle}
									onkeydown={(e) => e.key === 'Enter' && confirmAddChapter()}
								/>
								<button
									onclick={confirmAddChapter}
									class="rounded-lg bg-brand-500/90 p-1.5 hover:bg-brand-500"
								>
									<Check class="h-3.5 w-3.5" />
								</button>
								<button
									onclick={() => (addingChapter = false)}
									class="rounded-lg bg-white/10 p-1.5 hover:bg-white/20"
								>
									<X class="h-3.5 w-3.5" />
								</button>
							</div>
							<FieldError tone="dark" message={treeErrors.newChapter} />
						{/if}

						{#each chapters as chapter, chapterIndex (chapter.id)}
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
										<button
											onclick={() => confirmEditChapter(chapter)}
											class="rounded-lg p-1 hover:bg-white/10"
										>
											<Check class="h-3.5 w-3.5 text-emerald-400" />
										</button>
										<button
											onclick={() => (editingChapterId = null)}
											class="rounded-lg p-1 hover:bg-white/10"
										>
											<X class="h-3.5 w-3.5 text-brand-100/50" />
										</button>
									{:else}
										<button
											onclick={() =>
												(expandedChapterId = expandedChapterId === chapter.id ? null : chapter.id)}
											class="flex min-w-0 flex-1 items-center gap-2 text-left text-sm font-medium text-brand-100/80"
										>
											{#if expandedChapterId === chapter.id}
												<ChevronDown class="h-3.5 w-3.5 shrink-0 opacity-60" />
											{:else}
												<ChevronRight class="h-3.5 w-3.5 shrink-0 opacity-60" />
											{/if}
											<span class="truncate">{chapter.title}</span>
										</button>
										{#if chapter.is_published}
											<span
												title="Đã công khai"
												class="shrink-0 rounded-full bg-emerald-500/15 p-1"
											>
												<Globe class="h-3 w-3 text-emerald-300" />
											</span>
										{:else}
											<button
												onclick={() => confirmPublishChapter(chapter)}
												title="Công khai chương cho học sinh"
												class="shrink-0 rounded-lg p-1 opacity-0 hover:bg-emerald-500/20 group-hover:opacity-100"
											>
												<GlobeLock class="h-3 w-3 text-brand-100/60" />
											</button>
										{/if}
										<button
											onclick={() => startEditChapter(chapter)}
											class="shrink-0 rounded-lg p-1 opacity-0 hover:bg-white/10 group-hover:opacity-100"
										>
											<Pencil class="h-3 w-3 text-brand-100/60" />
										</button>
										<button
											onclick={() => removeChapter(chapter)}
											class="shrink-0 rounded-lg p-1 opacity-0 hover:bg-rose-500/20 group-hover:opacity-100"
										>
											<Trash2 class="h-3 w-3 text-rose-300" />
										</button>
									{/if}
								</div>
								<FieldError tone="dark" message={treeErrors.editChapter} />

								{#if expandedChapterId === chapter.id}
									<div class="relative ml-5 mt-1 space-y-0.5 pl-4">
										<div class="absolute bottom-2 left-0 top-0 w-px bg-white/10"></div>
										{#each chapter.lessons as lesson (lesson.id)}
											<div
												class={`group flex items-center gap-1 rounded-lg px-2 py-1.5 ${
													onTree && treeSelection.lessonId === lesson.id
														? 'bg-white/10'
														: 'hover:bg-white/5'
												}`}
											>
												{#if editingLessonId === lesson.id}
													<input
														class="min-w-0 flex-1 rounded-lg bg-white/10 px-2 py-1 text-xs text-white outline-none"
														bind:value={editLessonTitle}
														onkeydown={(e) => e.key === 'Enter' && confirmEditLesson(lesson)}
													/>
													<button
														onclick={() => confirmEditLesson(lesson)}
														class="rounded-lg p-1 hover:bg-white/10"
													>
														<Check class="h-3.5 w-3.5 text-emerald-400" />
													</button>
													<button
														onclick={() => (editingLessonId = null)}
														class="rounded-lg p-1 hover:bg-white/10"
													>
														<X class="h-3.5 w-3.5 text-brand-100/50" />
													</button>
												{:else}
													<button
														onclick={() => selectLesson(lesson.id)}
														class={`min-w-0 flex-1 truncate text-left text-[13px] ${
															onTree && treeSelection.lessonId === lesson.id
																? 'font-semibold text-white'
																: 'text-brand-100/60'
														}`}
													>
														{lesson.title}
													</button>
													{#if lesson.is_published}
														<span
															title="Đã công khai"
															class="shrink-0 rounded-full bg-emerald-500/15 p-1"
														>
															<Globe class="h-3 w-3 text-emerald-300" />
														</span>
													{:else}
														<button
															onclick={() => confirmPublishLesson(lesson)}
															title="Công khai bài học cho học sinh"
															class="shrink-0 rounded-lg p-1 opacity-0 hover:bg-emerald-500/20 group-hover:opacity-100"
														>
															<GlobeLock class="h-3 w-3 text-brand-100/60" />
														</button>
													{/if}
													<button
														onclick={() => startEditLesson(lesson)}
														class="shrink-0 rounded-lg p-1 opacity-0 hover:bg-white/10 group-hover:opacity-100"
													>
														<Pencil class="h-3 w-3 text-brand-100/60" />
													</button>
													<button
														onclick={() => removeLesson(lesson)}
														class="shrink-0 rounded-lg p-1 opacity-0 hover:bg-rose-500/20 group-hover:opacity-100"
													>
														<Trash2 class="h-3 w-3 text-rose-300" />
													</button>
												{/if}
											</div>
											<FieldError tone="dark" message={treeErrors.editLesson} />
										{/each}

										{#if chapter.assignment === null}
											<button
												onclick={() => openChapterAssignment(chapter.id)}
												class={`flex w-full items-center gap-1.5 rounded-lg px-2 py-1.5 text-[12px] transition-all ${
													onAssignment && page.url.searchParams.get('chapter') === String(chapter.id)
														? 'bg-white/10 font-semibold text-white'
														: 'text-brand-100/40 hover:bg-white/5 hover:text-brand-100/70'
												}`}
											>
												<Plus class="h-3 w-3" />
												Thêm bài tập
											</button>
										{:else}
											<button
												onclick={() => openChapterAssignment(chapter.id)}
												class={`flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-[13px] transition-all ${
													onAssignment && page.url.searchParams.get('chapter') === String(chapter.id)
														? 'bg-white/10 font-semibold text-white'
														: 'text-brand-100/60 hover:bg-white/5 hover:text-white'
												}`}
											>
												<ClipboardEdit class="h-3.5 w-3.5 shrink-0 opacity-70" />
												<span class="min-w-0 flex-1 truncate text-left">
													Bài tập ôn chương {chapterIndex + 1}
												</span>
											</button>
										{/if}

										{#if addingLessonChapterId === chapter.id}
											<div class="flex items-center gap-1.5 px-2 py-1">
												<input
													class="min-w-0 flex-1 rounded-lg bg-white/10 px-2 py-1 text-xs text-white placeholder-brand-100/40 outline-none"
													placeholder="Tên bài học mới..."
													bind:value={newLessonTitle}
													onkeydown={(e) => e.key === 'Enter' && confirmAddLesson(chapter)}
												/>
												<button
													onclick={() => confirmAddLesson(chapter)}
													class="rounded-lg bg-brand-500/90 p-1 hover:bg-brand-500"
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
											<FieldError tone="dark" message={treeErrors.newLesson} />
										{:else}
											<button
												onclick={() => startAddLesson(chapter.id)}
												class="flex w-full items-center gap-1.5 rounded-lg px-2 py-1.5 text-[12px] text-brand-100/40 hover:bg-white/5 hover:text-brand-100/70"
											>
												<Plus class="h-3 w-3" />
												Thêm bài học
												<span
													class={isNearCap(chapter.lessons.length, ENTITY_CAPS.lessonsPerChapter, 5)
														? 'text-amber-300'
														: 'text-brand-100/30'}
												>
													· {quotaLabel(chapter.lessons.length, ENTITY_CAPS.lessonsPerChapter)}
												</span>
											</button>
										{/if}
									</div>
								{/if}
							</div>
						{/each}
					</div>
				{/if}

				<button
					onclick={() => goto(statsUrl)}
					class={`flex w-full items-center gap-2.5 rounded-xl px-3 py-2.5 text-sm transition-all ${
						onStats
							? 'bg-white/10 font-semibold text-white'
							: 'text-brand-100/60 hover:bg-white/5 hover:text-white'
					}`}
				>
					<BarChart3 class="h-4 w-4 shrink-0 opacity-70" />
					<span class="flex-1 text-left">Thống kê</span>
				</button>

				<button
					onclick={() => goto(gradingUrl)}
					class={`flex w-full items-center gap-2.5 rounded-xl px-3 py-2.5 text-sm transition-all ${
						onGrading
							? 'bg-white/10 font-semibold text-white'
							: 'text-brand-100/60 hover:bg-white/5 hover:text-white'
					}`}
				>
					<ClipboardCheck class="h-4 w-4 shrink-0 opacity-70" />
					<span class="flex-1 text-left">Bài tập & chấm điểm</span>
				</button>
			</nav>
		{/if}

		<div class={`border-t border-white/10 py-4 ${sidebarCollapsed ? 'px-0' : 'px-3'}`}>
			<div
				class={`flex items-center rounded-xl py-2 hover:bg-white/5 ${sidebarCollapsed ? 'justify-center px-0' : 'gap-3 px-2'}`}
			>
				<Avatar src={avatarUrl} name={tutorName ?? ''} size="lg" />
				{#if !sidebarCollapsed}
					<div class="min-w-0 flex-1">
						<p class="truncate text-sm font-medium text-white">{tutorName}</p>
						<p class="truncate text-xs text-brand-100/50">Gia sư</p>
					</div>
				{/if}
			</div>
		</div>
	</aside>

	<div class="flex min-w-0 flex-1 flex-col">
		<header
			class="flex items-center justify-between border-b border-slate-200/70 bg-white/80 px-8 py-4 backdrop-blur"
		>
			<h1 class="text-sm font-semibold text-slate-800 font-heading">
				{#if onStats}
					Thống kê khóa học
				{:else if onGrading}
					Bài tập & chấm điểm
				{:else if onAssignment}
					Soạn bài tập ôn chương
				{:else}
					Cây khóa học
				{/if}
			</h1>

			<a
				href="/tutor-dashboard"
				class="flex shrink-0 items-center gap-2 rounded-full bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
			>
				<Home class="h-4 w-4" />
				Trang chủ
			</a>
		</header>

		<main class="flex-1 overflow-y-auto">
			{@render children()}
		</main>
	</div>
</div>

<style>
	.sidebar-nav {
		scrollbar-width: thin;
		scrollbar-color: rgba(255, 255, 255, 0.15) transparent;
	}

	.sidebar-nav::-webkit-scrollbar {
		width: 6px;
	}

	.sidebar-nav::-webkit-scrollbar-thumb {
		background-color: rgba(255, 255, 255, 0.15);
		border-radius: 9999px;
	}

	.sidebar-nav::-webkit-scrollbar-track {
		background: transparent;
	}
</style>
