export const ENDPOINTS = {
	LOGIN: 'users/login/',
	REFRESH: 'users/refresh/',
	LOGOUT: 'users/logout/',
	ME: 'users/me/',

	COURSES: 'courses/',
	STATS: 'courses/statistic/',
	COURSE_DETAIL: (courseId: string | number) => `courses/${courseId}/`,
	COURSE_TREE: (courseId: string | number) => `courses/${courseId}/tree/`,
	COURSE_OVERVIEW: (courseId: string | number) => `courses/${courseId}/overview/`,
	CHAPTER_STATS: (courseId: string | number) => `courses/${courseId}/chapter-stats/`,

	CHAPTERS: 'chapters/',
	CHAPTER_DETAIL: (chapterId: string | number) => `chapters/${chapterId}/`,
	PUBLISH_CHAPTER: (chapterId: string | number) => `chapters/${chapterId}/publish/`,

	LESSONS: 'lessons/',
	LESSONS_DETAIL: (lessonId: string | number) => `lessons/${lessonId}/`,
	PUBLISH_LESSON: (lessonId: string | number) => `lessons/${lessonId}/publish/`,
	COMPLETE_LESSON: (lessonId: string | number) => `lessons/${lessonId}/complete/`,
	COMMENTS: (lessonId: string | number) => `lessons/${lessonId}/comments/`,
	TOGGLE_RIGHT: (commentId: string | number) => `comments/${commentId}/toggle-mark-right/`,

	RESOURCES: 'resources/',
	RESOURCES_BY_LESSON: (lessonId: string | number) => `lessons/${lessonId}/resources/`,
	RESOURCE_DETAIL: (resourceId: string | number) => `resources/${resourceId}/`,
	PUBLISH_RESOURCE: (resourceId: string | number) => `resources/${resourceId}/publish/`,

	COURSE_STATS: (courseId: string | number) => `courses/${courseId}/stats/`,

	ASSIGNMENTS: 'assignments/',
	ASSIGNMENT_DETAIL: (assignmentId: string | number) => `assignments/${assignmentId}/`,
	PUBLISH_ASSIGNMENT: (assignmentId: string | number) => `assignments/${assignmentId}/publish/`,
	QUESTIONS: (assignmentId: string | number) => `assignments/${assignmentId}/questions/`,
	START_ASSIGNMENT: (assignmentId: string | number) => `assignments/${assignmentId}/start/`,
	SUBMIT_ASSIGNMENT: (assignmentId: string | number) => `assignments/${assignmentId}/submit/`,
	SUBMISSIONS: 'submissions/',
	SUBMISSION_DETAIL: (submissionId: string | number) => `submissions/${submissionId}/`,
	GRADE_SUBMISSION: (submissionId: string | number) => `submissions/${submissionId}/grade/`,

	QUESTIONS_ADMIN: 'questions/',
	QUESTION_DETAIL: (questionId: string | number) => `questions/${questionId}/`,

	CHANGE_PASSWORD: 'users/change-password/',
	ACADEMIC_LEVELS: 'users/academic-levels/',

	GRADES: 'grades/',

	RAG_ASK: 'rag/ask/',
	RAG_GENERATE_EXERCISES: 'rag/generate-exercises/'
};
