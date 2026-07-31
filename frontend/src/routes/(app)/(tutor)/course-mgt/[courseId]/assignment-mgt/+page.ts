import { getCourseTree, getDetailAssignment, getTutorQuestions } from '$lib/api/calledAPI';
import type { AssignmentDetail, TutorQuestion } from '$lib/api/entities';
import type { PageLoad } from './$types';

export const ssr = false;

/**
 * Bài tập gắn 1-1 với chương nên trang này luôn làm việc theo một chương cụ thể
 * (?chapter=<id>). Chương chưa có bài tập thì assignment = null.
 */
export const load: PageLoad = async ({ params, url }) => {
	const courseId = Number(params.courseId);
	const tree = await getCourseTree(courseId);

	const requestedChapterId = Number(url.searchParams.get('chapter'));
	const chapter =
		tree.chapters.find((c) => c.id === requestedChapterId) ?? tree.chapters[0] ?? null;

	let assignment: AssignmentDetail | null = null;
	let questions: TutorQuestion[] = [];

	if (chapter?.assignment) {
		assignment = await getDetailAssignment(chapter.assignment);
		questions = await getTutorQuestions(chapter.assignment);
	}

	return { courseId, tree, chapter, assignment, questions };
};
