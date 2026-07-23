import type { Toast } from "$lib/api/types";

const toasts = $state<Toast[]>([]);

export function showToast(message: string, type: Toast['type'] = "info") {
    const id = Date.now();
    toasts.push({
			id,
			message,
			type
		});

    setTimeout(() => {
        const index = toasts.findIndex((t) => t.id === id);
        if (index !== -1) {
            toasts.splice(index, 1);
        }
    }, 5000);
}

export function getToasts() {
    return toasts;
}