import { requireRole } from '$lib/server/requireRole';

// Kiểm tra user role, chặn user truy cập có Role khác Student
export const load = ({ locals }) => {
    requireRole(locals.user?.role, 'Student');
};