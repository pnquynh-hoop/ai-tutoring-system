import { readSessionUser } from '$lib/server/sessionUser';
import { redirect, type Handle } from '@sveltejs/kit';

// Là cổng chặn cho toàn server frontend. Thông tin user đọc thẳng từ access
// token nên mỗi lần chuyển trang không còn phải gọi /me sang Django nữa.
export const handle: Handle = async ({ event, resolve }) => {
	event.locals.user = readSessionUser(event.cookies.get('access_token'));

	if (event.url.pathname === '/') {
		redirect(307, event.locals.user ? '/stu-dashboard' : '/login');
	}
	return resolve(event);
};
