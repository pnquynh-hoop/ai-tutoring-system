import { redirect } from '@sveltejs/kit';

// Kiểm tra user đã đăng nhập mới được truy cập vào các route trong (app)
export const load = ({ locals, url }) => {
	if (!locals.user) {
		throw redirect(303, `/login?redirectTo=${url.pathname}`);
	}
};
