import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

interface User {
    id: number;
    username: string;
    email: string;
    role: string;
    full_name?: string;
    is_active: boolean;
    created_at: string;
    last_login?: string;
}

interface AuthContextType {
    user: User | null;
    token: string | null;
    login: (username: string, password: string) => Promise<void>;
    register: (username: string, email: string, password: string, fullName?: string) => Promise<void>;
    logout: () => void;
    refreshToken: () => Promise<void>;
    isAuthenticated: boolean;
    isAdmin: boolean;
    isOperator: boolean;
    isViewer: boolean;
    loading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const API_URL = process.env.REACT_APP_API_URL;

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const [user, setUser] = useState<User | null>(null);
    const [token, setToken] = useState<string | null>(
        localStorage.getItem('access_token')
    );
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();

    // Setup axios interceptor for auth
    useEffect(() => {
        const interceptor = axios.interceptors.request.use(
            (config) => {
                const accessToken = localStorage.getItem('access_token');
                if (accessToken) {
                    config.headers.Authorization = `Bearer ${accessToken}`;
                }
                return config;
            },
            (error) => Promise.reject(error)
        );

        return () => {
            axios.interceptors.request.eject(interceptor);
        };
    }, []);

    // Setup response interceptor for token refresh
    useEffect(() => {
        const interceptor = axios.interceptors.response.use(
            (response) => response,
            async (error) => {
                const originalRequest = error.config;

                if (error.response?.status === 401 && !originalRequest._retry) {
                    originalRequest._retry = true;

                    try {
                        await refreshToken();
                        return axios(originalRequest);
                    } catch (refreshError) {
                        logout();
                        return Promise.reject(refreshError);
                    }
                }

                return Promise.reject(error);
            }
        );

        return () => {
            axios.interceptors.response.eject(interceptor);
        };
    }, []);

    // Load user on mount if token exists
    useEffect(() => {
        const loadUser = async () => {
            if (token) {
                try {
                    await fetchUser();
                } catch (error) {
                    console.error('Failed to load user:', error);
                    logout();
                }
            }
            setLoading(false);
        };

        loadUser();
    }, [token]);

    const fetchUser = async () => {
        try {
            const response = await axios.get(`${API_URL}/auth/me`);
            setUser(response.data);
        } catch (error) {
            throw error;
        }
    };

    const login = async (username: string, password: string) => {
        try {
            const response = await axios.post(`${API_URL}/auth/login`, {
                username,
                password,
            });

            const { access_token, refresh_token } = response.data;

            localStorage.setItem('access_token', access_token);
            localStorage.setItem('refresh_token', refresh_token);
            setToken(access_token);

            // Fetch user data
            await fetchUser();

            navigate('/');
        } catch (error: any) {
            throw new Error(error.response?.data?.detail || 'Login failed');
        }
    };

    const register = async (username: string, email: string, password: string, fullName?: string) => {
        try {
            await axios.post(`${API_URL}/auth/register`, {
                username,
                email,
                password,
                full_name: fullName,
            });

            // Auto-login after registration
            await login(username, password);
        } catch (error: any) {
            throw new Error(error.response?.data?.detail || 'Registration failed');
        }
    };

    const refreshToken = async () => {
        try {
            const refresh = localStorage.getItem('refresh_token');
            if (!refresh) {
                throw new Error('No refresh token');
            }

            const response = await axios.post(`${API_URL}/auth/refresh`, {
                refresh_token: refresh,
            });

            const { access_token, refresh_token } = response.data;

            localStorage.setItem('access_token', access_token);
            localStorage.setItem('refresh_token', refresh_token);
            setToken(access_token);
        } catch (error) {
            logout();
            throw error;
        }
    };

    const logout = () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        setToken(null);
        setUser(null);
        navigate('/login');
    };

    const isAuthenticated = !!user && !!token;
    const isAdmin = user?.role === 'admin';
    const isOperator = user?.role === 'operator' || isAdmin;
    const isViewer = user?.role === 'viewer' || isOperator;

    return (
        <AuthContext.Provider
            value={{
                user,
                token,
                login,
                register,
                logout,
                refreshToken,
                isAuthenticated,
                isAdmin,
                isOperator,
                isViewer,
                loading,
            }}
        >
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within AuthProvider');
    }
    return context;
};