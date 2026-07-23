import { getDetailCourse } from '$lib/api/calledAPI';
import type { PageLoad } from './$types';

export const ssr = false;

// Load dữ liệu trước cho trang chi tiết khóa học
export const load: PageLoad = async ({ params }) => {
	return {
		course: await getDetailCourse(Number(params.courseId))
	};
};
