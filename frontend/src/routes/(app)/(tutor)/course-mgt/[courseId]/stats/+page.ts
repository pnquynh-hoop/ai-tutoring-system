import { getCourseStats } from '$lib/api/calledAPI';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params }) => {
	return {
		stats: await getCourseStats(Number(params.courseId))
	};
};
