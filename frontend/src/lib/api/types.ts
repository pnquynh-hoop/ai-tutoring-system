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
