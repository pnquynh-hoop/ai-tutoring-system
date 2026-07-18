<script lang="ts">
	import { goto } from '$app/navigation';
	import { logoutApi } from '$lib/api/auth';
	import {
		Home,
		MessageCircle,
		History,
		Search,
		Bell,
		Sparkles,
		ChevronRight,
		Flame,
		ClipboardList,
		Award,
		Bot,
		LogOut,
		Menu,
		User,
		KeyRound
	} from 'lucide-svelte';

	let studentName = $state('An');
	let currentStreak = $state(5);
	let showUserMenu = $state(false);
    let sidebarCollapsed = $state(false);

	let navItems = $state([
		{ id: 'home', label: 'Trang chủ', icon: Home },
		{ id: 'assistant', label: 'Trợ lý ảo AI', icon: MessageCircle, badge: true },
		{ id: 'history', label: 'Lịch sử làm bài', icon: History }
	]);
	let activeNav = $state('home');

	let quickStats = $state([
		{ label: 'Khóa học đang học', value: '4', icon: ClipboardList, tone: 'indigo' },
		{ label: 'Bài tập chờ làm', value: '3', icon: Bell, tone: 'amber' },
		{ label: 'Điểm trung bình', value: '8.6', icon: Award, tone: 'teal' }
	]);

	// let courses = $state([]);
	let courses = $state([
		{
			id: 1,
			name: 'Tiếng Anh 12',
			tutor: 'Nguyễn Văn Minh',
			progress: 20,
			tag: 'Từ vựng & Ngữ pháp',
			accent: 'from-indigo-500 to-violet-500',
			ring: '#4F46E5'
		},
		{
			id: 2,
			name: 'Toán 12',
			tutor: 'Trần Thị Hoa',
			progress: 65,
			tag: 'Giải tích - Đạo hàm',
			accent: 'from-teal-500 to-cyan-500',
			ring: '#0D9488'
		},
		{
			id: 3,
			name: 'Vật Lý 11',
			tutor: 'Lê Quốc Bảo',
			progress: 42,
			tag: 'Điện học',
			accent: 'from-amber-500 to-orange-500',
			ring: '#D97706'
		},
		{
			id: 4,
			name: 'Hóa học 12',
			tutor: 'Phạm Thu Trang',
			progress: 88,
			tag: 'Hóa hữu cơ',
			accent: 'from-rose-500 to-pink-500',
			ring: '#E11D48'
		}
	]);

    let isLoggingOut = false;

    async function handleLogout() {
        if (isLoggingOut) return;

        isLoggingOut = true;

        try {
            await logoutApi();
        } catch (err: any) {
            console.error(err);
        } finally {
            isLoggingOut = false;
            await goto('/login');
        }
    }

	
</script>

<svelte:head>
	<link rel="preconnect" href="https://fonts.googleapis.com" />
	<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="" />
	<link
		href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700;800&family=Inter:wght@400;500;600&display=swap"
		rel="stylesheet"
	/>
	<script src="https://unpkg.com/@lottiefiles/lottie-player@latest/dist/lottie-player.js"></script>
	<title>Trang chủ</title>
</svelte:head>

<div class="flex min-h-screen bg-[#F5F6FA]" style="font-family:'Inter',sans-serif;">
	<!-- SIDEBAR -->
	<aside
		class={`relative flex flex-col bg-[#0C1550] text-white transition-all duration-300 ${sidebarCollapsed ? 'w-20' : 'w-64'}`}
	>
		<div class="flex items-center gap-3 px-5 py-6">
			<div
				class="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-tr from-indigo-500 to-violet-500 shadow-lg shadow-indigo-900/40"
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
			{#each navItems as item}
				<button
					onclick={() => (activeNav = item.id)}
					class={`group flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all
						${
							activeNav === item.id
								? 'bg-white/10 text-white shadow-inner'
								: 'text-indigo-100/60 hover:bg-white/5 hover:text-white'
						}`}
				>
					<span class="relative shrink-0">
						<item.icon class="h-[18px] w-[18px]" />
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
				<button class="relative rounded-full p-2 text-slate-500 hover:bg-slate-100">
					<Bell class="h-5 w-5" />
					<span class="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-rose-500"></span>
				</button>
				<div class="relative">
					<button
						onclick={() => (showUserMenu = !showUserMenu)}
						class="h-9 w-9 rounded-full bg-gradient-to-tr from-rose-400 to-orange-300"
						aria-label="Mở menu tài khoản"
					></button>

					{#if showUserMenu}
						<!-- Lớp nền trong suốt để bấm ra ngoài là đóng menu -->
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
				<div
					class="flex items-center gap-2 rounded-full bg-gradient-to-r from-amber-50 to-orange-50 px-4 py-2 text-sm font-semibold text-orange-600 ring-1 ring-orange-200/60"
				>
					<Flame class="h-4 w-4" />
					{currentStreak} ngày học liên tiếp
				</div>
			</div>

			<!-- QUICK STATS -->
			<div class="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
				{#each quickStats as stat}
					<div
						class="flex items-center gap-4 rounded-2xl border border-slate-200/70 bg-white p-5 shadow-sm shadow-slate-200/50"
					>
						<div
							class={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl
								${stat.tone === 'indigo' ? 'bg-indigo-50 text-indigo-600' : ''}
								${stat.tone === 'amber' ? 'bg-amber-50 text-amber-600' : ''}
								${stat.tone === 'teal' ? 'bg-teal-50 text-teal-600' : ''}`}
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
				<button class="flex items-center gap-1 text-sm font-medium text-indigo-600 hover:underline">
					Xem tất cả <ChevronRight class="h-4 w-4" />
				</button>
			</div>

			{#if courses.length === 0}
				<div class="text-center py-20 text-slate-400">
					<p>Bạn chưa có khóa học nào. Hãy bắt đầu hành trình ngay!</p>
				</div>
			{:else}
				<div class="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3">
					{#each courses as course}
						<div
							class="group relative overflow-hidden rounded-2xl border border-slate-200/70 bg-white p-6 shadow-sm shadow-slate-200/50 transition-all hover:-translate-y-0.5 hover:shadow-md"
						>
							<div
								class={`absolute -right-6 -top-6 h-24 w-24 rounded-full bg-gradient-to-br opacity-10 ${course.accent}`}
							></div>

							<div class="mb-5 flex items-start justify-between">
								<div>
									<p class="text-xs font-medium uppercase tracking-wide text-slate-400">
										{course.tag}
									</p>
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
								href="/course"
								class="flex w-full items-center justify-center gap-2 rounded-xl bg-slate-900 py-2.5 text-sm font-semibold text-white transition-colors group-hover:bg-indigo-600"
							>
								Học tiếp
								<ChevronRight class="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
							</a>
						</div>
					{/each}
				</div>
			{/if}
		</main>
	</div>

	<div class="fixed bottom-8 right-8 z-50 flex flex-col items-end gap-3 group">
		<div
			class="bg-white px-5 py-3 rounded-2xl shadow-xl text-sm font-bold text-indigo-600 opacity-0 group-hover:opacity-100 transition-opacity border border-indigo-100 pointer-events-none whitespace-nowrap shadow-indigo-100/50"
		>
			Chào {studentName}! Mình giúp gì được bạn? 👋
		</div>

		<button
			class="flex h-16 w-16 items-center justify-center rounded-full bg-blue-700 text-white shadow-xl shadow-blue-900/40 transition-all hover:scale-110 hover:bg-blue-800"
		>
			<Bot class="h-8 w-8 animate-bounce" />
		</button>
	</div>
</div>
