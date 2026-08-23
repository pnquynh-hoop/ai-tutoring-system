import { readSessionUser } from '$lib/server/sessionUser';
import { getRouteByRole } from '$lib/utils/roleRedirect';
import { redirect, type Handle } from '@sveltejs/kit';

export const handle: Handle = async ({ event, resolve }) => {
	event.locals.user = readSessionUser(event.cookies.get('access_token'));

	if (event.url.pathname === '/') {
		const role = event.locals.user?.role;
		redirect(307, role ? getRouteByRole(role) : '/login');
	}
	return resolve(event);
};
