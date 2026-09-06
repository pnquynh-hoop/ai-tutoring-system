import { getMeApi } from '$lib/api/calledAPI';
import type { CurrentUser } from '$lib/api/entities';

export const load = async ({ locals, request }) => {
	if (!locals.user) return { user: null };

	const fallback: CurrentUser = { ...locals.user, full_name: '', avatar: null, grade: null };

	try {
		const me = await getMeApi(request.headers.get('cookie') ?? undefined);

		const user: CurrentUser = {
			...locals.user,
			full_name: me.full_name,
			avatar: me.avatar,
			grade: me.student_profile?.grade_name ?? null
		};
		return { user };
	} catch {
		return { user: fallback };
	}
};
