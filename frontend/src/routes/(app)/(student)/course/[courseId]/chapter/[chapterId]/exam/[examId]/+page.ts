import type { QuizDetail } from '$lib/api/entities';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params }) => {
	const quiz: QuizDetail = mockQuiz(params.chapterId);

	return {
		quiz,
		// TODO: lấy từ store auth thật (giống các trang course/lesson đang dùng auth.user)
		user: {
			full_name: 'Học Sinh C Vũ',
			avatar: null as string | null
		}
	};
};

function mockQuiz(id: string): QuizDetail {
	return {
		id: Number(id) || 1,
		title: 'BÀI ÔN TẬP CHƯƠNG SỐ 5. MỆNH ĐỀ QUAN HỆ ĐẦY ĐỦ VÀ RÚT GỌN',
		course_name: 'Tiếng anh 12',
		chapter_title: 'Chương 4: Relative Clauses (Mệnh đề quan hệ)',
		time_limit_seconds: null,
		questions: Array.from({ length: 10 }, (_, i) => ({
			id: i + 1,
			content: `Mệnh đề nào sau đây đúng ngữ pháp mệnh đề quan hệ rút gọn? (câu ${i + 1})`,
			options: [
				{ id: i * 10 + 1, content: 'Đáp án A' },
				{ id: i * 10 + 2, content: 'Đáp án B' },
				{ id: i * 10 + 3, content: 'Đáp án C' },
				{ id: i * 10 + 4, content: 'Đáp án D' }
			]
		}))
	};
}
