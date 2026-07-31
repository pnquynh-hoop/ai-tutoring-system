import { AxiosError, AxiosHeaders } from 'axios';
import { describe, expect, it } from 'vitest';
import { getApiErrorMessage } from './errors';

function axiosErrorWith(data: unknown, status = 400): AxiosError {
	const error = new AxiosError('Request failed');
	error.response = {
		data,
		status,
		statusText: '',
		headers: new AxiosHeaders(),
		config: { headers: new AxiosHeaders() }
	};
	return error;
}

describe('getApiErrorMessage', () => {
	it('đọc key detail của DRF (lỗi quyền, không tìm thấy)', () => {
		const err = axiosErrorWith({ detail: 'Bạn không có quyền truy cập.' }, 403);

		expect(getApiErrorMessage(err)).toBe('Bạn không có quyền truy cập.');
	});

	it('đọc lỗi validate theo field dạng mảng', () => {
		const err = axiosErrorWith({ answers: ['Mỗi câu hỏi chỉ được trả lời một lần.'] });

		expect(getApiErrorMessage(err)).toBe('Mỗi câu hỏi chỉ được trả lời một lần.');
	});

	it('đọc lỗi validate dạng chuỗi', () => {
		const err = axiosErrorWith({ non_field_errors: 'Bài tập đã hết hạn nộp.' });

		expect(getApiErrorMessage(err)).toBe('Bài tập đã hết hạn nộp.');
	});

	it('trả về nguyên văn khi backend trả chuỗi', () => {
		expect(getApiErrorMessage(axiosErrorWith('Lỗi máy chủ', 500))).toBe('Lỗi máy chủ');
	});

	it('dùng fallback khi lỗi không phải từ axios', () => {
		expect(getApiErrorMessage(new Error('boom'), 'Không tải được.')).toBe('Không tải được.');
	});

	it('dùng fallback khi response không có body', () => {
		const err = new AxiosError('Network Error');

		expect(getApiErrorMessage(err, 'Mất kết nối.')).toBe('Mất kết nối.');
	});

	it('báo rõ khi request bị huỷ do hết thời gian chờ', () => {
		const err = new AxiosError('timeout of 10000ms exceeded');
		err.code = 'ECONNABORTED';

		expect(getApiErrorMessage(err)).toBe(
			'Máy chủ phản hồi lâu hơn dự kiến, bạn thử lại giúp mình nhé.'
		);
	});

	it('không nhận key message vì DRF không dùng key này', () => {
		const err = axiosErrorWith({ message: 'sai key' });

		// Rơi vào nhánh quét field nên vẫn lấy được chuỗi, nhưng phải là chuỗi thật
		expect(getApiErrorMessage(err)).toBe('sai key');
	});
});
