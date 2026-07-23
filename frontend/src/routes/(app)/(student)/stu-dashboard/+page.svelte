<script lang="ts">
	import { goto } from '$app/navigation';
	import { logoutApi } from '$lib/api/calledAPI';
	import type { Course } from '$lib/api/entities.js';
	import Avatar from '$lib/components/Avatar.svelte';
	import Chatbot from '$lib/components/Chatbot.svelte';
	import { auth } from '$lib/stores/auth.svelte';
	import {
		Bell,
		ChevronRight,
		ClipboardList,
		Flame,
		Home,
		LogOut,
		Menu,
		Sparkles,
		User,
		History
	} from 'lucide-svelte';

	let studentName = $derived(auth.user?.full_name);
	let avatarUrl = $derived(auth.user?.avatar);
	let showUserMenu = $state(false);
	let sidebarCollapsed = $state(false);

	let navItems = $state([
		{ id: 'home', label: 'Trang chủ', icon: Home, href: '/stu-dashboard' },
		{ id: 'history', label: 'Lịch sử làm bài với AI', icon: History, href: '/history' }
	]);
	let activeNav = $state('home');
	let { data } = $props();

	let quickStats = $derived.by(() => {
		const stats = data.stats;

		const streakLabel =
			stats.streak === 0
				? 'Bắt đầu chuỗi học mới'
				: stats.studied_today
					? 'Ngày học liên tục'
					: 'Ngày liên tục — học hôm nay!';

		return [
			{
				label: 'Khóa học đang học',
				value: String(stats.ongoing_courses_count),
				icon: ClipboardList,
				tone: 'indigo'
			},
			{
				label: 'Bài tập chờ làm',
				value: String(stats.pending_assignments_count),
				icon: Bell,
				tone: 'amber'
			},
			{
				label: streakLabel,
				value: String(stats.streak),
				icon: Flame,
				tone: 'orange'
			}
		];
	});

	function getTheme(index: number, total: number) {
		const hue = (index * (360 / Math.max(total, 1))) % 360;
		const hue2 = (hue + 40) % 360;

		const ring = `hsl(${hue}, 70%, 50%)`;
		const accent = `hsl(${hue}, 85%, 60%)`;
		const accent2 = `hsl(${hue2}, 85%, 55%)`;

		return { ring, accentFrom: accent, accentTo: accent2 };
	}

	let courses = $derived.by(() => {
		const list: Course[] = data.courses ?? [];
		return list.map((c, i: number) => {
			const theme = getTheme(i, list.length);
			return {
				id: c.id,
				name: c.name,
				tutor: c.tutor_name ?? 'Chưa có gia sư',
				progress: Number(c.progress),
				ring: theme.ring,
				accentFrom: theme.accentFrom,
				accentTo: theme.accentTo
			};
		});
	});

	let isLoggingOut = false;

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

	function navigateTo(item: (typeof navItems)[number]) {
		activeNav = item.id;
		goto(item.href);
	}
</script>

<svelte:head>
	<link rel="preconnect" href="https://fonts.googleapis.com" />
	<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="" />
	<link
		href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700;800&family=Inter:wght@400;500;600&display=swap"
		rel="stylesheet"
	/>
	<title>Trang chủ</title>
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
					<span class="relative shrink-0">
						<item.icon class="h-4.5 w-4.5" />
					</span>
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
		<!-- TOP BAR -->
		<header
			class="flex items-center justify-end border-b border-slate-200/70 bg-white/80 px-8 py-4 backdrop-blur"
		>
			<div class="flex items-center gap-4">
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
			</div>
		</header>

		<main class="flex-1 overflow-y-auto px-8 py-8">
			<!-- GREETING -->
			<div class="mb-8 flex flex-wrap items-end justify-between gap-4">
				<div>
					<h1
						class="text-2xl font-bold tracking-tight text-slate-900"
						style="font-family:'Sora',sans-serif;"
					>
						Chào mừng quay trở lại, {studentName} 👋
					</h1>
					<p class="mt-1 text-sm text-slate-500">
						Hôm nay là một ngày tốt để học thêm điều gì đó mới.
					</p>
				</div>
			</div>

			<!-- QUICK STATS -->
			<div class="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
				{#each quickStats as stat (stat.label)}
					<div
						class="flex items-center gap-4 rounded-2xl border border-slate-200/70 bg-white p-5 shadow-sm shadow-slate-200/50"
					>
						<div
							class={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl
								${stat.tone === 'indigo' ? 'bg-indigo-50 text-indigo-600' : ''}
								${stat.tone === 'amber' ? 'bg-amber-50 text-amber-600' : ''}
								${stat.tone === 'orange' ? 'bg-orange-50 text-orange-600' : ''}`}
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
					Khóa học của bạn
				</h2>
			</div>

			{#if courses.length === 0}
				<div class="text-center py-20 text-slate-400">
					<p>Bạn chưa có khóa học nào. Hãy bắt đầu hành trình ngay!</p>
				</div>
			{:else}
				<div class="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3">
					{#each courses as course (course.id)}
						<div
							class="group relative flex h-full flex-col overflow-hidden rounded-2xl border border-slate-200/70 bg-white p-6 shadow-sm shadow-slate-200/50 transition-all hover:-translate-y-0.5 hover:shadow-md"
						>
							<div
								class="absolute -right-6 -top-6 h-24 w-24 rounded-full opacity-10"
								style={`background: linear-gradient(to bottom right, ${course.accentFrom}, ${course.accentTo})`}
							></div>

							<div class="mb-5 flex flex-1 items-start justify-between">
								<div>
									<h3
										class="mt-1 text-lg font-bold text-slate-900"
										style="font-family:'Sora',sans-serif;"
									>
										{course.name}
									</h3>
									<p class="mt-1 text-xs text-slate-500">
										Gia sư: <span class="font-medium text-slate-700">{course.tutor}</span>
									</p>
								</div>

								<div
									class="relative flex h-14 w-14 shrink-0 items-center justify-center rounded-full"
									style={`background: conic-gradient(${course.ring} ${course.progress * 3.6}deg, #EEF0F5 0deg)`}
								>
									<div class="flex h-11 w-11 items-center justify-center rounded-full bg-white">
										<span class="text-xs font-bold text-slate-800">{course.progress}%</span>
									</div>
								</div>
							</div>

							<a
								href={`/course/${course.id}`}
								class={`mt-auto flex w-full items-center justify-center gap-2 rounded-xl py-2.5 text-sm font-semibold text-white transition-colors ${
									course.progress >= 100
										? 'bg-emerald-600 group-hover:bg-emerald-700'
										: 'bg-slate-900 group-hover:bg-indigo-600'
								}`}
							>
								{course.progress >= 100 ? 'Xem khóa học' : 'Học tiếp'}
								<ChevronRight class="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
							</a>
						</div>
					{/each}
				</div>
			{/if}
		</main>
	</div>

	<Chatbot userName={auth.user?.full_name} />
</div>
