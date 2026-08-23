import { getCourseTree, getListCourses } from '$lib/api/calledAPI';
import type { PageLoad } from './$types';

export const ssr = false;

export const load: PageLoad = async () => {
	const courses = await getListCourses();
	const firstTree = courses.length ? await getCourseTree(courses[0].id) : null;

	return { courses, firstTree };
};
