import { useState, useCallback } from 'react';
import axios, { AxiosError } from 'axios';

interface ApiErrorResponse {
    detail?: string;
    message?: string;
    errors?: string[];
}

interface UseApiOptions<T> {
    onSuccess?: (data: T) => void;
    onError?: (error: Error) => void;
}

export const useApi = <T = any>(options?: UseApiOptions<T>) => {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<Error | null>(null);
    const [data, setData] = useState<T | null>(null);

    const execute = useCallback(async (apiCall: () => Promise<T>) => {
        setLoading(true);
        setError(null);

        try {
            const result = await apiCall();
            setData(result);
            options?.onSuccess?.(result);
            return result;
        } catch (err) {
            const error = err as AxiosError<ApiErrorResponse>;

            // Extract error message
            let errorMessage = 'An error occurred';
            if (error.response?.data) {
                const data = error.response.data;
                errorMessage = data.detail || data.message || errorMessage;

                // If there are multiple errors, concatenate them
                if (data.errors && Array.isArray(data.errors)) {
                    errorMessage = data.errors.join(', ');
                }
            } else if (error.message) {
                errorMessage = error.message;
            }

            const errorObj = new Error(errorMessage);
            setError(errorObj);
            options?.onError?.(errorObj);
            throw errorObj;
        } finally {
            setLoading(false);
        }
    }, [options]);

    const reset = useCallback(() => {
        setLoading(false);
        setError(null);
        setData(null);
    }, []);

    return {
        loading,
        error,
        data,
        execute,
        reset
    };
};