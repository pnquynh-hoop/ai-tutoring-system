import type { Role, SessionUser } from '$lib/api/entities';

/** Giải mã phần payload của JWT. Tách riêng vì atob trả về latin1, phải đi qua
 * TextDecoder mới ra đúng tiếng Việt trong claim như "Lớp 12". */
function decodePayload(segment: string): Record<string, unknown> {
	const base64 = segment.replace(/-/g, '+').replace(/_/g, '/');
	const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), '=');
	const bytes = Uint8Array.from(atob(padded), (c) => c.charCodeAt(0));
	return JSON.parse(new TextDecoder().decode(bytes));
}

/**
 * Lấy thông tin hiển thị và điều hướng thẳng từ access token, không gọi /me.
 *
 * Cố ý KHÔNG xác minh chữ ký: đây chỉ là dữ liệu để dựng giao diện. Quyền thật
 * do Django kiểm lại trên từng lời gọi API, nên token giả cũng chỉ mở ra được
 * một trang rỗng.
 */
export function readSessionUser(token: string | undefined): SessionUser | null {
	if (!token) return null;

	try {
		const segment = token.split('.')[1];
		if (!segment) return null;

		const claims = decodePayload(segment);

		// Token hết hạn thì coi như chưa đăng nhập, để guard đẩy về /login.
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
