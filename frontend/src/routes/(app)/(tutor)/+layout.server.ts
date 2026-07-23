import { requireRole } from '$lib/server/requireRole';

// Kiểm tra role, chỉ cho phép người dùng là Tutor truy cập vào các route bên trong (tutor)
export const load = ({ locals }) => {
    requireRole(locals.user?.role, 'Tutor');
};