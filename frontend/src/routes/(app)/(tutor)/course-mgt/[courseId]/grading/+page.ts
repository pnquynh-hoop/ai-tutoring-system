import { getListSubmissions } from '$lib/api/calledAPI';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params }) => {
	return {
		submissions: await getListSubmissions({ course: Number(params.courseId) })
	};
};
