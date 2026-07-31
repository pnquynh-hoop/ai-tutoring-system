import { getCourseTree, getTutorDetailCourse } from '$lib/api/calledAPI';
import type { PageLoad } from './$types';

export const ssr = false;

// Load khóa học + cây chương/bài học cho màn quản lý của gia sư.
export const load: PageLoad = async ({ params }) => {
	const courseId = Number(params.courseId);
	const [course, tree] = await Promise.all([
		getTutorDetailCourse(courseId),
		getCourseTree(courseId)
	]);

	return { courseId, course, tree };
};
