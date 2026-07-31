/**
 * Thứ tự cho phần tử mới = order lớn nhất hiện có + 1.
 *
 * Backend ràng buộc unique (course, order) và (chapter, order) nên không thể
 * dùng `length + 1`: sau khi xoá phần tử ở giữa, số lượng và order lệch nhau.
 */
export function nextOrder(items: { order: number | null }[]): number {
	return items.reduce((max, item) => Math.max(max, item.order ?? 0), 0) + 1;
}
