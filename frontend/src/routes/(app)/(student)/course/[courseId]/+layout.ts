import { getCourseTree } from '$lib/api/calledAPI';
import type { LayoutLoad } from '../$types';

export const ssr = false;

// Load dữ liệu trước cho những trang trong /course (cụ thể là Sidebar khóa học)
export const load: LayoutLoad = async ({ params }) => {
	return {
		course_tree: await getCourseTree(Number(params.courseId))
	};
};
