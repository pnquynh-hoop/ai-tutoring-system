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

export type ConfirmTone = 'danger' | 'warning' | 'info';

export interface ConfirmRequest {
	title: string;
	message: string;
	confirmLabel?: string;
	cancelLabel?: string;
	tone?: ConfirmTone;
	acknowledgeOnly?: boolean;
}

export interface ChapterStat {
	id: number;
	title: string;
	total_lessons: number;
	completed_lessons: number;
	score: string | null;
	has_pending_assignment: boolean;
	first_incomplete_lesson_id: number | null;
}

export interface CourseOverview {
	progress: {
		total_lessons: number;
		completed_lessons: number;
		progress_percent: number;
	};
	average_score: number | null;
	pending_assignments_count: number;
}

export interface StudentQuickStats {
	ongoing_courses_count: number;
	total_pending_assignments_count: number;
	streak: number;
	studied_today: boolean;
}

export interface TutorQuickStats {
	teaching_course_count: number;
	total_students_count: number;
	total_pending_submission_count: number;
}
