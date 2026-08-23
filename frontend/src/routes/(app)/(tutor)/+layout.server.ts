import { requireRole } from '$lib/server/requireRole';

export const load = ({ locals }) => {
	requireRole(locals.user?.role, 'Tutor');
};
