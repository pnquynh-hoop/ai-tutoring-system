import type {
	GradeAnswerItem,
	StudentAnswerReview,
	SubmitAnswerItem,
	UserAnswer
} from '$lib/api/entities';

/**
 * Chuyển câu trả lời của học sinh sang đúng cấu trúc backend yêu cầu ở
 * POST /assignments/{id}/submit/.
 */
export function buildAnswerPayload(userAnswers: Record<number, UserAnswer>): SubmitAnswerItem[] {
	return Object.entries(userAnswers).map(([questionId, answer]) =>
		answer.type === 'MULTIPLE_CHOICE'
			? { question_id: Number(questionId), answer_id: answer.answerId }
			: { question_id: Number(questionId), answer_text: answer.text }
	);
}

/** Số câu đã thực sự trả lời (bỏ qua ô text để trống). */
export function countAnswered(userAnswers: Record<number, UserAnswer>): number {
	return Object.values(userAnswers).filter((answer) =>
		answer.type === 'MULTIPLE_CHOICE' ? answer.answerId !== undefined : answer.text.trim() !== ''
	).length;
}

/**
 * Số giây còn lại tính từ deadline do server trả về.
 * Không có deadline nghĩa là bài không giới hạn thời gian.
 */
export function remainingSeconds(deadline: string | null, now: number = Date.now()): number {
	if (!deadline) return 0;
	return Math.max(0, Math.floor((new Date(deadline).getTime() - now) / 1000));
}

/** Câu tự luận chưa chấm là những câu backend trả về `point === null`. */
export function pendingEssayAnswers(answers: StudentAnswerReview[]): StudentAnswerReview[] {
	return answers.filter((answer) => answer.point === null);
}

/**
 * Gom điểm gia sư nhập thành payload chấm bài, bỏ qua câu chưa nhập điểm.
 * Backend chặn điểm vượt trần nên ở đây chỉ lọc dữ liệu chưa hợp lệ.
 */
export function buildGradePayload(
	drafts: Record<number, { point: string; tutor_comment: string }>
): GradeAnswerItem[] {
	return Object.entries(drafts)
		.filter(([, draft]) => draft.point.trim() !== '' && !Number.isNaN(Number(draft.point)))
		.map(([id, draft]) => ({
			id: Number(id),
			point: Number(draft.point),
			tutor_comment: draft.tutor_comment.trim() || null
		}));
}

/** Bài đã chấm xong khi backend trả về score khác null. */
export function isGraded(score: string | null): boolean {
	return score !== null;
}
