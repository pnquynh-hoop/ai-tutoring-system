import type { RagSource } from '$lib/api/entities';

/**
 * Ngữ cảnh gửi kèm khi hỏi AI.
 *
 * Backend bắt buộc `course_id` và kiểm tra học sinh đã ghi danh khóa đó, nên
 * ngữ cảnh của route (đang ở trong khóa/bài học nào) luôn được ưu tiên; chỉ khi
 * route không có mới dùng khóa học người dùng tự chọn trong sidebar.
 */
export function resolveChatContext(
	params: Record<string, string | undefined>,
	pickedCourseId: number | null = null
): { courseId: number | null; lessonId: number | null } {
	const routeCourseId = Number(params.courseId) || null;
	const routeLessonId = Number(params.lessonId) || null;

	return {
		courseId: routeCourseId ?? pickedCourseId,
		// lessonId chỉ có nghĩa khi nằm trong đúng khóa học của route.
		lessonId: routeCourseId ? routeLessonId : null
	};
}

/** Nhãn nguồn hiển thị cho học sinh; PyMuPDF đánh số trang từ 0 nên phải +1. */
export function formatSourceLabel(source: RagSource): string {
	if (source.page === null || source.page === undefined) return source.title;
	return `${source.title} · trang ${source.page + 1}`;
}
