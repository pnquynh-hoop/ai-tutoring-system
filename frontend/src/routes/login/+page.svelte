<script lang="ts">
	import { Bot, Eye, EyeOff } from 'lucide-svelte';
	import { loginApi } from '$lib/api/auth';
	import { goto } from '$app/navigation';

	let username = $state('');
	let password = $state('');
	let errorMessage = $state('');
	let isLoading = $state(false);
	let showPassword = $state(false);

	async function handleLogin(event: SubmitEvent) {
		event.preventDefault();

		isLoading = true;
		errorMessage = '';

		try {
			await loginApi({username, password});
			await goto('/');
		} catch (err: any) {
			console.error(err);
			errorMessage = err.response?.data?.message || 'Có lỗi xảy ra, vui lòng thử lại.';
		} finally {
			isLoading = false;
		}
	}
</script>

<svelte:head>
	<title>Đăng nhập</title>
</svelte:head>

<div
	class="flex min-h-screen items-center justify-center bg-[#f8fafc] p-4 sm:p-6 lg:p-8 font-sans"
>
	<div
		class="w-full max-w-7xl bg-white rounded-3xl shadow-xl shadow-slate-200/50 overflow-hidden flex flex-col md:flex-row border border-slate-100 relative"
	>
		<div
			class="hidden md:flex md:w-1/2 bg-gradient-to-br from-blue-50 to-indigo-50 p-16 flex-col justify-center items-center relative overflow-hidden"
		>
			<div
				class="absolute top-0 left-0 w-full h-full overflow-hidden opacity-60 pointer-events-none"
			>
				<div class="absolute -top-24 -left-24 w-64 h-64 rounded-full bg-blue-200 blur-3xl"></div>
				<div
					class="absolute -bottom-24 -right-24 w-72 h-72 rounded-full bg-indigo-200 blur-3xl"
				></div>
			</div>

			<div class="relative z-10 flex flex-col items-center text-center space-y-4">
				<h2 class="text-3xl font-extrabold text-slate-800 tracking-tight">
					Trung Tâm Gia Sư CaSiu
				</h2>
				<p class="text-slate-600 text-base leading-relaxed max-w-sm">
					Kết nối tri thức, ươm mầm tương lai. Đăng nhập để tham gia học tập các khóa học thú vị của
					bạn.
				</p>

				<div
					class="w-80 h-80 mt-12 bg-white/40 backdrop-blur-sm rounded-2xl border border-white/60 shadow-sm flex items-center justify-center"
				>
					<img
						src="https://res.cloudinary.com/desvczltb/image/upload/v1784110310/Education-rafiki_ffhps3.svg"
						alt="Hệ thống trung tâm gia sư"
						class="w-full h-full object-contain drop-shadow-xl transition-transform duration-500 hover:scale-105"
					/>
				</div>
			</div>
		</div>

		<div
			class="hidden md:block absolute left-1/2 -translate-x-1/2 top-0 h-full w-16 pointer-events-none z-20 bg-gradient-to-r from-transparent via-slate-300/30 to-transparent"
		>
			<div
				class="absolute left-1/2 -translate-x-1/2 top-0 h-full w-px bg-slate-200 shadow-[0_0_15px_3px_rgba(0,0,0,0.08)]"
			></div>
		</div>

		<div class="w-full md:w-1/2 p-12 sm:p-16 lg:p-20 flex flex-col justify-center bg-white">
			<div class="mb-10 text-center md:text-left">
				<h2 class="flex items-center gap-3 text-3xl font-bold tracking-tight text-slate-900">
					Chào mừng quay lại!

					<div
						class="animate-float group relative flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-500 shadow-md shadow-indigo-200 transition-all duration-300 hover:shadow-lg hover:shadow-indigo-300"
					>
						<div
							class="absolute inset-0 rounded-2xl bg-white/20 opacity-0 transition-opacity duration-300 group-hover:opacity-100"
						></div>

						<Bot
							class="relative z-10 h-6 w-6 text-white transition-transform duration-300 group-hover:scale-110 group-hover:rotate-12"
						/>
					</div>
				</h2>
				<p class="mt-2.5 text-sm text-slate-500">
					Vui lòng điền đầy đủ thông tin để truy cập vào hệ thống.
				</p>
			</div>

			<form class="space-y-5" onsubmit={handleLogin}>
				<div>
					<label for="username" class="block text-sm font-semibold text-slate-700 mb-1.5">
						Tên đăng nhập
					</label>
					<input
						type="text"
						id="username"
						bind:value={username}
						required
						placeholder="Nhập tên đăng nhập..."
						disabled={isLoading}
						class="block w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3.5 text-slate-900 placeholder-slate-400 focus:bg-white focus:border-blue-500 focus:outline-none focus:ring-4 focus:ring-blue-500/10 transition-all duration-200 sm:text-sm disabled:opacity-60"
					/>
				</div>

				<div>
					<div class="flex justify-between items-center mb-1.5">
						<label for="password" class="block text-sm font-semibold text-slate-700">
							Mật khẩu
						</label>
						<a
							href="#"
							class="text-sm font-medium text-blue-600 hover:text-blue-700 hover:underline transition-all"
							>Quên mật khẩu?</a
						>
					</div>

					<div class="relative">
						<input
							type={showPassword ? 'text' : 'password'}
							id="password"
							bind:value={password}
							required
							placeholder="••••••••"
							disabled={isLoading}
							class="block w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3.5 pr-12 text-slate-900 placeholder-slate-400 focus:bg-white focus:border-blue-500 focus:outline-none focus:ring-4 focus:ring-blue-500/10 transition-all duration-200 sm:text-sm disabled:opacity-60"
						/>

						<button
							type="button"
							onclick={() => (showPassword = !showPassword)}
							disabled={isLoading}
							class="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-slate-600 focus:outline-none disabled:opacity-50 transition-colors"
						>
							{#if showPassword}
								<EyeOff class="h-5 w-5" />
							{:else}
								<Eye class="h-5 w-5" />
							{/if}
						</button>
					</div>
				</div>

				{#if errorMessage}
					<div
						class="rounded-xl bg-red-50 p-4 border border-red-100 flex items-center gap-3 text-sm text-red-600"
					>
						<svg class="h-5 w-5 text-red-500 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor">
							<path
								fill-rule="evenodd"
								d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z"
								clip-rule="evenodd"
							/>
						</svg>
						<p>{errorMessage}</p>
					</div>
				{/if}

				<div class="pt-2">
					<button
						type="submit"
						disabled={isLoading}
						class="group relative flex w-full justify-center items-center gap-2 rounded-xl bg-slate-900 px-4 py-3.5 text-sm font-bold text-white shadow-md hover:bg-slate-800 hover:shadow-lg hover:-translate-y-0.5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-900 transition-all duration-200 disabled:bg-slate-300 disabled:hover:translate-y-0 disabled:cursor-not-allowed"
					>
						{#if isLoading}
							<svg
								class="animate-spin h-5 w-5 text-white/70"
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
							>
								<circle
									class="opacity-25"
									cx="12"
									cy="12"
									r="10"
									stroke="currentColor"
									stroke-width="4"
								></circle>
								<path
									class="opacity-75"
									fill="currentColor"
									d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
								></path>
							</svg>
							<span>Đang xử lý...</span>
						{:else}
							<span>Đăng Nhập</span>
							<svg
								class="w-4 h-4 transition-transform duration-300 group-hover:translate-x-1"
								fill="none"
								viewBox="0 0 24 24"
								stroke="currentColor"
								stroke-width="2.5"
							>
								<path stroke-linecap="round" stroke-linejoin="round" d="M14 5l7 7m0 0l-7 7m7-7H3" />
							</svg>
						{/if}
					</button>
				</div>
			</form>
		</div>
	</div>
</div>

<style>
	@keyframes float {
		0%,
		100% {
			transform: translateY(0);
		}
		50% {
			transform: translateY(-10px); /* Độ cao khi bay lên */
		}
	}

	.animate-float {
		animation: float 3s ease-in-out infinite;
	}
</style>
