<script lang="ts">
	import { goto, invalidateAll } from '$app/navigation';
	import { changePassword, updateMyAvatar, updateMyProfile } from '$lib/api/calledAPI';
	import { getApiErrorMessage } from '$lib/api/errors';
	import Avatar from '$lib/components/Avatar.svelte';
	import FieldError from '$lib/components/FieldError.svelte';
	import {
		FIELD_LIMITS,
		IMAGE_EXTENSIONS,
		emailError,
		hasError,
		imageFileError,
		phoneError,
		requiredError,
		textError
	} from '$lib/utils/validation';
	import { showToast } from '$lib/stores/toast.svelte';
	import { confirmAction } from '$lib/stores/confirm.svelte';
	import { Camera, Home, KeyRound, Lightbulb, Loader2, Save, User } from 'lucide-svelte';
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
		academic_level: ''
	});

	$effect(() => {
		form = {
			first_name: data.me.first_name ?? '',
			last_name: data.me.last_name ?? '',
			email: data.me.email ?? '',
			phone: data.me.phone ?? '',
			grade_level: data.me.student_profile?.grade_level ?? null,
			learning_goals: data.me.student_profile?.learning_goals ?? '',
			academic_level: data.me.student_profile?.academic_level ?? data.academicLevels[0]?.value ?? ''
		};
	});

	let isUploadingAvatar = $state(false);
	let avatarError = $state('');

	async function pickAvatar(event: Event) {
		const input = event.currentTarget as HTMLInputElement;
		const file = input.files?.[0] ?? null;
		if (!file) return;

		avatarError = imageFileError(file, 'Ảnh đại diện');
		if (avatarError) {
			input.value = '';
			return;
		}

		isUploadingAvatar = true;
		try {
			await updateMyAvatar(file);
			showToast('Đã cập nhật ảnh đại diện', 'success');
			await invalidateAll();
		} catch (err) {
			showToast(getApiErrorMessage(err, 'Cập nhật ảnh đại diện không thành công.'), 'error');
		} finally {
			isUploadingAvatar = false;
			input.value = '';
		}
	}

	let isSaving = $state(false);
	let profileErrors = $state<Record<string, string>>({});

	function clearProfileError(field: string) {
		profileErrors = { ...profileErrors, [field]: '' };
	}

	function validateProfile(): boolean {
		profileErrors = {
			last_name: textError(form.last_name, FIELD_LIMITS.title, 'Họ và tên đệm'),
			first_name: textError(form.first_name, FIELD_LIMITS.title, 'Tên'),
			email: emailError(form.email, 'Email'),
			phone: phoneError(form.phone, 'Số điện thoại')
		};
		return !hasError(profileErrors);
	}

	async function saveProfile() {
		if (isSaving) return;
		if (!validateProfile()) return;

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
	let passwordErrors = $state<Record<string, string>>({});

	function clearPasswordError(field: string) {
		passwordErrors = { ...passwordErrors, [field]: '' };
	}

	function validatePassword(): boolean {
		const errors: Record<string, string> = {
			old_password: requiredError(passwordForm.old_password, 'Mật khẩu hiện tại'),
			new_password: requiredError(passwordForm.new_password, 'Mật khẩu mới'),
			confirm_password: requiredError(passwordForm.confirm_password, 'Xác nhận mật khẩu mới')
		};

		if (!errors.new_password && passwordForm.new_password.length < 8) {
			errors.new_password = 'Mật khẩu mới phải có ít nhất 8 ký tự.';
		}

		if (!errors.confirm_password && passwordForm.confirm_password !== passwordForm.new_password) {
			errors.confirm_password = 'Xác nhận mật khẩu không khớp với mật khẩu mới.';
		}

		passwordErrors = errors;
		return !hasError(errors);
	}

	async function submitPassword() {
		if (isChangingPassword) return;
		if (!validatePassword()) return;

		const agreed = await confirmAction({
			title: 'Đổi mật khẩu tài khoản?',
			message:
				'Sau khi đổi, bạn phải dùng mật khẩu mới cho những lần đăng nhập sau. Hãy chắc chắn bạn đã ghi nhớ mật khẩu mới.',
			confirmLabel: 'Đổi mật khẩu',
			tone: 'danger'
		});
		if (!agreed) return;

		isChangingPassword = true;
		try {
			await changePassword(passwordForm);
			passwordForm = { old_password: '', new_password: '', confirm_password: '' };
			passwordErrors = {};
			showToast('Đổi mật khẩu thành công', 'success');
		} catch (err) {
			showToast(getApiErrorMessage(err, 'Đổi mật khẩu không thành công.'), 'error');
		} finally {
			isChangingPassword = false;
		}
	}
</script>

<svelte:head>
	<title>Hồ sơ cá nhân</title>
</svelte:head>

<div class="min-h-screen bg-slate-50">
	<header
		class="flex items-center justify-between gap-4 border-b border-slate-200/70 bg-white/80 px-8 py-4 backdrop-blur"
	>
		<div class="flex min-w-0 items-center gap-3">
			<div
				class="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-600"
			>
				<User class="h-4.5 w-4.5" />
			</div>
			<div class="min-w-0">
				<h1 class="font-heading text-sm font-semibold text-slate-800">Hồ sơ cá nhân</h1>
				<p class="truncate text-xs text-slate-500">
					Cập nhật thông tin liên lạc và mật khẩu đăng nhập của bạn
				</p>
			</div>
		</div>

		<button
			onclick={() => goto('/stu-dashboard')}
			class="flex items-center gap-2 rounded-full bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
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
				<label
					class="group relative shrink-0 rounded-full {isUploadingAvatar
						? 'pointer-events-none'
						: 'cursor-pointer'}"
					title="Đổi ảnh đại diện"
				>
					<Avatar src={me.avatar} name={me.full_name} size="xl" />
					<span
						class="absolute inset-0 flex items-center justify-center rounded-full bg-slate-900/45 text-white transition-opacity {isUploadingAvatar
							? 'opacity-100'
							: 'opacity-0 group-hover:opacity-100'}"
					>
						{#if isUploadingAvatar}
							<Loader2 class="h-6 w-6 animate-spin" />
						{:else}
							<Camera class="h-6 w-6" />
						{/if}
					</span>
					<input
						type="file"
						accept={IMAGE_EXTENSIONS.join(',')}
						class="hidden"
						disabled={isUploadingAvatar}
						onchange={pickAvatar}
					/>
				</label>
				<div class="min-w-0 flex-1">
					<h1 class="text-xl font-bold text-slate-900 font-heading">
						{me.full_name}
					</h1>
					<p class="mt-0.5 text-sm text-slate-500">
						Học sinh
						{#if me.student_profile?.grade_name}
							· {me.student_profile.grade_name}
						{/if}
					</p>
					<FieldError message={avatarError} />
				</div>
			</div>

			<div
				class="rounded-2xl border border-slate-200/70 bg-white p-6 shadow-sm shadow-slate-200/50"
			>
				<h2 class="mb-4 flex items-center gap-2 text-sm font-semibold text-slate-800 font-heading">
					<User class="h-4 w-4" />
					Thông tin cá nhân
				</h2>

				<div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
					<label class="block">
						<span class="mb-1 block text-xs font-medium text-slate-500">Họ</span>
						<input
							oninput={() => clearProfileError('last_name')}
							class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-300"
							bind:value={form.last_name}
						/>
						<FieldError message={profileErrors.last_name} />
					</label>
					<label class="block">
						<span class="mb-1 block text-xs font-medium text-slate-500">Tên</span>
						<input
							oninput={() => clearProfileError('first_name')}
							class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-300"
							bind:value={form.first_name}
						/>
						<FieldError message={profileErrors.first_name} />
					</label>
					<label class="block">
						<span class="mb-1 block text-xs font-medium text-slate-500">Email</span>
						<input
							oninput={() => clearProfileError('email')}
							type="email"
							class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-300"
							bind:value={form.email}
						/>
						<FieldError message={profileErrors.email} />
					</label>
					<label class="block">
						<span class="mb-1 block text-xs font-medium text-slate-500">Số điện thoại</span>
						<input
							oninput={() => clearProfileError('phone')}
							class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-300"
							bind:value={form.phone}
						/>
						<FieldError message={profileErrors.phone} />
					</label>
				</div>
			</div>

			{#if me.student_profile}
				<div
					class="rounded-2xl border border-slate-200/70 bg-white p-6 shadow-sm shadow-slate-200/50"
				>
					<h2 class="mb-3 text-sm font-semibold text-slate-800 font-heading">Hồ sơ học tập</h2>

					<div class="mb-4 flex gap-2.5 rounded-xl bg-brand-50 p-3 text-brand-900">
						<Lightbulb class="mt-0.5 h-4 w-4 shrink-0 text-brand-500" />
						<p class="text-xs leading-relaxed">
							<span class="font-semibold">Bạn có biết?</span> Những thông tin dưới đây giúp trợ lý
							học tập hiểu bạn đang ở đâu, để phần giải thích vừa sức và bám đúng thứ bạn đang cần.
						</p>
					</div>

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
							<span class="block text-xs font-medium text-slate-500">Mục tiêu học tập</span>
							<span class="mb-1.5 block text-[11px] text-slate-400">
								Viết ngắn gọn điều bạn muốn đạt được, trợ lý sẽ bám vào đó khi hướng dẫn bạn.
							</span>
							<textarea
								rows="3"
								class="w-full resize-none rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-300"
								bind:value={form.learning_goals}></textarea>
						</label>
						<label class="block">
							<span class="block text-xs font-medium text-slate-500">Học lực</span>
							<span class="mb-1.5 block text-[11px] text-slate-400">
								Chọn đúng mức hiện tại của bạn để phần giải thích không quá dễ cũng không quá khó.
							</span>
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

			<div class="flex justify-end">
				<button
					onclick={saveProfile}
					disabled={isSaving}
					class="flex items-center gap-2 rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
				>
					<Save class="h-4 w-4" />
					Lưu hồ sơ
				</button>
			</div>

			<div
				class="rounded-2xl border border-slate-200/70 bg-white p-6 shadow-sm shadow-slate-200/50"
			>
				<h2 class="mb-4 flex items-center gap-2 text-sm font-semibold text-slate-800 font-heading">
					<KeyRound class="h-4 w-4" />
					Đổi mật khẩu
				</h2>

				<div class="grid grid-cols-1 gap-3 sm:grid-cols-3">
					<input
						oninput={() => clearPasswordError('old_password')}
						type="password"
						placeholder="Mật khẩu hiện tại"
						class="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-300"
						bind:value={passwordForm.old_password}
					/>
					<FieldError message={passwordErrors.old_password} />
					<input
						oninput={() => clearPasswordError('new_password')}
						type="password"
						placeholder="Mật khẩu mới"
						class="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-300"
						bind:value={passwordForm.new_password}
					/>
					<FieldError message={passwordErrors.new_password} />
					<input
						oninput={() => clearPasswordError('confirm_password')}
						type="password"
						placeholder="Xác nhận mật khẩu mới"
						class="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-300"
						bind:value={passwordForm.confirm_password}
					/>
					<FieldError message={passwordErrors.confirm_password} />
				</div>

				<div class="mt-3 flex justify-end">
					<button
						onclick={submitPassword}
						disabled={isChangingPassword}
						class="flex items-center gap-2 rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
					>
						<KeyRound class="h-4 w-4" />
						Đổi mật khẩu
					</button>
				</div>
			</div>
		</div>
	</main>
</div>
