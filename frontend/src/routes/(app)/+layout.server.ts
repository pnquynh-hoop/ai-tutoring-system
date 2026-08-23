import { redirect } from '@sveltejs/kit';

export const load = ({ locals, url }) => {
	if (!locals.user) {
		throw redirect(303, `/login?redirectTo=${url.pathname}`);
	}
};
