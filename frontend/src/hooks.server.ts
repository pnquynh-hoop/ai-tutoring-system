import { getMeApi } from '$lib/api/calledAPI';
import type { Handle } from '@sveltejs/kit';

// Là cổng chặn cho toàn server frontend, chặn từng request kiểm tra trạng thái đăng nhập, lấy thông tin user lưu vào locals
export const handle: Handle = async ({ event, resolve }) => {
	const token = event.cookies.get('access_token');

	if (token) {
		try {
			const cookieHeader = event.request.headers.get('cookie') ?? undefined;
			const res = await getMeApi(cookieHeader);
			event.locals.user = res;
		} catch {
			event.locals.user = null;
			event.cookies.delete('access_token', { path: '/' });
		}
	} else {
		event.locals.user = null;
	}
	return resolve(event);
};
