import { getListSubmissions, getTutorDetailCourse } from '$lib/api/calledAPI';
import type { PageLoad } from './$types';

export const ssr = false;

// Danh sách bài đã nộp trong khóa: backend tự lọc theo gia sư phụ trách.
export const load: PageLoad = async ({ params }) => {
	const courseId = Number(params.courseId);
	const [course, submissions] = await Promise.all([
		getTutorDetailCourse(courseId),
		getListSubmissions({ course: courseId })
	]);

	return { courseId, course, submissions };
};
