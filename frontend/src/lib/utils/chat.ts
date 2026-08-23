import type { RagSource } from '$lib/api/entities';

export function resolveChatContext(
	params: Record<string, string | undefined>,
	pickedCourseId: number | null = null
): { courseId: number | null; lessonId: number | null } {
	const routeCourseId = Number(params.courseId) || null;
	const routeLessonId = Number(params.lessonId) || null;

	return {
		courseId: routeCourseId ?? pickedCourseId,
		lessonId: routeCourseId ? routeLessonId : null
	};
}

export function formatSourceLabel(source: RagSource): string {
	if (source.page === null || source.page === undefined) return source.title;
	return `${source.title} · trang ${source.page + 1}`;
}
