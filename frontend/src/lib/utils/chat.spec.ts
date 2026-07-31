import { describe, expect, it } from 'vitest';
import { formatSourceLabel, resolveChatContext } from './chat';

describe('resolveChatContext', () => {
	it('lấy khóa học và bài học từ route khi đang ở trong bài học', () => {
		expect(resolveChatContext({ courseId: '3', lessonId: '12' })).toEqual({
			courseId: 3,
			lessonId: 12
		});
	});

	it('chỉ có khóa học khi route không tới bài học', () => {
		expect(resolveChatContext({ courseId: '3' })).toEqual({ courseId: 3, lessonId: null });
	});

	it('dùng khóa học người dùng chọn khi route không có courseId', () => {
		expect(resolveChatContext({}, 7)).toEqual({ courseId: 7, lessonId: null });
	});

	it('route được ưu tiên hơn lựa chọn thủ công', () => {
		expect(resolveChatContext({ courseId: '3' }, 7).courseId).toBe(3);
	});

	it('bỏ qua lessonId lạc lõng khi không có courseId', () => {
		expect(resolveChatContext({ lessonId: '12' }, 7)).toEqual({ courseId: 7, lessonId: null });
	});

	it('trả về null khi chưa có ngữ cảnh nào', () => {
		expect(resolveChatContext({})).toEqual({ courseId: null, lessonId: null });
	});
});

describe('formatSourceLabel', () => {
	it('cộng 1 vào số trang vì PyMuPDF đánh số từ 0', () => {
		expect(formatSourceLabel({ title: 'SGK 12 clean', page: 41 })).toBe('SGK 12 clean · trang 42');
	});

	it('chỉ hiện tên với nguồn không phân trang', () => {
		expect(formatSourceLabel({ title: 'Bài 1: Mệnh đề quan hệ', page: null })).toBe(
			'Bài 1: Mệnh đề quan hệ'
		);
	});

	it('trang 0 vẫn hiển thị là trang 1', () => {
		expect(formatSourceLabel({ title: 'SGK', page: 0 })).toBe('SGK · trang 1');
	});
});
