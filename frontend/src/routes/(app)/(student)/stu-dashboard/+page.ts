import { getListCourses, getQuickStats } from '$lib/api/calledAPI';
import type { PageLoad } from './$types';

export const ssr = false;

// Load dữ liệu cho trang student dashboard
export const load: PageLoad = async () => {
	const [courses, stats] = await Promise.all([getListCourses(), getQuickStats()]);

	return { courses, stats };
};
