import type { Student } from './entities';

export interface LoginRequest {
	username: string;
	password: string;
}

export type MeResponse = Student;

export type Toast = {
	id: number;
	message: string;
	type: 'success' | 'error' | 'info';
};

/** GET /courses/{id}/chapter-stats/ */
export interface ChapterStat {
	id: number;
	title: string;
	order: number;
	total_lessons: number;
	completed_lessons: number;
	score: number | null;
	pending_assignments: number;
	first_incomplete_lesson_id: number | null;
}

/** GET /courses/{id}/overview/ */
export interface CourseOverview {
	progress: {
		total_lessons: number;
		completed_lessons: number;
		progress_percent: number;
	};
	average_score: number | null;
	pending_assignments_count: number;
}

/** GET /courses/statistic/ khi user là học sinh */
export interface StudentQuickStats {
	ongoing_courses_count: number;
	pending_assignments_count: number;
	streak: number;
	studied_today: boolean;
}

/** GET /courses/statistic/ khi user là gia sư */
export interface TutorQuickStats {
	teaching_course_count: number;
	students_count: number;
	pending_submission_count: number;
}
