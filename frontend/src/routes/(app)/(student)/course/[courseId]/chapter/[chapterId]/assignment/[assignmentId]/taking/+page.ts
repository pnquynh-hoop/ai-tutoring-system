import { getListQuestions, startAssignment } from '$lib/api/calledAPI';
import type { PageLoad } from './$types';

export const ssr = false;

// Mở lượt làm bài ở server trước khi hiện đề: server là nơi giữ mốc thời gian
// và trả về deadline, tránh việc client tự tính giờ.
export const load: PageLoad = async ({ params }) => {
	const assignmentId = Number(params.assignmentId);
	const [attempt, questions] = await Promise.all([
		startAssignment(assignmentId),
		getListQuestions(assignmentId)
	]);

	return { assignmentId, attempt, questions };
};
