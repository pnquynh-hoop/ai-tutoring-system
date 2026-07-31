import { getAcademicLevels, getGrades, getMyProfile } from '$lib/api/calledAPI';
import type { PageLoad } from './$types';

export const ssr = false;

/**
 * Ô chọn khối lớp và học lực phải lấy đúng giá trị hệ thống đang có:
 * khối lớp từ bảng academics.Grade, học lực từ TextChoices của StudentProfile.
 */
export const load: PageLoad = async () => {
	const [me, grades, academicLevels] = await Promise.all([
		getMyProfile(),
		getGrades(),
		getAcademicLevels()
	]);

	return { me, grades, academicLevels };
};
