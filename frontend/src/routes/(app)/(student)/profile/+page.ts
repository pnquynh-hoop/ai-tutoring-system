import { getAcademicLevels, getGrades, getMyProfile } from '$lib/api/calledAPI';
import type { PageLoad } from './$types';

export const ssr = false;

export const load: PageLoad = async () => {
	const [me, grades, academicLevels] = await Promise.all([
		getMyProfile(),
		getGrades(),
		getAcademicLevels()
	]);

	return { me, grades, academicLevels };
};
