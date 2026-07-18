import axios from "axios";
import { ENDPOINTS } from "./endpoints";

const BASE_URL = 'http://localhost:8000/api/v1/';

const api = axios.create({
    withCredentials: true,
    baseURL: BASE_URL,
    timeout: 10000,
    headers: {
        "Content-Type": "application/json",
    },
});

let isRefreshing = false;
let refreshPromise: Promise<any> | null = null;

api.interceptors.response.use(
    (response) => response,

    async (error) => {
        const originalRequest = error.config;

        if (
            error.response?.status === 401 &&
            !originalRequest._retry &&
            !originalRequest.url?.includes(ENDPOINTS.REFRESH)
        ) {
            originalRequest._retry = true;

            try {
                if (!isRefreshing) {
                    isRefreshing = true;
                    refreshPromise = api.post(ENDPOINTS.REFRESH, {}).finally(() => {
                        isRefreshing = false;
                    });
                }

                await refreshPromise;

                return api(originalRequest);
            } catch (refreshError) {
                window.location.href = "/login";
                return Promise.reject(refreshError);
            }
        }

        return Promise.reject(error);
    }
);

export default api;