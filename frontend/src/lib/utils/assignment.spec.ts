import { describe, expect, it } from 'vitest';
import type { StudentAnswerReview, UserAnswer } from '$lib/api/entities';
import {
	buildAnswerPayload,
	buildGradePayload,
	countAnswered,
	isGraded,
	pendingEssayAnswers,
	remainingSeconds
} from './assignment';

function reviewAnswer(overrides: Partial<StudentAnswerReview>): StudentAnswerReview {
	return {
		id: 1,
		question: 1,
		question_content: 'Câu hỏi',
		question_type: 'ESSAY',
		explanation: '',
		answer: null,
		selected_answer: null,
		correct_answer: null,
		answer_text: null,
		point: null,
		tutor_comment: null,
		is_correct: null,
		...overrides
	};
}

describe('buildAnswerPayload', () => {
	it('gửi answer_id cho câu trắc nghiệm và answer_text cho câu tự luận', () => {
		const answers: Record<number, UserAnswer> = {
			10: { type: 'MULTIPLE_CHOICE', answerId: 99 },
			11: { type: 'ESSAY', text: 'Bài làm của em' }
		};

		expect(buildAnswerPayload(answers)).toEqual([
			{ question_id: 10, answer_id: 99 },
			{ question_id: 11, answer_text: 'Bài làm của em' }
		]);
	});

	it('trả về mảng rỗng khi chưa trả lời câu nào', () => {
		expect(buildAnswerPayload({})).toEqual([]);
	});

	it('chuyển khoá của object thành số vì backend nhận question_id kiểu số', () => {
		const payload = buildAnswerPayload({ 7: { type: 'FILL_IN_BLANK', text: 'Hà Nội' } });

		expect(payload[0].question_id).toBe(7);
		expect(typeof payload[0].question_id).toBe('number');
	});
});

describe('countAnswered', () => {
	it('không tính câu chỉ có khoảng trắng', () => {
		const answers: Record<number, UserAnswer> = {
			1: { type: 'MULTIPLE_CHOICE', answerId: 5 },
			2: { type: 'ESSAY', text: '   ' },
			3: { type: 'FILL_IN_BLANK', text: 'Đáp án' }
		};

		expect(countAnswered(answers)).toBe(2);
	});
});

describe('remainingSeconds', () => {
	const now = new Date('2026-07-29T10:00:00Z').getTime();

	it('tính số giây còn lại từ deadline của server', () => {
		expect(remainingSeconds('2026-07-29T10:30:00Z', now)).toBe(1800);
	});

	it('trả về 0 khi bài không giới hạn thời gian', () => {
		expect(remainingSeconds(null, now)).toBe(0);
	});

	it('không trả về số âm khi đã quá hạn', () => {
		expect(remainingSeconds('2026-07-29T09:00:00Z', now)).toBe(0);
	});
});

describe('pendingEssayAnswers', () => {
	it('chỉ lấy câu backend chưa chấm (point === null)', () => {
		const answers = [
			reviewAnswer({ id: 1, point: '5.00' }),
			reviewAnswer({ id: 2, point: null }),
			reviewAnswer({ id: 3, point: '0.00' })
		];

		expect(pendingEssayAnswers(answers).map((a) => a.id)).toEqual([2]);
	});
});

describe('buildGradePayload', () => {
	it('bỏ qua câu gia sư chưa nhập điểm', () => {
		const payload = buildGradePayload({
			1: { point: '4.5', tutor_comment: 'Tốt' },
			2: { point: '', tutor_comment: 'Chưa chấm' }
		});

		expect(payload).toEqual([{ id: 1, point: 4.5, tutor_comment: 'Tốt' }]);
	});

	it('bỏ qua giá trị không phải số', () => {
		expect(buildGradePayload({ 1: { point: 'mười', tutor_comment: '' } })).toEqual([]);
	});

	it('gửi tutor_comment là null khi để trống', () => {
		const payload = buildGradePayload({ 3: { point: '0', tutor_comment: '  ' } });

		expect(payload).toEqual([{ id: 3, point: 0, tutor_comment: null }]);
	});
});

describe('isGraded', () => {
	it('score null nghĩa là bài còn chờ gia sư chấm', () => {
		expect(isGraded(null)).toBe(false);
		expect(isGraded('0.0')).toBe(true);
	});
});
