import { getCourseTree, getListCourses } from '$lib/api/calledAPI';
import type { PageLoad } from './$types';

export const ssr = false;

// Trợ lý AI hỏi đáp theo khóa học: cần danh sách khóa học đang học và cây
// chương/bài của khóa đầu tiên để chọn ngữ cảnh gửi kèm cho backend.
export const load: PageLoad = async () => {
	const courses = await getListCourses();
	const firstTree = courses.length ? await getCourseTree(courses[0].id) : null;

	return { courses, firstTree };
};
