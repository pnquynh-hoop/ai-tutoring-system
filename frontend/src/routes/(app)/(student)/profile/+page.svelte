<script lang="ts">
	import { goto } from '$app/navigation';
	import { logoutApi } from '$lib/api/calledAPI';
	import { auth } from '$lib/stores/auth.svelte';
	import { showToast } from '$lib/stores/toast.svelte';
	import Avatar from '$lib/components/Avatar.svelte';
	import {
		Home,
		MessageCircle,
		History,
		LogOut,
		Menu,
		Sparkles,
		User,
		ShieldCheck,
		KeyRound,
		GraduationCap
	} from 'lucide-svelte';

	// ============================================================
	// Hồ sơ cá nhân — gộp "cập nhật thông tin" + "đổi mật khẩu" 1 trang.
	// Field lấy đúng từ model:
	//   User: last_name, first_name, email, phone, avatar
	//   StudentProfile: grade_level, learning_goals, academic_level
	//   TutorProfile: bio, qualification, experience_years, is_verified (chỉ xem)
	// Đổi mật khẩu không có model riêng -> chỉ là 1 form hành động (current/new/confirm).
	// ============================================================

	type AcademicLevel = 'POOR' | 'AVERAGE' | 'GOOD' | 'EXCELLENT';

	// TODO: thay bằng auth.user?.is_student / auth.user?.is_tutor thật
	let role = $state<'student' | 'tutor'>('student');

	let navItems = $state([
		{ id: 'home', label: 'Trang chủ', icon: Home, href: '/stu-dashboard' },
		{ id: 'chatbot', label: 'Trợ lý ảo AI', icon: MessageCircle, href: '/chabot' },
		{ id: 'history', label: 'Lịch sử làm bài với AI', icon: History, href: '/history' }
	]);
	let activeNav = $state('profile');
	let sidebarCollapsed = $state(false);
	let showUserMenu = $state(false);
	let isLoggingOut = false;

	let displayName = $derived(auth.user?.full_name);
	let avatarUrl = $derived(auth.user?.avatar);

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

	// --- MOCK: thông tin cá nhân (User) ---
	let form = $state({
		last_name: 'Nguyễn Văn',
		first_name: 'An',
		email: 'nguyenvanan@example.com',
		phone: '0901234567'
	});

	// --- MOCK: StudentProfile ---
	let studentProfile = $state({
		grade_level: 'Khối 12',
		learning_goals: 'Muốn cải thiện kỹ năng Writing và ngữ pháp mệnh đề quan hệ.',
		academic_level: 'AVERAGE' as AcademicLevel
	});

	const academicLevelLabel: Record<AcademicLevel, string> = {
		POOR: 'Yếu',
		AVERAGE: 'Trung bình',
		GOOD: 'Khá',
		EXCELLENT: 'Giỏi'
	};

	// --- MOCK: TutorProfile ---
	let tutorProfile = $state({
		bio: 'Gia sư Toán - Tiếng Anh với 5 năm kinh nghiệm luyện thi THPT QG.',
		qualification: 'Cử nhân Sư phạm Toán, ĐH Sư phạm TP.HCM',
		experience_years: 5,
		is_verified: true
	});

	let isSavingProfile = $state(false);
	async function saveProfile() {
		isSavingProfile = true;
		try {
			// TODO: gọi API PATCH /api/users/me/ với form (+ studentProfile/tutorProfile theo role)
			await new Promise((r) => setTimeout(r, 600));
			showToast('Đã cập nhật hồ sơ', 'success');
		} catch (err: unknown) {
			console.log(err);
			showToast('Cập nhật hồ sơ không thành công', 'error');
		} finally {
			isSavingProfile = false;
		}
	}

	// --- Đổi mật khẩu ---
	let passwordForm = $state({
		current_password: '',
		new_password: '',
		confirm_password: ''
	});
	let isChangingPassword = $state(false);

	async function changePassword() {
		if (!passwordForm.current_password || !passwordForm.new_password) {
			showToast('Vui lòng nhập đầy đủ thông tin', 'error');
			return;
		}
		if (passwordForm.new_password !== passwordForm.confirm_password) {
			showToast('Mật khẩu mới không khớp', 'error');
			return;
		}
		isChangingPassword = true;
		try {
			// TODO: gọi API POST /api/users/change-password/
			await new Promise((r) => setTimeout(r, 600));
			showToast('Đã đổi mật khẩu', 'success');
			passwordForm = { current_password: '', new_password: '', confirm_password: '' };
		} catch (err) {
			console.log(err);
			showToast('Đổi mật khẩu không thành công', 'error');
		} finally {
			isChangingPassword = false;
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
	<title>Hồ sơ cá nhân</title>
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
					<span class="text-sm font-medium text-slate-700">{displayName}</span>
					<Avatar src={avatarUrl} name={displayName ?? ''} size="lg" />
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

		<main class="flex-1 overflow-y-auto px-8 py-8">
			<div class="mb-6">
				<h1
					class="text-2xl font-bold tracking-tight text-slate-900"
					style="font-family:'Sora',sans-serif;"
				>
					Hồ sơ cá nhân
				</h1>
				<p class="mt-1 text-sm text-slate-500">Quản lý thông tin tài khoản và bảo mật.</p>
			</div>

			<div class="grid grid-cols-1 gap-6 lg:grid-cols-3">
				<!-- CỘT TRÁI: avatar + tóm tắt -->
				<div class="lg:col-span-1">
					<div class="rounded-2xl border border-slate-200/70 bg-white p-6 text-center shadow-sm shadow-slate-200/50">
						<div class="mx-auto w-fit">
							<Avatar src={avatarUrl} name={displayName ?? ''} size="lg" />
						</div>
						<p class="mt-4 text-base font-bold text-slate-900" style="font-family:'Sora',sans-serif;">
							{displayName}
						</p>
						<p class="text-xs text-slate-500">{form.email}</p>

						<button
							class="mt-4 w-full rounded-xl border border-slate-200 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50"
						>
							Đổi ảnh đại diện
						</button>

						{#if role === 'tutor'}
							<div
								class={`mt-4 flex items-center justify-center gap-2 rounded-xl px-3 py-2 text-xs font-semibold ${
									tutorProfile.is_verified
										? 'bg-emerald-50 text-emerald-600'
										: 'bg-amber-50 text-amber-600'
								}`}
							>
								<ShieldCheck class="h-4 w-4" />
								{tutorProfile.is_verified ? 'Tài khoản đã xác minh' : 'Chờ xác minh'}
							</div>
						{/if}
					</div>
				</div>

				<!-- CỘT PHẢI: các form -->
				<div class="space-y-6 lg:col-span-2">
					<!-- THÔNG TIN CÁ NHÂN -->
					<div class="rounded-2xl border border-slate-200/70 bg-white p-6 shadow-sm shadow-slate-200/50">
						<div class="mb-4 flex items-center gap-2">
							<User class="h-4 w-4 text-indigo-600" />
							<h2 class="text-sm font-semibold text-slate-800" style="font-family:'Sora',sans-serif;">
								Thông tin cá nhân
							</h2>
						</div>

						<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
							<div>
								<label for="last_name" class="mb-1 block text-xs font-medium text-slate-500">Họ</label>
								<input
									id="last_name"
									class="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-indigo-300 focus:bg-white focus:ring-4 focus:ring-indigo-50"
									bind:value={form.last_name}
								/>
							</div>
							<div>
								<label for="first_name" class="mb-1 block text-xs font-medium text-slate-500">Tên</label>
								<input
									id="first_name"
									class="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-indigo-300 focus:bg-white focus:ring-4 focus:ring-indigo-50"
									bind:value={form.first_name}
								/>
							</div>
							<div>
								<label for="email" class="mb-1 block text-xs font-medium text-slate-500">Email</label>
								<input
									id="email"
									type="email"
									class="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-indigo-300 focus:bg-white focus:ring-4 focus:ring-indigo-50"
									bind:value={form.email}
								/>
							</div>
							<div>
								<label for="phone" class="mb-1 block text-xs font-medium text-slate-500">Số điện thoại</label>
								<input
									id="phone"
									class="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-indigo-300 focus:bg-white focus:ring-4 focus:ring-indigo-50"
									bind:value={form.phone}
								/>
							</div>
						</div>

						{#if role === 'student'}
							<div class="mt-5 border-t border-slate-100 pt-5">
								<div class="mb-3 flex items-center gap-2">
									<GraduationCap class="h-4 w-4 text-indigo-600" />
									<h3 class="text-xs font-semibold uppercase tracking-wide text-slate-500">
										Thông tin học tập
									</h3>
								</div>
								<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
									<div>
										<label for="grade" class="mb-1 block text-xs font-medium text-slate-500">Khối lớp</label>
										<input
											id="grade"
											class="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-indigo-300 focus:bg-white focus:ring-4 focus:ring-indigo-50"
											bind:value={studentProfile.grade_level}
										/>
									</div>
									<div>
										<label for="level" class="mb-1 block text-xs font-medium text-slate-500">Học lực hiện tại</label>
										<select
											id="level"
											class="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-indigo-300 focus:bg-white focus:ring-4 focus:ring-indigo-50"
											bind:value={studentProfile.academic_level}
										>
											{#each Object.entries(academicLevelLabel) as [value, label] (value)}
												<option {value}>{label}</option>
											{/each}
										</select>
									</div>
									<div class="sm:col-span-2">
										<label for="goals" class="mb-1 block text-xs font-medium text-slate-500">Mục tiêu học tập</label>
										<textarea
											id="goals"
											rows="3"
											class="w-full resize-none rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-indigo-300 focus:bg-white focus:ring-4 focus:ring-indigo-50"
											bind:value={studentProfile.learning_goals}
										></textarea>
									</div>
								</div>
							</div>
						{:else}
							<div class="mt-5 border-t border-slate-100 pt-5">
								<div class="mb-3 flex items-center gap-2">
									<GraduationCap class="h-4 w-4 text-indigo-600" />
									<h3 class="text-xs font-semibold uppercase tracking-wide text-slate-500">
										Thông tin giảng dạy
									</h3>
								</div>
								<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
									<div>
										<label for="qualification" class="mb-1 block text-xs font-medium text-slate-500">
											Trình độ
										</label>
										<input
											id="qualification"
											class="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-indigo-300 focus:bg-white focus:ring-4 focus:ring-indigo-50"
											bind:value={tutorProfile.qualification}
										/>
									</div>
									<div>
										<label for="years" class="mb-1 block text-xs font-medium text-slate-500">
											Số năm kinh nghiệm
										</label>
										<input
											id="years"
											type="number"
											min="0"
											class="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-indigo-300 focus:bg-white focus:ring-4 focus:ring-indigo-50"
											bind:value={tutorProfile.experience_years}
										/>
									</div>
									<div class="sm:col-span-2">
										<label for="bio" class="mb-1 block text-xs font-medium text-slate-500">Giới thiệu ngắn</label>
										<textarea
											id="bio"
											rows="3"
											class="w-full resize-none rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-indigo-300 focus:bg-white focus:ring-4 focus:ring-indigo-50"
											bind:value={tutorProfile.bio}
										></textarea>
									</div>
								</div>
							</div>
						{/if}

						<div class="mt-5 flex justify-end">
							<button
								class="rounded-xl bg-[#0C1550] px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-indigo-600 disabled:opacity-60"
								disabled={isSavingProfile}
								onclick={saveProfile}
							>
								{isSavingProfile ? 'Đang lưu...' : 'Lưu thay đổi'}
							</button>
						</div>
					</div>

					<!-- ĐỔI MẬT KHẨU -->
					<div class="rounded-2xl border border-slate-200/70 bg-white p-6 shadow-sm shadow-slate-200/50">
						<div class="mb-4 flex items-center gap-2">
							<KeyRound class="h-4 w-4 text-indigo-600" />
							<h2 class="text-sm font-semibold text-slate-800" style="font-family:'Sora',sans-serif;">
								Đổi mật khẩu
							</h2>
						</div>

						<div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
							<div>
								<label for="current_password" class="mb-1 block text-xs font-medium text-slate-500">
									Mật khẩu hiện tại
								</label>
								<input
									id="current_password"
									type="password"
									class="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-indigo-300 focus:bg-white focus:ring-4 focus:ring-indigo-50"
									bind:value={passwordForm.current_password}
								/>
							</div>
							<div>
								<label for="new_password" class="mb-1 block text-xs font-medium text-slate-500">
									Mật khẩu mới
								</label>
								<input
									id="new_password"
									type="password"
									class="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-indigo-300 focus:bg-white focus:ring-4 focus:ring-indigo-50"
									bind:value={passwordForm.new_password}
								/>
							</div>
							<div>
								<label for="confirm_password" class="mb-1 block text-xs font-medium text-slate-500">
									Xác nhận mật khẩu mới
								</label>
								<input
									id="confirm_password"
									type="password"
									class="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-indigo-300 focus:bg-white focus:ring-4 focus:ring-indigo-50"
									bind:value={passwordForm.confirm_password}
								/>
							</div>
						</div>

						<div class="mt-5 flex justify-end">
							<button
								class="rounded-xl border border-slate-200 px-5 py-2.5 text-sm font-semibold text-slate-700 transition-colors hover:bg-slate-50 disabled:opacity-60"
								disabled={isChangingPassword}
								onclick={changePassword}
							>
								{isChangingPassword ? 'Đang xử lý...' : 'Đổi mật khẩu'}
							</button>
						</div>
					</div>
				</div>
			</div>
		</main>
	</div>
</div>