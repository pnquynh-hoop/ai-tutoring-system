<script lang="ts">
	import { goto } from '$app/navigation';
	import { logoutApi } from '$lib/api/calledAPI';
	import { auth } from '$lib/stores/auth.svelte';
	import Avatar from '$lib/components/Avatar.svelte';
	import {
		Home,
		MessageCircle,
		History,
		LogOut,
		Menu,
		Sparkles,
		User,
		ChevronRight,
		Flag,
		CheckCircle2,
		Clock
	} from 'lucide-svelte';

	// ============================================================
	// Lịch sử làm bài với AI
	// Map đúng model thật đang có trong DB:
	//   Tab 1 "Bài đã làm"      -> Submission -> StudentAnswer -> Question/Answer
	//   Tab 2 "Câu hỏi đã báo lỗi" -> Report (question, note, status, reported_at)
	// Không có model AIConversation/AIMessage thật nên KHÔNG hiển thị "chat log",
	// chỉ hiển thị những gì DB thật sự lưu được.
	// ============================================================

	type QuestionType = 'MULTIPLE_CHOICE' | 'FILL_IN_BLANK' | 'ESSAY';
	type ReportStatus = 'REPORTED' | 'REVIEWING' | 'SOLVED';

	interface AnswerOption {
		id: number;
		content: string;
		is_correct: boolean;
	}

	interface QuestionItem {
		id: number;
		content: string;
		question_type: QuestionType;
		explanation: string;
	}

	interface StudentAnswerItem {
		id: number;
		answer_text: string | null;
		tutor_comment: string | null;
		point: number;
		question: QuestionItem;
		answer: AnswerOption | null;
	}

	interface SubmissionItem {
		id: number;
		assignment: {
			id: number;
			title: string;
			chapter_title: string;
			course_name: string;
		};
		score: number;
		submitted_at: string;
		student_answers: StudentAnswerItem[];
	}

	interface ReportItem {
		id: number;
		question: { id: number; content: string };
		note: string;
		status: ReportStatus;
		reported_at: string;
	}

	// --- User thật (đồng bộ với các trang khác) ---
	let studentName = $derived(auth.user?.full_name);
	let avatarUrl = $derived(auth.user?.avatar);
	let showUserMenu = $state(false);
	let sidebarCollapsed = $state(false);
	let isLoggingOut = false;

	let navItems = $state([
		{ id: 'home', label: 'Trang chủ', icon: Home, href: '/stu-dashboard' },
		{ id: 'chatbot', label: 'Trợ lý ảo AI', icon: MessageCircle, href: '/chabot' },
		{ id: 'history', label: 'Lịch sử làm bài với AI', icon: History, href: '/history' }
	]);
	let activeNav = $state('history');

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

	// --- MOCK: Submission + StudentAnswer (thay bằng fetch API thật sau) ---
	const submissions: SubmissionItem[] = [
		{
			id: 1,
			assignment: {
				id: 101,
				title: 'Bài tập: Phương trình mũ - logarit',
				chapter_title: 'Chương 1: Phương trình - Bất phương trình',
				course_name: 'Luyện Thi THPT QG Toán Học 2026'
			},
			score: 8.5,
			submitted_at: '2026-07-20T14:32:00',
			student_answers: [
				{
					id: 1001,
					answer_text: null,
					tutor_comment: null,
					point: 1,
					question: {
						id: 1,
						content: 'Nghiệm của phương trình 2^x = 8 là:',
						question_type: 'MULTIPLE_CHOICE',
						explanation: 'Vì 8 = 2^3 nên x = 3.'
					},
					answer: { id: 1, content: 'A. x = 3', is_correct: true }
				},
				{
					id: 1002,
					answer_text: null,
					tutor_comment: 'Chọn nhầm cơ số, xem lại quy tắc đổi cơ số.',
					point: 0,
					question: {
						id: 2,
						content: 'log2(16) bằng bao nhiêu?',
						question_type: 'MULTIPLE_CHOICE',
						explanation: 'log2(16) = 4 vì 2^4 = 16.'
					},
					answer: { id: 2, content: 'B. 3', is_correct: false }
				}
			]
		},
		{
			id: 2,
			assignment: {
				id: 102,
				title: 'Bài tập: Task 2 - Cấu trúc bài luận',
				chapter_title: 'Chương 1: Writing',
				course_name: 'IELTS Foundation'
			},
			score: 6,
			submitted_at: '2026-07-18T09:10:00',
			student_answers: [
				{
					id: 2001,
					answer_text:
						'In my opinion, technology has changed the way students learn in both positive and negative ways.',
					tutor_comment: 'Câu mở bài ổn nhưng thiếu luận điểm rõ ràng.',
					point: 1.5,
					question: {
						id: 3,
						content: 'Viết câu mở bài (introduction) cho đề bài về ảnh hưởng của công nghệ.',
						question_type: 'ESSAY',
						explanation: 'Câu mở bài cần nêu rõ quan điểm và định hướng bài luận.'
					},
					answer: null
				}
			]
		}
	];

	// --- MOCK: Report của chính học sinh này ---
	const myReports: ReportItem[] = [
		{
			id: 1,
			question: { id: 2, content: 'log2(16) bằng bao nhiêu?' },
			note: 'Em thấy đáp án AI chấm đúng là B nhưng hệ thống báo sai.',
			status: 'REVIEWING',
			reported_at: '2026-07-20T15:00:00'
		},
		{
			id: 2,
			question: { id: 5, content: 'Mệnh đề quan hệ "who" dùng khi nào?' },
			note: 'Giải thích của AI không rõ ràng, dễ hiểu nhầm.',
			status: 'SOLVED',
			reported_at: '2026-07-10T08:20:00'
		}
	];

	type Tab = 'submissions' | 'reports';
	let activeTab = $state<Tab>('submissions');
	let expandedSubmissionId = $state<number | null>(null);

	function toggleSubmission(id: number) {
		expandedSubmissionId = expandedSubmissionId === id ? null : id;
	}

	function formatDate(iso: string): string {
		return new Date(iso).toLocaleString('vi-VN', {
			day: '2-digit',
			month: '2-digit',
			year: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	function scoreTone(score: number): string {
		if (score >= 8) return 'text-emerald-600 bg-emerald-50';
		if (score >= 5) return 'text-amber-600 bg-amber-50';
		return 'text-rose-600 bg-rose-50';
	}

	const questionTypeLabel: Record<QuestionType, string> = {
		MULTIPLE_CHOICE: 'Trắc nghiệm',
		FILL_IN_BLANK: 'Điền khuyết',
		ESSAY: 'Tự luận'
	};

	const reportStatusMeta: Record<ReportStatus, { label: string; tone: string; icon: typeof Clock }> = {
		REPORTED: { label: 'Đã báo cáo', tone: 'text-amber-600 bg-amber-50', icon: Flag },
		REVIEWING: { label: 'Đang xem xét', tone: 'text-indigo-600 bg-indigo-50', icon: Clock },
		SOLVED: { label: 'Đã xử lý', tone: 'text-emerald-600 bg-emerald-50', icon: CheckCircle2 }
	};
</script>

<svelte:head>
	<link rel="preconnect" href="https://fonts.googleapis.com" />
	<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="" />
	<link
		href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700;800&family=Inter:wght@400;500;600&family=Sora:wght@600;700;800&display=swap"
		rel="stylesheet"
	/>
	<title>Lịch sử làm bài với AI</title>
</svelte:head>

<div class="flex min-h-screen bg-[#F5F6FA]" style="font-family:'Inter',sans-serif;">
	<!-- SIDEBAR -->
	<aside
		class={`relative flex flex-col bg-[#0C1550] text-white transition-all duration-300 ${sidebarCollapsed ? 'w-20' : 'w-64'}`}
	>
		<div class="flex items-center gap-3 px-5 py-6">
			<div
				class="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-linear-to-tr from-indigo-500 to-violet-500 shadow-lg shadow-indigo-900/40"
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
								: 'text-indigo-100/60 hover:bg-white/5 hover:text-white'
						}`}
				>
					<item.icon class="h-4.5 w-4.5 shrink-0" />
					{#if !sidebarCollapsed}
						<span class="truncate">{item.label}</span>
					{/if}
					{#if activeNav === item.id && !sidebarCollapsed}
						<span class="ml-auto h-1.5 w-1.5 rounded-full bg-indigo-400"></span>
					{/if}
				</button>
			{/each}
		</nav>

		<button
			onclick={() => (sidebarCollapsed = !sidebarCollapsed)}
			class="mx-3 mb-2 flex items-center gap-2 rounded-xl px-3 py-2 text-xs text-indigo-100/40 hover:bg-white/5 hover:text-white"
		>
			<Menu class="h-4 w-4" />
			{#if !sidebarCollapsed}Thu gọn{/if}
		</button>
	</aside>

	<!-- MAIN -->
	<div class="flex flex-1 flex-col">
		<header
			class="flex items-center justify-end border-b border-slate-200/70 bg-white/80 px-8 py-4 backdrop-blur"
		>
			<div class="relative">
				<button
					onclick={() => (showUserMenu = !showUserMenu)}
					class="flex items-center gap-2.5 rounded-full py-1 pl-3 pr-1 hover:bg-slate-100"
					aria-label="Mở menu tài khoản"
				>
					<span class="text-sm font-medium text-slate-700">{studentName}</span>
					<Avatar src={avatarUrl} name={studentName ?? ''} size="lg" />
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
							onclick={() => goto('/profile')}
							class="flex w-full items-center gap-3 px-4 py-2.5 text-sm text-slate-600 hover:bg-slate-50"
						>
							<User class="h-4 w-4" />
							Xem hồ sơ
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
		</header>

		<main class="flex-1 overflow-y-auto px-8 py-8">
			<div class="mb-6">
				<h1
					class="text-2xl font-bold tracking-tight text-slate-900"
					style="font-family:'Sora',sans-serif;"
				>
					Lịch sử làm bài với AI
				</h1>
				<p class="mt-1 text-sm text-slate-500">
					Xem lại các bài đã nộp và các câu hỏi bạn đã báo lỗi cho AI.
				</p>
			</div>

			<!-- TABS -->
			<div class="mb-6 inline-flex items-center rounded-full bg-slate-100 p-1 text-sm font-semibold">
				<button
					class={`rounded-full px-4 py-1.5 transition ${activeTab === 'submissions' ? 'bg-white text-indigo-600 shadow' : 'text-slate-500'}`}
					onclick={() => (activeTab = 'submissions')}
				>
					Bài đã làm
				</button>
				<button
					class={`rounded-full px-4 py-1.5 transition ${activeTab === 'reports' ? 'bg-white text-indigo-600 shadow' : 'text-slate-500'}`}
					onclick={() => (activeTab = 'reports')}
				>
					Câu hỏi đã báo lỗi
				</button>
			</div>

			{#if activeTab === 'submissions'}
				<div class="space-y-4">
					{#each submissions as sub (sub.id)}
						<div
							class="overflow-hidden rounded-2xl border border-slate-200/70 bg-white shadow-sm shadow-slate-200/50"
						>
							<button
								class="flex w-full items-center justify-between gap-4 px-6 py-4 text-left"
								onclick={() => toggleSubmission(sub.id)}
							>
								<div class="min-w-0">
									<p class="text-xs text-slate-400">
										{sub.assignment.course_name} • {sub.assignment.chapter_title}
									</p>
									<p
										class="truncate text-sm font-semibold text-slate-900"
										style="font-family:'Sora',sans-serif;"
									>
										{sub.assignment.title}
									</p>
									<p class="mt-1 text-xs text-slate-400">Nộp lúc {formatDate(sub.submitted_at)}</p>
								</div>
								<div class="flex shrink-0 items-center gap-3">
									<span class={`rounded-full px-3 py-1 text-sm font-bold ${scoreTone(sub.score)}`}>
										{sub.score}/10
									</span>
									<ChevronRight
										class={`h-4 w-4 text-slate-300 transition-transform ${expandedSubmissionId === sub.id ? 'rotate-90' : ''}`}
									/>
								</div>
							</button>

							{#if expandedSubmissionId === sub.id}
								<div class="space-y-3 border-t border-slate-100 bg-slate-50/60 px-6 py-4">
									{#each sub.student_answers as sa (sa.id)}
										<div class="rounded-xl border border-slate-200/70 bg-white p-4">
											<div class="flex items-start justify-between gap-3">
												<span
													class="rounded-full bg-indigo-50 px-2.5 py-0.5 text-[11px] font-semibold text-indigo-600"
												>
													{questionTypeLabel[sa.question.question_type]}
												</span>
												<span class="text-xs font-semibold text-slate-500">
													{sa.point} điểm
												</span>
											</div>
											<p class="mt-2 text-sm font-medium text-slate-800">{sa.question.content}</p>

											{#if sa.answer}
												<p
													class={`mt-2 rounded-lg border px-3 py-1.5 text-[13px] ${
														sa.answer.is_correct
															? 'border-emerald-200 bg-emerald-50 text-emerald-700'
															: 'border-rose-200 bg-rose-50 text-rose-700'
													}`}
												>
													Bạn chọn: {sa.answer.content}
													{sa.answer.is_correct ? ' ✓' : ' ✗'}
												</p>
											{:else if sa.answer_text}
												<p class="mt-2 rounded-lg border border-slate-100 bg-slate-50 px-3 py-2 text-[13px] text-slate-600">
													{sa.answer_text}
												</p>
											{/if}

											{#if sa.tutor_comment}
												<p class="mt-2 text-[12.5px] text-slate-500">
													<span class="font-medium text-slate-600">Nhận xét gia sư:</span>
													{sa.tutor_comment}
												</p>
											{/if}
										</div>
									{/each}
								</div>
							{/if}
						</div>
					{/each}

					{#if submissions.length === 0}
						<div class="rounded-2xl border border-dashed border-slate-200 bg-white py-16 text-center text-sm text-slate-400">
							Bạn chưa nộp bài tập nào.
						</div>
					{/if}
				</div>
			{:else}
				<div class="space-y-3">
					{#each myReports as r (r.id)}
						{@const meta = reportStatusMeta[r.status]}
						<div class="rounded-2xl border border-slate-200/70 bg-white p-5 shadow-sm shadow-slate-200/50">
							<div class="flex items-start justify-between gap-3">
								<p class="text-sm font-medium text-slate-800">{r.question.content}</p>
								<span class={`flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold ${meta.tone}`}>
									<meta.icon class="h-3 w-3" />
									{meta.label}
								</span>
							</div>
							<p class="mt-2 text-[13px] text-slate-500">{r.note}</p>
							<p class="mt-2 text-[11px] text-slate-400">Báo lúc {formatDate(r.reported_at)}</p>
						</div>
					{/each}

					{#if myReports.length === 0}
						<div class="rounded-2xl border border-dashed border-slate-200 bg-white py-16 text-center text-sm text-slate-400">
							Bạn chưa báo lỗi câu hỏi nào.
						</div>
					{/if}
				</div>
			{/if}
		</main>
	</div>
</div>