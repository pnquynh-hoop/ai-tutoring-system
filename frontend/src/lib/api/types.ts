import type { Comment, Course, CourseTree, Student } from './entities';

export interface LoginRequest {
	username: string;
	password: string;
}

export interface LoginResponse {
	access: string;
	refresh: string;
}

export type CourseListResponse = Course[];

export type CourseDetailResponse = CourseTree;

export type MeResponse = Student;

export type ProgressMap = Record<string, { is_completed: boolean }>;

export type Toast = {
	id: number;
	message: string;
	type: 'success' | 'error' | 'info';
};

export type CommentListResponse = Comment;

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

export interface QuizAnswerResult {
	question_id: number;
	selected_option_id: number | null;
	correct_option_id: number;
	is_correct: boolean;
	explanation?: string | null;
}

export interface QuizResult {
	score: number;
	total: number;
	duration_seconds: number;
	answers: QuizAnswerResult[];
}

export type QuestionCellStatus = 'unanswered' | 'answered' | 'correct' | 'incorrect';

export interface QuestionCell {
	id: number;
	label: number;
	status: QuestionCellStatus;
}
