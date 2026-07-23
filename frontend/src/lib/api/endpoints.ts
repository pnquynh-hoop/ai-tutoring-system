export const ENDPOINTS = {
	LOGIN: 'users/login/',
	REFRESH: 'users/refresh/',
	LOGOUT: 'users/logout/',
	ME: 'users/me/',
	COURSES: 'courses/',
	STATS: 'statistic/',
	COURSE_DETAIL: (courseId: string | number) => `courses/${courseId}/`,
	COURSE_TREE: (courseId: string | number) => `courses/${courseId}/tree/`,
	LESSONS_DETAIL: (lessonId: string | number) => `lessons/${lessonId}/`,
	COMPLETE_LESSON: (lessonId: string | number) => `lessons/${lessonId}/complete/`,
	COMMENTS: (lessonId: string | number) => `lessons/${lessonId}/comments/`,
	TOGGLE_RIGHT: (commentId: string | number) => `comments/${commentId}/toggle-right/`,
};