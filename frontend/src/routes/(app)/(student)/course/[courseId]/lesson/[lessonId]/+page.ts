import { getDetailLesson, getListComments } from '$lib/api/calledAPI';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params }) => {
	return {
		lesson: await getDetailLesson(Number(params.lessonId)),
		comments: await getListComments(Number(params.lessonId))
	};
};
