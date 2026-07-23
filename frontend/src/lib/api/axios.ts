import axios from 'axios';
import { ENDPOINTS } from './endpoints';
import { PUBLIC_BASE_URL } from '$env/static/public';

const api = axios.create({
	withCredentials: true,
	baseURL: PUBLIC_BASE_URL,
	timeout: 10000,
	headers: {
		'Content-Type': 'application/json'
	}
});

let refreshPromise: Promise<unknown> | null = null;

api.interceptors.response.use(
	(response) => response,

	async (error) => {
		const originalRequest = error.config;

		const isUnauthorized = error.response?.status === 401;

		const isRefreshRequest = originalRequest?.url?.includes(ENDPOINTS.REFRESH);
		const isLoginRequest = originalRequest?.url?.includes(ENDPOINTS.LOGIN);

		const alreadyRetried = originalRequest?._retry;

		if (!isUnauthorized || isRefreshRequest || isLoginRequest || alreadyRetried) {
			return Promise.reject(error);
		}

		originalRequest._retry = true;

		try {
			if (!refreshPromise) {
				refreshPromise = api.post(ENDPOINTS.REFRESH).finally(() => {
					refreshPromise = null;
				});
			}

			await refreshPromise;

			return api(originalRequest);
		} catch {
			return Promise.reject(error);
		}
	}
);

export default api;
