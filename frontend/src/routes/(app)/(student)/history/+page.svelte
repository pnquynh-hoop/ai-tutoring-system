<script lang="ts">
	import { goto } from '$app/navigation';
	import { getSubmissionDetail } from '$lib/api/calledAPI';
	import { getApiErrorMessage } from '$lib/api/errors';
	import type { SubmissionDetail } from '$lib/api/entities';
	import { showToast } from '$lib/stores/toast.svelte';
	import { CheckCircle2, Clock, FileText, Home, XCircle } from 'lucide-svelte';
	import type { PageProps } from './$types';

	// ============================================================
	// Lịch sử làm bài: mỗi dòng là một Submission đã nộp. Mở ra xem lại từng
	// StudentAnswer kèm đáp án đúng, lời giải và nhận xét của gia sư.
	// ============================================================

	let { data }: PageProps = $props();
	let submissions = $derived(data.submissions);

	let selected = $state<SubmissionDetail | null>(null);
	let isLoadingDetail = $state(false);

	function formatDate(iso: string | null): string {
		if (!iso) return '--';
		return new Date(iso).toLocaleString('vi-VN', {
			day: '2-digit',
			month: '2-digit',
			year: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	async function openSubmission(submissionId: number) {
		isLoadingDetail = true;
		try {
			selected = await getSubmissionDetail(submissionId);
		} catch (err) {
			showToast(getApiErrorMessage(err, 'Không mở được bài làm.'), 'error');
		} finally {
			isLoadingDetail = false;
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
	<title>Lịch sử làm bài</title>
</svelte:head>

<div class="min-h-screen w-full bg-[#F4F5F8]" style="font-family:'Inter',sans-serif;">
	<header
		class="flex items-center justify-between border-b border-slate-200/70 bg-white/80 px-8 py-4 backdrop-blur"
	>
		<button
			onclick={() => goto('/stu-dashboard')}
			class="flex items-center gap-2 rounded-full bg-[#0C1550] px-4 py-2 text-sm font-medium text-white hover:bg-indigo-900"
		>
			<Home class="h-4 w-4" />
			Trang chủ
		</button>
	</header>

	<main class="px-8 py-8">
		<div class="mb-6">
			<h1
				class="text-2xl font-bold tracking-tight text-slate-900"
				style="font-family:'Sora',sans-serif;"
			>
				Lịch sử làm bài
			</h1>
			<p class="mt-1 text-sm text-slate-500">
				Toàn bộ bài tập bạn đã nộp, kèm điểm và nhận xét của gia sư.
			</p>
		</div>

		<div class="grid grid-cols-1 gap-6 lg:grid-cols-[380px_1fr]">
			<!-- DANH SÁCH BÀI ĐÃ NỘP -->
			<div
				class="rounded-2xl border border-slate-200/70 bg-white p-5 shadow-sm shadow-slate-200/50"
			>
				<div class="space-y-2">
					{#each submissions as submission (submission.id)}
						<button
							onclick={() => openSubmission(submission.id)}
							class={`w-full rounded-xl border p-3 text-left transition-colors ${
								selected?.id === submission.id
									? 'border-[#0C1550] bg-slate-50'
									: 'border-slate-100 hover:bg-slate-50'
							}`}
						>
							<div class="flex items-start justify-between gap-3">
								<div class="min-w-0">
									<p class="truncate text-sm font-medium text-slate-700">
										{submission.assignment_title}
									</p>
									<p class="truncate text-xs text-slate-400">
										{submission.course_name} · {submission.chapter_title}
									</p>
									<p class="mt-1 flex items-center gap-1 text-[11px] text-slate-400">
										<Clock class="h-3 w-3" />
										{formatDate(submission.submitted_at)}
									</p>
								</div>
								{#if submission.score === null}
									<span
										class="shrink-0 rounded-full bg-amber-50 px-2 py-0.5 text-[11px] font-medium text-amber-700"
									>
										Chờ chấm
									</span>
								{:else}
									<span
										class="shrink-0 rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-semibold text-emerald-700"
									>
										{submission.score}
									</span>
								{/if}
							</div>
						</button>
					{/each}

					{#if submissions.length === 0}
						<p class="py-10 text-center text-sm text-slate-400">Bạn chưa nộp bài tập nào.</p>
					{/if}
				</div>
			</div>

			<!-- XEM LẠI BÀI LÀM -->
			<div
				class="rounded-2xl border border-slate-200/70 bg-white p-6 shadow-sm shadow-slate-200/50"
			>
				{#if isLoadingDetail}
					<p class="py-20 text-center text-sm text-slate-400">Đang tải bài làm...</p>
				{:else if !selected}
					<p class="py-20 text-center text-sm text-slate-400">
						Chọn một bài ở danh sách bên trái để xem lại chi tiết.
					</p>
				{:else}
					<div class="mb-5 flex flex-wrap items-center justify-between gap-3">
						<div>
							<h2 class="text-base font-bold text-slate-900" style="font-family:'Sora',sans-serif;">
								{selected.assignment_title}
							</h2>
							<p class="mt-0.5 text-xs text-slate-400">
								{selected.course_name} · {selected.chapter_title}
							</p>
						</div>
						<div class="text-right">
							<p class="text-lg font-bold text-slate-900">{selected.score ?? 'Chờ chấm'}</p>
							<p class="text-[11px] text-slate-400">Điểm tổng</p>
						</div>
					</div>

					<div class="space-y-4">
						{#each selected.stu_answers as answer, index (answer.id)}
							<div class="rounded-xl border border-slate-100 bg-slate-50 p-4">
								<div class="flex items-start gap-2">
									{#if answer.is_correct === true}
										<CheckCircle2 class="mt-0.5 h-4 w-4 shrink-0 text-emerald-500" />
									{:else if answer.is_correct === false}
										<XCircle class="mt-0.5 h-4 w-4 shrink-0 text-rose-500" />
									{:else}
										<FileText class="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />
									{/if}
									<p class="text-sm font-medium text-slate-700">
										Câu {index + 1}: {answer.question_content}
									</p>
								</div>

								<div class="mt-2 space-y-1 pl-6 text-xs">
									<p class="text-slate-500">
										Bạn trả lời:
										<span class="font-medium text-slate-700">
											{answer.selected_answer ?? answer.answer_text ?? '(không trả lời)'}
										</span>
									</p>
									{#if answer.correct_answer}
										<p class="text-slate-500">
											Đáp án đúng:
											<span class="font-medium text-emerald-600">{answer.correct_answer}</span>
										</p>
									{/if}
									<p class="text-slate-500">
										Điểm: <span class="font-medium text-slate-700"
											>{answer.point ?? 'chưa chấm'}</span
										>
									</p>
									{#if answer.explanation}
										<p class="text-slate-500">
											Lời giải: <span class="text-slate-600">{answer.explanation}</span>
										</p>
									{/if}
									{#if answer.tutor_comment}
										<p class="rounded-lg bg-white px-3 py-2 text-slate-600">
											Nhận xét của gia sư: {answer.tutor_comment}
										</p>
									{/if}
								</div>
							</div>
						{/each}
					</div>
				{/if}
			</div>
		</div>
	</main>
</div>
