import { getCourseTree } from '$lib/api/calledAPI';
import type { LayoutLoad } from './$types';

export const ssr = false;

export const load: LayoutLoad = async ({ params }) => {
	const courseId = Number(params.courseId);
	const tree = await getCourseTree(courseId);

	return { courseId, tree };
};
