import type { CurrentUser } from '$lib/api/entities';

export const auth = $state({
	user: null as CurrentUser | null
});
