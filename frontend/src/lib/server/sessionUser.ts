import type { Role, SessionUser } from '$lib/api/entities';

function decodePayload(segment: string): Record<string, unknown> {
	const base64 = segment.replace(/-/g, '+').replace(/_/g, '/');
	const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), '=');
	const bytes = Uint8Array.from(atob(padded), (c) => c.charCodeAt(0));
	return JSON.parse(new TextDecoder().decode(bytes));
}

export function readSessionUser(token: string | undefined): SessionUser | null {
	if (!token) return null;

	try {
		const segment = token.split('.')[1];
		if (!segment) return null;

		const claims = decodePayload(segment);

		if (typeof claims.exp === 'number' && claims.exp * 1000 <= Date.now()) return null;

		return {
			id: Number(claims.user_id),
			role: (claims.role as Role) ?? null,
			full_name: (claims.full_name as string) ?? '',
			avatar: (claims.avatar as string) ?? null,
			grade: (claims.grade as string) ?? null
		};
	} catch {
		return null;
	}
}
