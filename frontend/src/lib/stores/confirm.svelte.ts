import type { ConfirmRequest } from '$lib/api/types';

const confirmBox = $state({ request: null as ConfirmRequest | null });

let answerCurrent: ((agreed: boolean) => void) | null = null;

export function confirmAction(request: ConfirmRequest): Promise<boolean> {
	answerConfirm(false);

	return new Promise((resolve) => {
		answerCurrent = resolve;
		confirmBox.request = request;
	});
}

export function notifyAction(request: Omit<ConfirmRequest, 'acknowledgeOnly'>): Promise<boolean> {
	return confirmAction({ ...request, acknowledgeOnly: true });
}

export function getConfirmBox() {
	return confirmBox;
}

export function answerConfirm(agreed: boolean) {
	const answer = answerCurrent;
	if (!answer) return;

	answerCurrent = null;
	confirmBox.request = null;
	answer(agreed);
}
