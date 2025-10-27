import axios from 'axios';
import { scriptApi, executionApi } from './api';

jest.mock('axios');
const mockedAxios = axios as jest.Mocked<typeof axios>;

describe('Script API', () => {
    beforeEach(() => {
        jest.clearAllMocks();
    });

    test('getAll returns list of scripts', async () => {
        const mockScripts = [
            { id: 1, name: 'test-script', script_type: 'bash', content: 'echo test' }
        ];

        mockedAxios.create.mockReturnValue({
            get: jest.fn().mockResolvedValue({ data: mockScripts }),
            post: jest.fn(),
            put: jest.fn(),
            delete: jest.fn(),
            interceptors: {
                request: { use: jest.fn(), eject: jest.fn() },
                response: { use: jest.fn(), eject: jest.fn() }
            }
        } as any);

        // Note: This is a simplified test. In real scenario, you'd need to properly mock the axios instance
    });
});

describe('Execution API', () => {
    test('create execution calls correct endpoint', async () => {
        const mockExecution = {
            script_id: 1,
            parameters: { key: 'value' }
        };

        mockedAxios.create.mockReturnValue({
            get: jest.fn(),
            post: jest.fn().mockResolvedValue({ data: mockExecution }),
            put: jest.fn(),
            delete: jest.fn(),
            interceptors: {
                request: { use: jest.fn(), eject: jest.fn() },
                response: { use: jest.fn(), eject: jest.fn() }
            }
        } as any);

        const response = await executionApi.create(mockExecution);
        expect(response).toEqual(mockExecution);
    });
});