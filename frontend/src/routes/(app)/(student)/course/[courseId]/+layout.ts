import { getCourseTree } from '$lib/api/calledAPI';
import type { LayoutLoad } from '../$types';

export const ssr = false;

export const load: LayoutLoad = async ({ params }) => {
	return {
		course_tree: await getCourseTree(Number(params.courseId))
	};
};
