import type { SessionUser } from '$lib/api/entities';

export const auth = $state({
	user: null as SessionUser | null
});
