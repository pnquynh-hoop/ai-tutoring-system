import { getListQuestions, startAssignment } from '$lib/api/calledAPI';
import type { PageLoad } from './$types';

export const ssr = false;

export const load: PageLoad = async ({ params }) => {
	const assignmentId = Number(params.assignmentId);
	const [attempt, questions] = await Promise.all([
		startAssignment(assignmentId),
		getListQuestions(assignmentId)
	]);

	return { assignmentId, attempt, questions };
};
