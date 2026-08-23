import { getListSubmissions } from '$lib/api/calledAPI';
import type { PageLoad } from './$types';

export const ssr = false;

export const load: PageLoad = async () => {
	return { submissions: await getListSubmissions() };
};
