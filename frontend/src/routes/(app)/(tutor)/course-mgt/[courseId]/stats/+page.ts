import { getCourseStats, getTutorDetailCourse } from '$lib/api/calledAPI';
import type { PageLoad } from './$types';

export const ssr = false;

export const load: PageLoad = async ({ params }) => {
	const courseId = Number(params.courseId);
	const [course, stats] = await Promise.all([
		getTutorDetailCourse(courseId),
		getCourseStats(courseId)
	]);

	return { courseId, course, stats };
};
