import { beforeEach, describe, expect, it, vi } from 'vitest';

const get = vi.fn();
const post = vi.fn();
const patch = vi.fn();
const del = vi.fn();

vi.mock('./axios', () => ({
	default: {
		get: (...args: unknown[]) => get(...args),
		post: (...args: unknown[]) => post(...args),
		patch: (...args: unknown[]) => patch(...args),
		delete: (...args: unknown[]) => del(...args)
	}
}));

const {
	createChapter,
	createLesson,
	createQuestion,
	createResource,
	getLessonResources,
	getListSubmissions,
	getTutorQuestions,
	gradeSubmission,
	postComment,
	startAssignment,
	submitAssignment,
	toggleCommentRight,
	updateMyProfile
} = await import('./calledAPI');

beforeEach(() => {
	get.mockReset().mockResolvedValue({ data: [] });
	post.mockReset().mockResolvedValue({ data: {} });
	patch.mockReset().mockResolvedValue({ data: {} });
	del.mockReset().mockResolvedValue({ data: null });
});

describe('cây khóa học', () => {
	it('tạo chương gửi đúng course/title/order', async () => {
		await createChapter({ course: 3, title: 'Chương 1', order: 1 });

		expect(post).toHaveBeenCalledWith('chapters/', { course: 3, title: 'Chương 1', order: 1 });
	});

	it('tạo bài học gắn vào chapter chứ không phải course', async () => {
		await createLesson({ chapter: 9, title: 'Bài 1', order: 2 });

		expect(post).toHaveBeenCalledWith('lessons/', { chapter: 9, title: 'Bài 1', order: 2 });
	});

	it('list tài nguyên gọi qua đường dẫn lồng của bài học', async () => {
		await getLessonResources(12);

		expect(get).toHaveBeenCalledWith('lessons/12/resources/');
	});

	it('tạo tài nguyên gửi kèm lesson', async () => {
		await createResource({ lesson: 12, title: 'Video', resource_type: 'VIDEO_URL' });

		expect(post).toHaveBeenCalledWith('resources/', {
			lesson: 12,
			title: 'Video',
			resource_type: 'VIDEO_URL'
		});
	});
});

describe('bình luận', () => {
	it('không gửi created_by vì backend tự gán từ user của request', async () => {
		await postComment(5, 'Em chưa hiểu bài');

		expect(post).toHaveBeenCalledWith('lessons/5/comments/', { content: 'Em chưa hiểu bài' });
	});

	it('gửi parent khi trả lời một bình luận', async () => {
		await postComment(5, 'Trả lời', 77);

		expect(post).toHaveBeenCalledWith('lessons/5/comments/', {
			content: 'Trả lời',
			parent: 77
		});
	});

	it('toggle đánh dấu đúng dùng POST đúng như route backend', async () => {
		await toggleCommentRight(42);

		expect(post).toHaveBeenCalledWith('comments/42/toggle-mark-right/');
	});
});

describe('làm bài và nộp bài', () => {
	it('mở lượt làm bài bằng POST start', async () => {
		await startAssignment(8);

		expect(post).toHaveBeenCalledWith('assignments/8/start/');
	});

	it('nộp bài bọc danh sách trong khoá answers', async () => {
		await submitAssignment(8, [{ question_id: 1, answer_id: 2 }]);

		expect(post).toHaveBeenCalledWith('assignments/8/submit/', {
			answers: [{ question_id: 1, answer_id: 2 }]
		});
	});

	it('học sinh lấy bài nộp của mình không cần tham số', async () => {
		await getListSubmissions();

		expect(get).toHaveBeenCalledWith('submissions/', { params: undefined });
	});

	it('gia sư lọc bài nộp theo khóa học', async () => {
		await getListSubmissions({ course: 4 });

		expect(get).toHaveBeenCalledWith('submissions/', { params: { course: 4 } });
	});
});

describe('soạn câu hỏi và chấm bài', () => {
	it('lấy câu hỏi cho gia sư qua route lồng theo bài tập', async () => {
		await getTutorQuestions(3);

		expect(get).toHaveBeenCalledWith('assignments/3/questions/');
	});

	it('tạo câu hỏi gửi kèm mảng answers lồng bên trong', async () => {
		await createQuestion({
			assignment: 3,
			content: '2 + 2 = ?',
			question_type: 'MULTIPLE_CHOICE',
			explanation: 'Cộng hai số',
			answers: [
				{ content: '4', is_correct: true },
				{ content: '5', is_correct: false }
			]
		});

		expect(post).toHaveBeenCalledWith(
			'questions/',
			expect.objectContaining({ assignment: 3, answers: expect.any(Array) })
		);
	});

	it('chấm bài dùng PATCH vào route grade', async () => {
		await gradeSubmission(15, [{ id: 1, point: 4.5, tutor_comment: 'Khá' }]);

		expect(patch).toHaveBeenCalledWith('submissions/15/grade/', {
			answers: [{ id: 1, point: 4.5, tutor_comment: 'Khá' }]
		});
	});
});

describe('trợ lý AI', () => {
	it('gửi course_id, bỏ lesson_id khi hỏi theo cả khóa học', async () => {
		const { askAI } = await import('./calledAPI');
		await askAI('Bài này nói gì?', 3);

		expect(post).toHaveBeenCalledWith(
			'rag/ask/',
			{ question: 'Bài này nói gì?', course_id: 3 },
			expect.objectContaining({ timeout: expect.any(Number) })
		);
	});

	it('gửi kèm lesson_id khi đang ở trong một bài học', async () => {
		const { askAI } = await import('./calledAPI');
		await askAI('Giải thích lại', 3, 12);

		expect(post).toHaveBeenCalledWith(
			'rag/ask/',
			{ question: 'Giải thích lại', course_id: 3, lesson_id: 12 },
			expect.objectContaining({ timeout: expect.any(Number) })
		);
	});

	it('dùng timeout dài hơn mặc định 10s vì gọi LLM mất 15-25 giây', async () => {
		const { askAI } = await import('./calledAPI');
		await askAI('Câu hỏi', 1);

		const config = post.mock.calls[0][2] as { timeout: number };
		expect(config.timeout).toBeGreaterThan(10_000);
	});
});

describe('hồ sơ cá nhân', () => {
	it('cập nhật hồ sơ bằng PATCH vào users/me/', async () => {
		await updateMyProfile({ first_name: 'Quỳnh' });

		expect(patch).toHaveBeenCalledWith('users/me/', { first_name: 'Quỳnh' });
	});
});
