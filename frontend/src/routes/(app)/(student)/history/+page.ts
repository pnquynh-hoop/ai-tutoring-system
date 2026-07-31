import { getListSubmissions } from '$lib/api/calledAPI';
import type { PageLoad } from './$types';

export const ssr = false;

// Lịch sử làm bài của chính học sinh: backend đã lọc theo user của request.
export const load: PageLoad = async () => {
	return { submissions: await getListSubmissions() };
};
