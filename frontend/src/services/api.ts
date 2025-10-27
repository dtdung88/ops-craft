import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL;
const WS_BASE_URL = process.env.REACT_APP_WS_URL;

const apiClient = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Request interceptor for adding auth token
apiClient.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('access_token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            localStorage.removeItem('access_token');
            window.location.href = '/login';
        }
        return Promise.reject(error);
    }
);

export interface Script {
    id: number;
    name: string;
    description?: string;
    script_type: 'bash' | 'python' | 'ansible' | 'terraform';
    content: string;
    parameters?: any;
    status: 'active' | 'deprecated' | 'draft';
    version: string;
    tags?: string[];
    created_at: string;
    updated_at?: string;
    created_by?: string;
}

export interface ScriptCreate {
    name: string;
    description?: string;
    script_type: 'bash' | 'python' | 'ansible' | 'terraform';
    content: string;
    parameters?: any;
    tags?: string[];
    version?: string;
}

export interface Execution {
    id: number;
    script_id: number;
    status: 'pending' | 'running' | 'success' | 'failed' | 'cancelled';
    parameters?: any;
    output?: string;
    error?: string;
    started_at?: string;
    completed_at?: string;
    executed_by?: string;
    created_at: string;
}

export interface ExecutionCreate {
    script_id: number;
    parameters?: any;
}

// Script API
export const scriptApi = {
    getAll: () => apiClient.get<Script[]>('/scripts'),
    getById: (id: number) => apiClient.get<Script>(`/scripts/${id}`),
    create: (data: ScriptCreate) => apiClient.post<Script>('/scripts', data),
    update: (id: number, data: Partial<ScriptCreate>) =>
        apiClient.put<Script>(`/scripts/${id}`, data),
    delete: (id: number) => apiClient.delete(`/scripts/${id}`),
    execute: (id: number, params?: any) => apiClient.post(`/scripts/${id}/execute`, params),
};

// Execution API
export const executionApi = {
    getAll: (scriptId?: number) =>
        apiClient.get<Execution[]>('/executions', { params: { script_id: scriptId } }),
    getById: (id: number) => apiClient.get<Execution>(`/executions/${id}`),
    create: (data: ExecutionCreate) => apiClient.post<Execution>('/executions', data),
    cancel: (id: number) => apiClient.post<Execution>(`/executions/${id}/cancel`),
};

// Auth API
export const authApi = {
    login: (username: string, password: string) =>
        apiClient.post('/auth/login', new URLSearchParams({ username, password }), {
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        }),
    register: (data: any) => apiClient.post('/auth/register', data),
    getCurrentUser: () => apiClient.get('/auth/me'),
};

// Admin API
export const adminApi = {
    getStats: () => apiClient.get('/admin/stats'),
    listUsers: (params?: any) => apiClient.get('/admin/users', { params }),
    getUser: (id: number) => apiClient.get(`/admin/users/${id}`),
    createUser: (data: any) => apiClient.post('/admin/users', data),
    updateUser: (id: number, data: any) => apiClient.put(`/admin/users/${id}`, data),
    deleteUser: (id: number) => apiClient.delete(`/admin/users/${id}`),
    toggleUserActive: (id: number) => apiClient.patch(`/admin/users/${id}/toggle-active`),
};

// Secrets API
export const secretsApi = {
    getAll: (params?: any) => apiClient.get('/secrets', { params }),
    getById: (id: number) => apiClient.get(`/secrets/${id}`),
    getByName: (name: string) => apiClient.get(`/secrets/name/${name}`),
    create: (data: any) => apiClient.post('/secrets', data),
    update: (id: number, data: any) => apiClient.put(`/secrets/${id}`, data),
    delete: (id: number) => apiClient.delete(`/secrets/${id}`),
};

// Health API
export const healthApi = {
    check: () => apiClient.get('/health'),
};

// WebSocket URL helper
export const getWebSocketUrl = (executionId: number): string => {
    const token = localStorage.getItem('access_token');
    return `${WS_BASE_URL}/ws/executions/${executionId}?token=${token}`;
};

export default apiClient;