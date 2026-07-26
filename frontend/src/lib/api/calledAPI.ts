import api from './axios';
import { ENDPOINTS } from './endpoints';
import type { CommentListResponse, LoginRequest, MeResponse } from './types';

export async function loginApi(data: LoginRequest) {
	const response = await api.post(ENDPOINTS.LOGIN, data);
	return response.data;
}

export async function logoutApi() {
	return await api.post(ENDPOINTS.LOGOUT);
}

export async function getMeApi(cookieHeader?: string): Promise<MeResponse> {
	const res = await api.get<MeResponse>(ENDPOINTS.ME, {
		headers: cookieHeader ? { Cookie: cookieHeader } : undefined
	});
	return res.data;
}

export async function getListCourses() {
	return (await api.get(ENDPOINTS.COURSES)).data;
}

export async function getQuickStats() {
	return (await api.get(ENDPOINTS.STATS)).data;
}

export async function getDetailCourse(courseId: number) {
	return (await api.get(ENDPOINTS.COURSE_DETAIL(courseId))).data;
}

export async function getCourseTree(courseId: number) {
	return (await api.get(ENDPOINTS.COURSE_TREE(courseId))).data;
}

export async function getDetailLesson(lessonId: number) {
	return (await api.get(ENDPOINTS.LESSONS_DETAIL(lessonId))).data;
}

export async function postCompleteLesson(lessonId: number) {
	return (await api.post(ENDPOINTS.COMPLETE_LESSON(lessonId))).data;
}

export async function getListComments(lessonId: number): Promise<CommentListResponse[]> {
	return (await api.get<CommentListResponse[]>(ENDPOINTS.COMMENTS(lessonId))).data;
}

export async function postComment(lessonId: number, content: string, parentId?: number) {
	return (
		await api.post(ENDPOINTS.COMMENTS(lessonId), {
			content,
			...(parentId ? { parent: parentId } : {})
		})
	).data;
}

export async function toggleCommentRight(commentId: number) {
	return (await api.post(ENDPOINTS.TOGGLE_RIGHT(commentId))).data;
}

export async function getCourseOverview(courseId: number) {
	return (await api.get(ENDPOINTS.COURSE_OVERVIEW(courseId))).data;
}

export async function getChapterStats(courseId: number) {
	return (await api.get(ENDPOINTS.CHAPTER_STATS(courseId))).data;
}

