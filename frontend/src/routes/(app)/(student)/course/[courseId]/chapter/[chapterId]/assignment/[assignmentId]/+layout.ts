import { getDetailAssignment } from '$lib/api/calledAPI';
import type { LayoutLoad } from './$types';

export const ssr = false;

export const load: LayoutLoad = async ({ params }) => {
	const res = await getDetailAssignment(Number(params.assignmentId));

	return {
		assignment: {
			id: res.id,
			title: res.title,
			timeLimitMinutes: res.time_limit_minutes,
			dueDate: res.due_date,
			totalQuestions: res.total_questions,
			questionTypes: res.question_types,
			maxAttempts: res.max_attempts,
			attemptsUsed: res.attempts_used
		}
	};
};
