import type {
	GradeAnswerItem,
	StudentAnswerReview,
	SubmitAnswerItem,
	UserAnswer
} from '$lib/api/entities';

export function buildAnswerPayload(userAnswers: Record<number, UserAnswer>): SubmitAnswerItem[] {
	return Object.entries(userAnswers).map(([questionId, answer]) =>
		answer.type === 'MULTIPLE_CHOICE'
			? { question_id: Number(questionId), answer_id: answer.answerId }
			: { question_id: Number(questionId), answer_text: answer.text }
	);
}

export function countAnswered(userAnswers: Record<number, UserAnswer>): number {
	return Object.values(userAnswers).filter((answer) =>
		answer.type === 'MULTIPLE_CHOICE' ? answer.answerId !== undefined : answer.text.trim() !== ''
	).length;
}

export function remainingSeconds(deadline: string | null, now: number = Date.now()): number {
	if (!deadline) return 0;
	return Math.max(0, Math.floor((new Date(deadline).getTime() - now) / 1000));
}

export function pendingEssayAnswers(answers: StudentAnswerReview[]): StudentAnswerReview[] {
	return answers.filter((answer) => answer.point === null);
}

export function buildGradePayload(
	drafts: Record<number, { point: number | null; tutor_comment: string }>
): GradeAnswerItem[] {
	const items: GradeAnswerItem[] = [];

	for (const [id, draft] of Object.entries(drafts)) {
		const point = draft.point;
		if (point === null || Number.isNaN(point)) continue;

		items.push({
			id: Number(id),
			point,
			tutor_comment: draft.tutor_comment.trim() || null
		});
	}

	return items;
}

export function isGraded(score: string | null): boolean {
	return score !== null;
}

const ANSWER_DRAFT_PREFIX = 'assignment-answer-draft-';

function answerDraftKey(attemptId: number): string {
	return `${ANSWER_DRAFT_PREFIX}${attemptId}`;
}

export function loadAnswerDraft(attemptId: number): Record<number, UserAnswer> {
	try {
		const stored = localStorage.getItem(answerDraftKey(attemptId));
		return stored ? JSON.parse(stored) : {};
	} catch {
		return {};
	}
}

export function saveAnswerDraft(
	attemptId: number,
	userAnswers: Record<number, UserAnswer>
): boolean {
	try {
		localStorage.setItem(answerDraftKey(attemptId), JSON.stringify(userAnswers));
		return true;
	} catch {
		return false;
	}
}

export function clearAnswerDraft(attemptId: number): boolean {
	try {
		localStorage.removeItem(answerDraftKey(attemptId));
		return true;
	} catch {
		return false;
	}
}
