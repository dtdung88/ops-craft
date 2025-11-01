import React, { Suspense, lazy } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './contexts/AuthContext';
import { ToastProvider } from './contexts/ToastContext';
import { ErrorBoundary } from './components/ErrorBoundary';
import ProtectedRoute from './components/ProtectedRoute';
import { LoadingSpinner } from './components/ui/LoadingSpinner';
import './App.css';

// Lazy load pages
const Login = lazy(() => import('./pages/Login'));
const Register = lazy(() => import('./pages/Register'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const ScriptList = lazy(() => import('./pages/ScriptList'));
const ScriptDetail = lazy(() => import('./pages/ScriptDetail'));
const ScriptCreate = lazy(() => import('./pages/ScriptCreate'));
const ScriptEdit = lazy(() => import('./pages/ScriptEdit'));
const ExecutionList = lazy(() => import('./pages/ExecutionList'));
const AdminPanel = lazy(() => import('./pages/AdminPanel'));
const SecretsManagement = lazy(() => import('./pages/SecretsManagement'));

// Lazy load Navbar
const Navbar = lazy(() => import('./components/Navbar'));

const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            refetchOnWindowFocus: false,
            retry: 1,
            staleTime: 5 * 60 * 1000, // 5 minutes
            gcTime: 10 * 60 * 1000, // 10 minutes (replaces cacheTime in v5)
        },
    },
});

// Loading fallback component
const PageLoader = () => (
    <div className="page-loader">
        <LoadingSpinner size="large" message="Loading..." />
    </div>
);

function App() {
    return (
        <ErrorBoundary>
            <QueryClientProvider client={queryClient}>
                <Router>
                    <AuthProvider>
                        <ToastProvider>
                            <div className="App">
                                <Suspense fallback={<div className="navbar-skeleton" />}>
                                    <Navbar />
                                </Suspense>

                                <main className="main-content">
                                    <Suspense fallback={<PageLoader />}>
                                        <Routes>
                                            {/* Public routes */}
                                            <Route path="/login" element={<Login />} />
                                            <Route path="/register" element={<Register />} />

                                            {/* Protected routes */}
                                            <Route path="/" element={
                                                <ProtectedRoute>
                                                    <Dashboard />
                                                </ProtectedRoute>
                                            } />

                                            <Route path="/scripts" element={
                                                <ProtectedRoute>
                                                    <ScriptList />
                                                </ProtectedRoute>
                                            } />

                                            <Route path="/scripts/new" element={
                                                <ProtectedRoute requireOperator>
                                                    <ScriptCreate />
                                                </ProtectedRoute>
                                            } />

                                            <Route path="/scripts/:id" element={
                                                <ProtectedRoute>
                                                    <ScriptDetail />
                                                </ProtectedRoute>
                                            } />

                                            <Route path="/scripts/:id/edit" element={
                                                <ProtectedRoute requireOperator>
                                                    <ScriptEdit />
                                                </ProtectedRoute>
                                            } />

                                            <Route path="/executions" element={
                                                <ProtectedRoute>
                                                    <ExecutionList />
                                                </ProtectedRoute>
                                            } />

                                            <Route path="/secrets" element={
                                                <ProtectedRoute requireOperator>
                                                    <SecretsManagement />
                                                </ProtectedRoute>
                                            } />

                                            <Route path="/admin" element={
                                                <ProtectedRoute requireAdmin>
                                                    <AdminPanel />
                                                </ProtectedRoute>
                                            } />

                                            {/* Fallback */}
                                            <Route path="*" element={<Navigate to="/" replace />} />
                                        </Routes>
                                    </Suspense>
                                </main>
                            </div>
                        </ToastProvider>
                    </AuthProvider>
                </Router>
            </QueryClientProvider>
        </ErrorBoundary>
    );
}

export default App;