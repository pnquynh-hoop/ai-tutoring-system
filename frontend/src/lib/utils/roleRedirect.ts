import type { Role } from "$lib/api/entities";

const ROLE_ROUTES: Record<Role, string> = {
    Student: '/stu-dashboard',
    Tutor: '/tutor-dashboard',
};

export function  getRouteByRole(role: Role): string {
    return ROLE_ROUTES[role] ?? '/login';
}             