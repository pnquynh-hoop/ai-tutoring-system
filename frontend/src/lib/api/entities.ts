export type Role = 'Student' | 'Tutor';
export type ResourceType = 'VIDEO_URL' | 'PDF_FILE' | string;

export interface Course {
	id: number;
	name: string;
	tutor_name: string;
	progress: number;
}

export interface CourseDetail {
	id: number;
	name: string;
	tutor_name: string;
	description: string;
	subject_name: string;
	grade: number;
}

export interface Lesson {
	id: number;
	title: string;
	is_completed: boolean;
}

export interface Chapter {
    id: number;
    title: string;
    lessons: Lesson[];
}

export interface CourseTree extends Course {
    chapters: Chapter[];
}

export interface Student {
	role: Role;
	full_name: string;
	avatar: string;
	grade: string;
}

interface LessonResource {
	id: number;
	title: string;
	resource_type: ResourceType;
	content: string | null;
	file_url: string | null;
	video_url: string | null;
}

export interface LessonDetail {
	id: number;
	title: string;
	resources: LessonResource[];
}

export interface CommentUser {
	id: number;
	full_name: string;
	avatar: string | null;
}

export interface Comment {
	id: number;
	content: string;
	is_right: boolean;
	created_by: CommentUser;
	parent: number | null;
	created_at: string;
	lesson: number;
	is_active: boolean;
}
