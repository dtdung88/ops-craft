import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';
const WS_BASE_URL = process.env.REACT_APP_WS_URL || 'ws://localhost:8000';

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

export interface Secret {
    id: number;
    name: string;
    description?: string;
    created_by?: number;
    created_at: string;
    updated_at?: string;
    last_accessed_at?: string;
}

export interface SecretCreate {
    name: string;
    value: string;
    description?: string;
}

export interface AuditLog {
    id: number;
    secret_id: number;
    secret_name: string;
    action: string;
    accessed_by: number;
    accessed_by_username: string;
    execution_id?: number;
    script_id?: number;
    timestamp: string;
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

    // Secret management for scripts
    getSecrets: (scriptId: number) =>
        apiClient.get<Secret[]>(`/scripts/${scriptId}/secrets`),
    attachSecret: (scriptId: number, secretId: number) =>
        apiClient.post(`/scripts/${scriptId}/secrets/${secretId}`),
    detachSecret: (scriptId: number, secretId: number) =>
        apiClient.delete(`/scripts/${scriptId}/secrets/${secretId}`),
};

// Execution API
export const executionApi = {
    getAll: (scriptId?: number) =>
        apiClient.get<Execution[]>('/executions', { params: { script_id: scriptId } }),
    getById: (id: number) => apiClient.get<Execution>(`/executions/${id}`),
    create: (data: ExecutionCreate) => apiClient.post<Execution>('/executions', data),
    cancel: (id: number) => apiClient.post<Execution>(`/executions/${id}/cancel`),
    getLogs: (id: number) => apiClient.get(`/executions/${id}/logs`),
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
    getAll: (params?: any) => apiClient.get<Secret[]>('/secrets', { params }),
    getById: (id: number) => apiClient.get<Secret>(`/secrets/${id}`),
    getByName: (name: string) => apiClient.get<Secret>(`/secrets/name/${name}`),
    create: (data: SecretCreate) => apiClient.post<Secret>('/secrets', data),
    update: (id: number, data: Partial<SecretCreate>) =>
        apiClient.put<Secret>(`/secrets/${id}`, data),
    delete: (id: number) => apiClient.delete(`/secrets/${id}`),

    // Audit logs for secrets
    getAuditLogs: (secretId: number) =>
        apiClient.get<AuditLog[]>(`/secrets/${secretId}/audit-logs`),
};

// Health API
export const healthApi = {
    check: () => apiClient.get('/health'),
};

// WebSocket API
export const websocketApi = {
    getStats: () => apiClient.get('/ws/stats'),
};

// WebSocket URL helper
export const getWebSocketUrl = (executionId: number): string => {
    const token = localStorage.getItem('access_token');
    if (!token) {
        console.warn('[WebSocket] No access token found');
        return '';
    }
    return `${WS_BASE_URL}/ws/executions/${executionId}?token=${token}`;
};

export default apiClient;