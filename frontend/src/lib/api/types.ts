export type LoginRequest = {
    username: string;
    password: string;
};

export type LoginResponse = {
    access: string;
    refresh: string;
};

export interface MeResponse {
    role: 'Student' | 'Teacher' | 'Admin';
    full_name: string;
}