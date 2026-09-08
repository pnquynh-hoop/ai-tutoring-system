<script lang="ts">
	import type { ConfirmTone } from '$lib/api/types';
	import { answerConfirm, getConfirmBox } from '$lib/stores/confirm.svelte';
	import { Info, ShieldAlert, TriangleAlert } from 'lucide-svelte';

	const confirmBox = getConfirmBox();

	const toneStyles: Record<
		ConfirmTone,
		{ icon: typeof ShieldAlert; iconBox: string; confirmButton: string }
	> = {
		danger: {
			icon: ShieldAlert,
			iconBox: 'bg-rose-600 text-white',
			confirmButton: 'bg-rose-600 hover:bg-rose-700'
		},
		warning: {
			icon: TriangleAlert,
			iconBox: 'bg-yellow-500 text-white',
			confirmButton: 'bg-yellow-500 hover:bg-yellow-600'
		},
		info: {
			icon: Info,
			iconBox: 'bg-brand-600 text-white',
			confirmButton: 'bg-brand-600 hover:bg-brand-700'
		}
	};

	let request = $derived(confirmBox.request);
	let tone = $derived(toneStyles[request?.tone ?? 'danger']);

	function handleKeydown(event: KeyboardEvent) {
		if (!request) return;
		if (event.key === 'Escape') answerConfirm(false);
	}
</script>

<svelte:window onkeydown={handleKeydown} />

{#if request}
	<div class="fixed inset-0 z-[60] flex items-center justify-center px-4">
		<button
			class="absolute inset-0 cursor-default bg-slate-900/40 backdrop-blur-sm"
			onclick={() => answerConfirm(false)}
			aria-label="Đóng hộp thoại"
		></button>

		<div
			role="alertdialog"
			aria-modal="true"
			aria-labelledby="confirm-dialog-title"
			aria-describedby="confirm-dialog-message"
			class="relative w-full max-w-md overflow-hidden rounded-2xl border border-slate-200/70 bg-white shadow-2xl shadow-slate-900/20"
		>
			<div class="flex gap-4 px-6 pt-6">
				<div
					class={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ${tone.iconBox}`}
				>
					<tone.icon class="h-5 w-5" />
				</div>
				<div class="min-w-0 flex-1">
					<h2 id="confirm-dialog-title" class="text-base font-bold text-slate-900 font-heading">
						{request.title}
					</h2>
					<p id="confirm-dialog-message" class="mt-1.5 text-sm leading-relaxed text-slate-600">
						{request.message}
					</p>
				</div>
			</div>

			<div class="mt-6 flex justify-end gap-2 bg-slate-50 px-6 py-4">
				{#if !request.acknowledgeOnly}
					<button
						onclick={() => answerConfirm(false)}
						class="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100"
					>
						{request.cancelLabel ?? 'Huỷ'}
					</button>
				{/if}
				<!-- svelte-ignore a11y_autofocus -->
				<button
					autofocus
					onclick={() => answerConfirm(true)}
					class={`rounded-xl px-4 py-2 text-sm font-semibold text-white ${tone.confirmButton}`}
				>
					{request.confirmLabel ?? 'Đồng ý'}
				</button>
			</div>
		</div>
	</div>
{/if}
