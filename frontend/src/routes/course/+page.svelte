<script lang="ts">
	import {
		Home,
		ChevronRight,
		ChevronLeft,
		Star,
		Bot,
		Target,
		BookOpen,
		PenLine,
		Dumbbell,
		Heart,
		Send,
		Menu
	} from 'lucide-svelte';

	let courseName = $state('Tiếng anh 12');
	let studentName = $state('Quỳnh');

	let chapters = $state([
		{ id: 1, name: 'Chương 1', lessons: [] },
		{ id: 2, name: 'Chương 2', lessons: [] },
		{ id: 3, name: 'Chương 3', lessons: [] },
		{ id: 4, name: 'Chương 4', lessons: [] },
		{
			id: 5,
			name: 'Chương 5',
			lessons: [
				{ id: 1, name: 'Bài học 1', starred: true },
				{ id: 2, name: 'Bài học 2', starred: false }
			]
		}
	]);

	let expandedChapterId = $state<number | null>(5);
	let activeChapterId = $state(5);
	let activeLessonId = $state(1);
	let sidebarCollapsed = $state(false);

	function toggleChapter(id: number) {
		expandedChapterId = expandedChapterId === id ? null : id;
	}

	function selectLesson(chapterId: number, lessonId: number) {
		activeChapterId = chapterId;
		activeLessonId = lessonId;
	}

	// ---- Breadcrumb: tính động dựa trên chương/bài đang active ----
	let activeChapter = $derived(chapters.find((c) => c.id === activeChapterId));
	let activeLesson = $derived(activeChapter?.lessons.find((l) => l.id === activeLessonId));

	// ---- Điều hướng bài trước / bài sau trong cùng chương ----
	let currentLessonIndex = $derived(
		activeChapter?.lessons.findIndex((l) => l.id === activeLessonId) ?? -1
	);
	let prevLesson = $derived(
		currentLessonIndex > 0 ? activeChapter?.lessons[currentLessonIndex - 1] : null
	);
	let nextLesson = $derived(
		activeChapter && currentLessonIndex < activeChapter.lessons.length - 1
			? activeChapter.lessons[currentLessonIndex + 1]
			: null
	);

	let lessonTitle = $state('Bài học số 2. Mệnh đề quan hệ');

	let lessonSections = $state([
		{
			id: 'muc-tieu',
			label: 'Mục tiêu bài học',
			icon: Target,
			tone: 'indigo',
			items: [
				'Nhận biết được các đại từ quan hệ: who, whom, which, that, whose',
				'Phân biệt mệnh đề quan hệ xác định và không xác định',
				'Áp dụng đúng mệnh đề quan hệ khi viết câu'
			]
		},
		{
			id: 'ly-thuyet',
			label: 'Các phần lý thuyết',
			icon: BookOpen,
			tone: 'teal',
			items: [
				'Khái niệm và chức năng của mệnh đề quan hệ',
				'Cách dùng who / whom / which / that / whose',
				'Mệnh đề quan hệ xác định (defining) và không xác định (non-defining)',
				'Cách rút gọn mệnh đề quan hệ'
			]
		},
		{
			id: 'vi-du',
			label: 'Bài tập ví dụ',
			icon: PenLine,
			tone: 'amber',
			items: [
				'The man who is standing there is my teacher.',
				'The book which I bought yesterday is interesting.',
				'This is the house whose roof is red.'
			]
		},
		{
			id: 'on-luyen',
			label: 'Bài tập ôn luyện',
			icon: Dumbbell,
			tone: 'rose',
			items: [
				'10 câu trắc nghiệm chọn đại từ quan hệ phù hợp',
				'5 câu viết lại câu có dùng mệnh đề quan hệ',
				'1 đoạn văn ngắn yêu cầu xác định mệnh đề quan hệ'
			]
		}
	]);

	const toneClasses: Record<string, string> = {
		indigo: 'bg-indigo-50 text-indigo-600',
		teal: 'bg-teal-50 text-teal-600',
		amber: 'bg-amber-50 text-amber-600',
		rose: 'bg-rose-50 text-rose-600'
	};

	let comments = $state([
		{
			id: 1,
			name: 'Như Quỳnh',
			text: 'Tại sao khi dùng who thay thế cho mệnh đề whom vậy ạ?',
			liked: true
		},
		{
			id: 2,
			name: 'Như Quỳnh',
			text: 'Tại sao khi dùng who thay thế cho mệnh đề whom vậy ạ?',
			liked: false
		}
	]);
	let newComment = $state('');

	function toggleLike(id: number) {
		comments = comments.map((c) => (c.id === id ? { ...c, liked: !c.liked } : c));
	}

	function submitComment() {
		if (!newComment.trim()) return;
		comments = [...comments, { id: Date.now(), name: studentName, text: newComment, liked: false }];
		newComment = '';
	}
