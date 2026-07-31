import { getQuickStats, getTutorCourses } from '$lib/api/calledAPI';
import type { TutorQuickStats } from '$lib/api/types';
import type { PageLoad } from './$types';

export const ssr = false;

// Load dữ liệu cho trang chủ gia sư: danh sách khóa học đang dạy + 3 thẻ thống kê.
export const load: PageLoad = async () => {
	const [courses, stats] = await Promise.all([getTutorCourses(), getQuickStats()]);

	return { courses, stats: stats as TutorQuickStats };
};
