import { renderHook, act, waitFor } from '@testing-library/react';
import { useApi } from '../useApi';

describe('useApi Hook', () => {
    it('handles successful API call', async () => {
        const mockApiCall = jest.fn().mockResolvedValue({ data: 'success' });
        const { result } = renderHook(() => useApi());

        await act(async () => {
            await result.current.execute(mockApiCall);
        });

        await waitFor(() => {
            expect(result.current.loading).toBe(false);
            expect(result.current.data).toEqual({ data: 'success' });
            expect(result.current.error).toBeNull();
        });
    });

    it('handles API call errors', async () => {
        const mockApiCall = jest.fn().mockRejectedValue(new Error('API Error'));
        const { result } = renderHook(() => useApi());

        await act(async () => {
            try {
                await result.current.execute(mockApiCall);
            } catch (error) {
                // Expected to throw
            }
        });

        await waitFor(() => {
            expect(result.current.loading).toBe(false);
            expect(result.current.error).toBeTruthy();
            expect(result.current.data).toBeNull();
        });
    });

    it('calls onSuccess callback', async () => {
        const mockApiCall = jest.fn().mockResolvedValue({ data: 'success' });
        const onSuccess = jest.fn();

        const { result } = renderHook(() => useApi({ onSuccess }));

        await act(async () => {
            await result.current.execute(mockApiCall);
        });

        await waitFor(() => {
            expect(onSuccess).toHaveBeenCalledWith({ data: 'success' });
        });
    });
});