</script>

<svelte:head>
	<link rel="preconnect" href="https://fonts.googleapis.com" />
	<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="" />
	<link
		href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700;800&family=Inter:wght@400;500;600&display=swap"
		rel="stylesheet"
	/>
	<title>{lessonTitle}</title>
</svelte:head>

<div class="flex min-h-screen bg-[#F5F6FA]" style="font-family:'Inter',sans-serif;">
	<!-- SIDEBAR -->
	<aside
		class={`flex shrink-0 flex-col overflow-hidden bg-[#0C1550] text-white transition-all duration-300 ${sidebarCollapsed ? 'w-16' : 'w-72'}`}
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

		{#if sidebarCollapsed}
			<div class="flex-1"></div>
		{:else}
			<nav class="flex-1 space-y-1 overflow-y-auto px-3 py-4">
				{#each chapters as chapter}
					<div>
						<button
							onclick={() => toggleChapter(chapter.id)}
							class={`flex w-full items-center gap-3 rounded-full px-4 py-2.5 text-sm transition-all
	                        ${expandedChapterId === chapter.id ? 'bg-white/10 font-semibold text-white' : 'text-indigo-100/55 hover:bg-white/5 hover:text-white'}`}
						>
							<BookOpen class="h-4 w-4 shrink-0 opacity-60" />
							<span class="flex-1 text-left">{chapter.name}</span>
							{#if chapter.lessons.length > 0}
								<ChevronRight
									class={`h-4 w-4 shrink-0 text-indigo-100/40 transition-transform ${expandedChapterId === chapter.id ? 'rotate-90' : ''}`}
								/>
							{/if}
						</button>

						{#if expandedChapterId === chapter.id && chapter.lessons.length > 0}
							<div class="relative ml-6 mt-1 space-y-0.5 pl-4">
								<div class="absolute left-0 top-0 bottom-2 w-px bg-white/10"></div>
								{#each chapter.lessons as lesson}
									<button
										onclick={() => selectLesson(chapter.id, lesson.id)}
										class={`flex w-full items-center gap-2 rounded-full py-2 pl-3 pr-2 text-sm transition-all
				                        ${activeChapterId === chapter.id && activeLessonId === lesson.id ? 'bg-white/10 font-semibold text-white' : 'text-indigo-100/50 hover:bg-white/5 hover:text-white'}`}
									>
										<span class="truncate">{lesson.name}</span>
										{#if lesson.starred}
											<Star class="h-3.5 w-3.5 shrink-0 fill-amber-400 text-amber-400" />
										{/if}
										{#if activeChapterId === chapter.id && activeLessonId === lesson.id}
											<ChevronRight class="ml-auto h-4 w-4 shrink-0 text-indigo-100/50" />
										{/if}
									</button>
								{/each}
							</div>
						{/if}
					</div>
				{/each}
			</nav>
		{/if}

		<div class={`border-t border-white/10 py-4 ${sidebarCollapsed ? 'px-0' : 'px-3'}`}>
			<div
				class={`flex items-center rounded-xl py-2 hover:bg-white/5 ${sidebarCollapsed ? 'justify-center px-0' : 'gap-3 px-2'}`}
			>
				<div
					class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gradient-to-tr from-rose-400 to-orange-300 text-sm font-bold text-white"
				>
					{studentName[0]}
				</div>
				{#if !sidebarCollapsed}
					<div class="min-w-0 flex-1">
						<p class="truncate text-sm font-medium text-white">{studentName}</p>
						<p class="truncate text-xs text-indigo-100/50">Học sinh lớp 12</p>
					</div>
				{/if}
			</div>
		</div>
	</aside>

	<!-- MAIN -->
	<div class="flex flex-1 flex-col">
		<!-- TOP BAR: breadcrumb thay cho search, vì trang này đã ở đúng ngữ cảnh 1 bài học cụ thể -->
		<header
			class="flex items-center justify-between border-b border-slate-200/70 bg-white/80 px-8 py-4 backdrop-blur"
		>
			<nav class="flex items-center gap-2 text-sm text-slate-500">
				<span class="font-medium text-slate-700">{courseName}</span>
				{#if activeChapter}
					<ChevronRight class="h-3.5 w-3.5 text-slate-300" />
					<span class="font-medium text-slate-700">{activeChapter.name}</span>
				{/if}
				{#if activeLesson}
					<ChevronRight class="h-3.5 w-3.5 text-slate-300" />
					<span class="font-semibold text-[#0C1550]">{activeLesson.name}</span>
				{/if}
			</nav>

			<a
				href="/"
				class="flex items-center gap-2 rounded-full bg-[#0C1550] px-4 py-2 text-sm font-medium text-white hover:bg-indigo-900"
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
				{lessonTitle}
			</h1>

			<div class="mb-8 grid grid-cols-1 gap-5 lg:grid-cols-2">
				{#each lessonSections as section}
					<div
						class="rounded-2xl border border-slate-200/70 bg-white p-6 shadow-sm shadow-slate-200/50"
					>
						<div class="mb-4 flex items-center gap-3">
							<div
								class={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${toneClasses[section.tone]}`}
							>
								<section.icon class="h-5 w-5" />
							</div>
							<h2
								class="text-sm font-semibold text-slate-800"
								style="font-family:'Sora',sans-serif;"
							>
								{section.label}
							</h2>
						</div>
						<ul class="space-y-2">
							{#each section.items as item}
								<li class="flex items-start gap-2 text-sm text-slate-600">
									<span class="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-slate-300"></span>
									<span>{item}</span>
								</li>
							{/each}
						</ul>
					</div>
				{/each}
			</div>

			<!-- ĐIỀU HƯỚNG BÀI TRƯỚC / SAU: thay thế logic thực tế của một trang bài học trong khóa học -->
			<div class="mb-8 flex items-center justify-between gap-4">
				{#if prevLesson}
					<button
						onclick={() => activeChapter && selectLesson(activeChapter.id, prevLesson.id)}
						class="flex items-center gap-2 rounded-full border border-slate-200 bg-white px-5 py-2.5 text-sm font-medium text-slate-600 hover:bg-slate-50"
					>
						<ChevronLeft class="h-4 w-4" />
						{prevLesson.name}
					</button>
				{:else}
					<span></span>
				{/if}

				<button
					class="rounded-full bg-[#0C1550] px-6 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-indigo-900"
				>
					Hoàn thành
				</button>

				{#if nextLesson}
					<button
						onclick={() => activeChapter && selectLesson(activeChapter.id, nextLesson.id)}
						class="flex items-center gap-2 rounded-full bg-[#0C1550] px-5 py-2.5 text-sm font-medium text-white hover:bg-indigo-900"
					>
						{nextLesson.name}
						<ChevronRight class="h-4 w-4" />
					</button>
				{:else}
					<span></span>
				{/if}
			</div>

			<!-- BÌNH LUẬN -->
			<div
				class="rounded-2xl border border-slate-200/70 bg-white p-6 shadow-sm shadow-slate-200/50"
			>
				<h2
					class="mb-4 text-sm font-semibold text-slate-800"
					style="font-family:'Sora',sans-serif;"
				>
					Bình luận
				</h2>

				<div class="space-y-4">
					{#each comments as comment}
						<div class="flex items-start justify-between gap-3">
							<div class="flex items-start gap-3">
								<div
									class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-tr from-rose-400 to-orange-300 text-xs font-bold text-white"
								>
									{comment.name[0]}
								</div>
								<div>
									<p class="text-xs font-semibold text-slate-700">{comment.name}</p>
									<p class="text-sm text-slate-600">{comment.text}</p>
								</div>
							</div>
							<button onclick={() => toggleLike(comment.id)} class="shrink-0 pt-1">
								<Heart
									class={`h-4 w-4 ${comment.liked ? 'fill-rose-500 text-rose-500' : 'text-slate-400'}`}
								/>
							</button>
						</div>
					{/each}
				</div>

				<div class="mt-5 flex items-center gap-2 rounded-full bg-slate-100 px-4 py-2.5">
					<input
						type="text"
						bind:value={newComment}
						onkeydown={(e) => e.key === 'Enter' && submitComment()}
						placeholder="Nhập bình luận..."
						class="w-full bg-transparent text-sm text-slate-600 placeholder-slate-400 outline-none"
					/>
					<button onclick={submitComment} class="text-[#0C1550] hover:text-indigo-700">
						<Send class="h-4 w-4" />
					</button>
				</div>
			</div>
		</main>
	</div>

	<!-- TRỢ LÝ AI NỔI -->
	<div class="fixed bottom-8 right-8 z-50 flex flex-col items-end gap-3 group">
		<div
			class="pointer-events-none whitespace-nowrap rounded-2xl border border-indigo-100 bg-white px-5 py-3 text-sm font-bold text-indigo-600 opacity-0 shadow-xl shadow-indigo-100/50 transition-opacity group-hover:opacity-100"
		>
			Chào {studentName}! Mình giúp gì được bạn? 👋
		</div>

		<button
			class="flex h-16 w-16 items-center justify-center rounded-full bg-[#0C1550] text-white shadow-xl shadow-indigo-900/40 transition-all hover:scale-110 hover:bg-indigo-900"
		>
			<Bot class="h-8 w-8 animate-bounce" />
		</button>
	</div>
</div>
