import api from "./axios";
import { ENDPOINTS } from "./endpoints";
import type { LoginRequest, LoginResponse, MeResponse } from "./types";

export async function loginApi(data: LoginRequest): Promise<LoginResponse> {
    const response = await api.post<LoginResponse>(ENDPOINTS.LOGIN, data);
    return response.data;
}

export async function logoutApi() {
    return await api.post(ENDPOINTS.LOGOUT);
}

export async function meApi(): Promise<MeResponse | null> {
    try {
        const response = await api.get<MeResponse>(ENDPOINTS.ME);
        return response.data;
    } catch (err) {
        return null; 
    }
}