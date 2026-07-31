import type { Role } from '$lib/api/entities';
import { error } from '@sveltejs/kit';

export function requireRole(userRole: Role | null | undefined, allowed: Role | Role[]) {
	const allowedRoles = Array.isArray(allowed) ? allowed : [allowed];

	if (!userRole || !allowedRoles.includes(userRole)) {
		throw error(403, 'Bạn không có quyền truy cập vào trang này!');
	}
}
