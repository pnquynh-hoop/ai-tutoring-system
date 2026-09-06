import { getDetailAssignment, getTutorQuestions } from '$lib/api/calledAPI';
import type { AssignmentDetail, TutorQuestion } from '$lib/api/entities';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ url, parent }) => {
	const { tree } = await parent();

	const requestedChapterId = Number(url.searchParams.get('chapter'));
	const chapter =
		tree.chapters.find((c) => c.id === requestedChapterId) ?? tree.chapters[0] ?? null;

	let assignment: AssignmentDetail | null = null;
	let questions: TutorQuestion[] = [];

	if (chapter?.assignment) {
		assignment = await getDetailAssignment(chapter.assignment);
		questions = await getTutorQuestions(chapter.assignment);
	}

	return { chapter, assignment, questions };
};
