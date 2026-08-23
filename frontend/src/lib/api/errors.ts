import axios from 'axios';

export function getApiErrorMessage(err: unknown, fallback = 'Đã xảy ra lỗi.'): string {
	if (!axios.isAxiosError(err)) return fallback;

	if (err.code === 'ECONNABORTED' || err.code === 'ETIMEDOUT') {
		return 'Máy chủ phản hồi lâu hơn dự kiến, bạn thử lại giúp mình nhé.';
	}

	const data = err.response?.data;
	if (!data) return fallback;
	if (typeof data === 'string') return data;

	if (typeof data.detail === 'string') return data.detail;

	for (const value of Object.values(data)) {
		if (typeof value === 'string') return value;
		if (Array.isArray(value) && typeof value[0] === 'string') return value[0];
	}

	return fallback;
}
