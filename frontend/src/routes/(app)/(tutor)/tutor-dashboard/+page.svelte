<script lang="ts">
	import { goto } from '$app/navigation';
	import { logoutApi } from '$lib/api/calledAPI';
	import Avatar from '$lib/components/Avatar.svelte';
	import { auth } from '$lib/stores/auth.svelte';
	import { LogOut, Users, ClipboardCheck, BookOpen, ChevronRight, BarChart3 } from 'lucide-svelte';
	import type { PageProps } from './$types';

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
			value: String(summary.total_students_count),
			icon: Users,
			tone: 'slate'
		},
		{
			label: 'Bài chờ chấm',
			value: String(summary.total_pending_submission_count),
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
	<title>Trang chủ gia sư</title>
</svelte:head>

<div class="min-h-screen bg-slate-50">
	<header
		class="flex items-center justify-between border-b border-slate-200/70 bg-white/80 px-8 py-4 backdrop-blur"
	>
		<div class="flex items-center gap-2.5">
			<div class="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-600">
				<BookOpen class="h-4.5 w-4.5 text-white" />
			</div>
			<span class="font-semibold tracking-tight text-slate-800 font-heading">
				Trung tâm gia sư Novi
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
			<h1 class="text-2xl font-bold tracking-tight text-slate-900 font-heading">
				Chào thầy/cô, {tutorName}
			</h1>
			<p class="mt-1 text-sm text-slate-500">Tổng quan các khóa học thầy/cô đang phụ trách.</p>
		</div>

		<div class="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
			{#each quickStats as stat (stat.label)}
				<div
					class="flex items-center gap-4 rounded-2xl border border-slate-200/70 bg-white p-5 shadow-sm shadow-slate-200/50"
				>
					<div
						class={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl
							${stat.tone === 'navy' ? 'bg-brand-50 text-brand-600' : ''}
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

		<div class="mb-4 flex items-center justify-between">
			<h2 class="text-base font-semibold text-slate-800 font-heading">Khóa học đang giảng dạy</h2>
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
							<h3 class="text-lg font-bold text-slate-900 font-heading">
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
								class="flex items-center justify-center gap-2 rounded-xl bg-brand-600 py-2.5 text-sm font-semibold text-white hover:bg-brand-700"
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
