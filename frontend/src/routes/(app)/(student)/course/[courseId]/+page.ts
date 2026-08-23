import { getChapterStats, getCourseOverview, getDetailCourse } from '$lib/api/calledAPI';
import type { PageLoad } from './$types';

export const ssr = false;

export const load: PageLoad = async ({ params }) => {
	return {
		course: await getDetailCourse(Number(params.courseId)),
		course_overview: await getCourseOverview(Number(params.courseId)),
		chapter_stats: await getChapterStats(Number(params.courseId))
	};
};
