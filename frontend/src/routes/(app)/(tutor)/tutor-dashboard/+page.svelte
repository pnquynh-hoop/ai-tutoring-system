<script lang="ts">
	// Route suggestion: /tutor-dashboard
	import { goto } from '$app/navigation';
	import { logoutApi } from '$lib/api/calledAPI';
	import Avatar from '$lib/components/Avatar.svelte';
	import { auth } from '$lib/stores/auth.svelte';
	import {
		LogOut,
		User,
		Users,
		ClipboardCheck,
		BookOpen,
		ChevronRight,
		BarChart3
	} from 'lucide-svelte';
	import type { PageProps } from './$types';

	// ============================================================
	// Trang chủ Gia sư: danh sách khóa học đang dạy + số liệu tổng quan.
	// Không cần sidebar điều hướng vì đây là trang duy nhất ở cấp cao nhất;
	// mọi thao tác khác (quản lý cây, thống kê, chấm bài) đi vào từ mỗi khóa học.
	// Dữ liệu lấy từ GET /courses/ và GET /courses/statistic/ (backend tự đổi
	// bộ field theo vai trò gia sư).
	// ============================================================

	let { data }: PageProps = $props();
	let courses = $derived(data.courses);
	let summary = $derived(data.stats);

	let tutorName = $derived(auth.user?.full_name);
	let avatarUrl = $derived(auth.user?.avatar);
	let showUserMenu = $state(false);
	let isLoggingOut = false;

	let quickStats = $derived([
		{
			label: 'Khóa học đang dạy',
			value: String(summary.teaching_course_count),
			icon: BookOpen,
			tone: 'navy'
		},
		{
			label: 'Học sinh đang theo học',
			value: String(summary.students_count),
			icon: Users,
			tone: 'slate'
		},
		{
			label: 'Bài chờ chấm',
			value: String(summary.pending_submission_count),
			icon: ClipboardCheck,
			tone: 'amber'
		}
	]);

	async function handleLogout() {
		if (isLoggingOut) return;
		isLoggingOut = true;
		try {
			await logoutApi();
		} catch (err: unknown) {
			console.error(err);
		} finally {
			isLoggingOut = false;
			await goto('/login');
		}
	}

	function goManage(courseId: number) {
		goto(`/course-mgt/${courseId}`);
	}

	function goStats(courseId: number) {
		goto(`/course-mgt/${courseId}/stats`);
	}
</script>

<svelte:head>
	<link rel="preconnect" href="https://fonts.googleapis.com" />
	<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="" />
	<link
		href="https://fonts.googleapis.com/css2?family=Sora:wght@600;700;800&family=Inter:wght@400;500;600&display=swap"
		rel="stylesheet"
	/>
	<title>Trang chủ gia sư</title>
</svelte:head>

<div class="min-h-screen bg-[#F4F5F8]" style="font-family:'Inter',sans-serif;">
	<!-- TOP BAR (không có sidebar trái vì đây là trang duy nhất) -->
	<header
		class="flex items-center justify-between border-b border-slate-200/70 bg-white/80 px-8 py-4 backdrop-blur"
	>
		<div class="flex items-center gap-2.5">
			<div class="flex h-9 w-9 items-center justify-center rounded-xl bg-[#0C1550]">
				<BookOpen class="h-4.5 w-4.5 text-white" />
			</div>
			<span
				class="font-semibold tracking-tight text-slate-800"
				style="font-family:'Sora',sans-serif;"
			>
				Gia sư AI CaSiu
			</span>
		</div>

		<div class="relative">
			<button
				onclick={() => (showUserMenu = !showUserMenu)}
				class="flex items-center gap-2.5 rounded-full py-1 pl-3 pr-1 hover:bg-slate-100"
				aria-label="Mở menu tài khoản"
			>
				<span class="text-sm font-medium text-slate-700">{tutorName}</span>
				<Avatar src={avatarUrl} name={tutorName ?? ''} size="lg" />
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
						onclick={() => goto('/profile')}
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

	<main class="px-8 py-8">
		<div class="mb-8">
			<h1
				class="text-2xl font-bold tracking-tight text-slate-900"
				style="font-family:'Sora',sans-serif;"
			>
				Chào thầy/cô, {tutorName}
			</h1>
			<p class="mt-1 text-sm text-slate-500">Tổng quan các khóa học thầy/cô đang phụ trách.</p>
		</div>

		<!-- QUICK STATS -->
		<div class="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
			{#each quickStats as stat (stat.label)}
				<div
					class="flex items-center gap-4 rounded-2xl border border-slate-200/70 bg-white p-5 shadow-sm shadow-slate-200/50"
				>
					<div
						class={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl
							${stat.tone === 'navy' ? 'bg-[#0C1550]/5 text-[#0C1550]' : ''}
							${stat.tone === 'slate' ? 'bg-slate-100 text-slate-600' : ''}
							${stat.tone === 'amber' ? 'bg-amber-50 text-amber-600' : ''}`}
					>
						<stat.icon class="h-5 w-5" />
					</div>
					<div>
						<p class="text-lg font-bold text-slate-900">{stat.value}</p>
						<p class="text-xs text-slate-500">{stat.label}</p>
					</div>
				</div>
			{/each}
		</div>

		<!-- COURSES -->
		<div class="mb-4 flex items-center justify-between">
			<h2 class="text-base font-semibold text-slate-800" style="font-family:'Sora',sans-serif;">
				Khóa học đang giảng dạy
			</h2>
		</div>

		{#if courses.length === 0}
			<div class="py-20 text-center text-slate-400">
				<p>Thầy/cô chưa được phân công khóa học nào.</p>
			</div>
		{:else}
			<div class="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3">
				{#each courses as course (course.id)}
					<div
						class="flex h-full flex-col rounded-2xl border border-slate-200/70 bg-white p-6 shadow-sm shadow-slate-200/50 transition-all hover:-translate-y-0.5 hover:shadow-md"
					>
						<div class="mb-4 flex-1">
							<h3 class="text-lg font-bold text-slate-900" style="font-family:'Sora',sans-serif;">
								{course.name}
							</h3>
							<div
								class="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-slate-500"
							>
								<span class="flex items-center gap-1.5">
									<Users class="h-3.5 w-3.5" />
									{course.students_count} học sinh
								</span>
								<span class="flex items-center gap-1.5">
									<BookOpen class="h-3.5 w-3.5" />
									{course.chapters_count} chương · {course.lessons_count} bài
								</span>
							</div>
							{#if course.pending_submission_count > 0}
								<div
									class="mt-3 inline-flex items-center gap-1.5 rounded-full bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-700"
								>
									<ClipboardCheck class="h-3 w-3" />
									{course.pending_submission_count} bài chờ chấm
								</div>
							{/if}
						</div>

						<div class="mt-auto grid grid-cols-2 gap-2">
							<button
								onclick={() => goStats(course.id)}
								class="flex items-center justify-center gap-1.5 rounded-xl border border-slate-200 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50"
							>
								<BarChart3 class="h-4 w-4" />
								Thống kê
							</button>
							<button
								onclick={() => goManage(course.id)}
								class="flex items-center justify-center gap-2 rounded-xl bg-[#0C1550] py-2.5 text-sm font-semibold text-white hover:bg-indigo-700"
							>
								Quản lý
								<ChevronRight class="h-4 w-4" />
							</button>
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</main>
</div>
