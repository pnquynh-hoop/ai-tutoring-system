<script lang="ts">
	import { goto, invalidateAll } from '$app/navigation';
	import { changePassword, updateMyProfile } from '$lib/api/calledAPI';
	import { getApiErrorMessage } from '$lib/api/errors';
	import Avatar from '$lib/components/Avatar.svelte';
	import { showToast } from '$lib/stores/toast.svelte';
	import { Home, KeyRound, Save, ShieldCheck, User } from 'lucide-svelte';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
	let me = $derived(data.me);
	let grades = $derived(data.grades);
	let academicLevels = $derived(data.academicLevels);

	let form = $state({
		first_name: '',
		last_name: '',
		email: '',
		phone: '',
		grade_level: null as number | null,
		learning_goals: '',
		academic_level: '',
		bio: '',
		qualification: '',
		experience_years: 0
	});

	$effect(() => {
		form = {
			first_name: data.me.first_name ?? '',
			last_name: data.me.last_name ?? '',
			email: data.me.email ?? '',
			phone: data.me.phone ?? '',
			grade_level: data.me.student_profile?.grade_level ?? null,
			learning_goals: data.me.student_profile?.learning_goals ?? '',
			academic_level:
				data.me.student_profile?.academic_level ?? data.academicLevels[0]?.value ?? '',
			bio: data.me.tutor_profile?.bio ?? '',
			qualification: data.me.tutor_profile?.qualification ?? '',
			experience_years: data.me.tutor_profile?.experience_years ?? 0
		};
	});

	let isSaving = $state(false);

	async function saveProfile() {
		if (isSaving) return;
		isSaving = true;
		try {
			await updateMyProfile({
				first_name: form.first_name,
				last_name: form.last_name,
				email: form.email,
				phone: form.phone,
				...(me.student_profile
					? {
							student_profile: {
								grade_level: form.grade_level,
								learning_goals: form.learning_goals,
								academic_level: form.academic_level as 'POOR' | 'AVERAGE' | 'GOOD' | 'EXCELLENT'
							}
						}
					: {}),
				...(me.tutor_profile
					? {
							tutor_profile: {
								bio: form.bio,
								qualification: form.qualification,
								experience_years: Number(form.experience_years)
							}
						}
					: {})
			});
			showToast('Đã lưu hồ sơ', 'success');
			await invalidateAll();
		} catch (err) {
			showToast(getApiErrorMessage(err, 'Lưu hồ sơ không thành công.'), 'error');
		} finally {
			isSaving = false;
		}
	}

	let passwordForm = $state({ old_password: '', new_password: '', confirm_password: '' });
	let isChangingPassword = $state(false);

	async function submitPassword() {
		if (isChangingPassword) return;
		isChangingPassword = true;
		try {
			await changePassword(passwordForm);
			passwordForm = { old_password: '', new_password: '', confirm_password: '' };
			showToast('Đổi mật khẩu thành công', 'success');
		} catch (err) {
			showToast(getApiErrorMessage(err, 'Đổi mật khẩu không thành công.'), 'error');
		} finally {
			isChangingPassword = false;
		}
	}
</script>

<svelte:head>
	<link rel="preconnect" href="https://fonts.googleapis.com" />
	<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="" />
	<link
		href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Sora:wght@600;700;800&display=swap"
		rel="stylesheet"
	/>
	<title>Hồ sơ cá nhân</title>
</svelte:head>

