export function nextOrder(items: { order: number | null }[]): number {
	return items.reduce((max, item) => Math.max(max, item.order ?? 0), 0) + 1;
}
