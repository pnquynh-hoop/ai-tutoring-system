import type { MeResponse } from "$lib/api/types";

export const auth = $state({
    user: null as MeResponse | null,
});