<div class="min-h-screen bg-slate-50" style="font-family:'Inter',sans-serif;">
	<header
		class="flex items-center justify-between border-b border-slate-200/70 bg-white/80 px-8 py-4 backdrop-blur"
	>
		<button
			onclick={() => goto(me.role === 'Tutor' ? '/tutor-dashboard' : '/stu-dashboard')}
			class="flex items-center gap-2 rounded-full bg-brand-950 px-4 py-2 text-sm font-medium text-white hover:bg-brand-900"
		>
			<Home class="h-4 w-4" />
			Trang chủ
		</button>
	</header>

	<main class="px-8 py-8">
		<div class="mx-auto max-w-3xl space-y-6">
			<div
				class="flex items-center gap-4 rounded-2xl border border-slate-200/70 bg-white p-6 shadow-sm shadow-slate-200/50"
			>
				<Avatar src={me.avatar} name={me.full_name} size="lg" />
				<div class="min-w-0 flex-1">
					<h1 class="text-xl font-bold text-slate-900" style="font-family:'Sora',sans-serif;">
						{me.full_name}
					</h1>
					<p class="mt-0.5 text-sm text-slate-500">
						{me.role === 'Tutor' ? 'Gia sư' : 'Học sinh'}
						{#if me.student_profile?.grade_name}
							· {me.student_profile.grade_name}
						{/if}
					</p>
				</div>
				{#if me.tutor_profile?.is_verified}
					<span
						class="flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700"
					>
						<ShieldCheck class="h-3.5 w-3.5" />
						Đã xác minh
					</span>
				{/if}
			</div>

			<div
				class="rounded-2xl border border-slate-200/70 bg-white p-6 shadow-sm shadow-slate-200/50"
			>
				<h2
					class="mb-4 flex items-center gap-2 text-sm font-semibold text-slate-800"
					style="font-family:'Sora',sans-serif;"
				>
					<User class="h-4 w-4" />
					Thông tin cá nhân
				</h2>

				<div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
					<label class="block">
						<span class="mb-1 block text-xs font-medium text-slate-500">Họ</span>
						<input
							class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-300"
							bind:value={form.last_name}
						/>
					</label>
					<label class="block">
						<span class="mb-1 block text-xs font-medium text-slate-500">Tên</span>
						<input
							class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-300"
							bind:value={form.first_name}
						/>
					</label>
					<label class="block">
						<span class="mb-1 block text-xs font-medium text-slate-500">Email</span>
						<input
							type="email"
							class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-300"
							bind:value={form.email}
						/>
					</label>
					<label class="block">
						<span class="mb-1 block text-xs font-medium text-slate-500">Số điện thoại</span>
						<input
							class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-300"
							bind:value={form.phone}
						/>
					</label>
				</div>
			</div>

			{#if me.student_profile}
				<div
					class="rounded-2xl border border-slate-200/70 bg-white p-6 shadow-sm shadow-slate-200/50"
				>
					<h2
						class="mb-4 text-sm font-semibold text-slate-800"
						style="font-family:'Sora',sans-serif;"
					>
						Hồ sơ học tập
					</h2>

					<div class="space-y-3">
						<label class="block">
							<span class="mb-1 block text-xs font-medium text-slate-500">Khối lớp</span>
							<select
								class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-300"
								bind:value={form.grade_level}
							>
								<option value={null}>Chưa chọn</option>
								{#each grades as grade (grade.id)}
									<option value={grade.id}>{grade.name}</option>
								{/each}
							</select>
						</label>
						<label class="block">
							<span class="mb-1 block text-xs font-medium text-slate-500">Mục tiêu học tập</span>
							<textarea
								rows="3"
								class="w-full resize-none rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-300"
								bind:value={form.learning_goals}></textarea>
						</label>
						<label class="block">
							<span class="mb-1 block text-xs font-medium text-slate-500">Học lực</span>
							<select
								class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-300"
								bind:value={form.academic_level}
							>
								{#each academicLevels as level (level.value)}
									<option value={level.value}>{level.label}</option>
								{/each}
							</select>
						</label>
					</div>
				</div>
			{/if}

			{#if me.tutor_profile}
				<div
					class="rounded-2xl border border-slate-200/70 bg-white p-6 shadow-sm shadow-slate-200/50"
				>
					<h2
						class="mb-4 text-sm font-semibold text-slate-800"
						style="font-family:'Sora',sans-serif;"
					>
						Hồ sơ gia sư
					</h2>

					<div class="space-y-3">
						<label class="block">
							<span class="mb-1 block text-xs font-medium text-slate-500">Giới thiệu ngắn</span>
							<textarea
								rows="3"
								class="w-full resize-none rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-300"
								bind:value={form.bio}></textarea>
						</label>
						<div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
							<label class="block">
								<span class="mb-1 block text-xs font-medium text-slate-500">Trình độ</span>
								<input
									class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-300"
									bind:value={form.qualification}
								/>
							</label>
							<label class="block">
								<span class="mb-1 block text-xs font-medium text-slate-500">Số năm kinh nghiệm</span
								>
								<input
									type="number"
									min="0"
									class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-300"
									bind:value={form.experience_years}
								/>
							</label>
						</div>
					</div>
				</div>
			{/if}

			<div class="flex justify-end">
				<button
					onclick={saveProfile}
					disabled={isSaving}
					class="flex items-center gap-2 rounded-xl bg-brand-950 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
				>
					<Save class="h-4 w-4" />
					Lưu hồ sơ
				</button>
			</div>

			<div
				class="rounded-2xl border border-slate-200/70 bg-white p-6 shadow-sm shadow-slate-200/50"
			>
				<h2
					class="mb-4 flex items-center gap-2 text-sm font-semibold text-slate-800"
					style="font-family:'Sora',sans-serif;"
				>
					<KeyRound class="h-4 w-4" />
					Đổi mật khẩu
				</h2>

				<div class="grid grid-cols-1 gap-3 sm:grid-cols-3">
					<input
						type="password"
						placeholder="Mật khẩu hiện tại"
						class="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-300"
						bind:value={passwordForm.old_password}
					/>
					<input
						type="password"
						placeholder="Mật khẩu mới"
						class="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-300"
						bind:value={passwordForm.new_password}
					/>
					<input
						type="password"
						placeholder="Xác nhận mật khẩu mới"
						class="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-300"
						bind:value={passwordForm.confirm_password}
					/>
				</div>

				<div class="mt-3 flex justify-end">
					<button
						onclick={submitPassword}
						disabled={isChangingPassword}
						class="rounded-xl border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
					>
						Đổi mật khẩu
					</button>
				</div>
			</div>
		</div>
	</main>
</div>
