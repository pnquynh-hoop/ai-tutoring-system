import axios from 'axios';

/**
 * Lấy thông báo lỗi từ response của DRF.
 *
 * DRF trả về `{ "detail": "..." }` cho lỗi quyền/không tìm thấy, hoặc
 * `{ "field": ["..."] }` cho lỗi validate - không bao giờ có key `message`.
 */
export function getApiErrorMessage(err: unknown, fallback = 'Đã xảy ra lỗi.'): string {
	if (!axios.isAxiosError(err)) return fallback;

	// Hết thời gian chờ: không có response nên phải nhận diện qua mã lỗi của axios.
	if (err.code === 'ECONNABORTED' || err.code === 'ETIMEDOUT') {
		return 'Máy chủ phản hồi lâu hơn dự kiến, bạn thử lại giúp mình nhé.';
	}

	const data = err.response?.data;
	if (!data) return fallback;
	if (typeof data === 'string') return data;

	if (typeof data.detail === 'string') return data.detail;

	// Lỗi validate theo field: lấy thông báo đầu tiên đọc được.
	for (const value of Object.values(data)) {
		if (typeof value === 'string') return value;
		if (Array.isArray(value) && typeof value[0] === 'string') return value[0];
	}

	return fallback;
}
