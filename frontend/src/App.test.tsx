import React from 'react';
import { render, screen } from '@testing-library/react';
import App from './App';

const originalWarn = console.warn;

beforeAll(() => {
    // Overwrite the console.warn function before running tests
    console.warn = (...args) => {
        // Check if the warning message includes the known warning text
        const message = args[0] || '';
        if (typeof message === 'string' && message.includes('React Router Future Flag Warning')) {
            return; // Ignore the warning
        }
        originalWarn(...args); // Pass through other warnings
    };
});

// Mock the child components to avoid complex setup
jest.mock('./pages/Dashboard', () => () => <div>Dashboard</div>);
jest.mock('./pages/ScriptList', () => () => <div>Script List</div>);
jest.mock('./pages/ScriptDetail', () => () => <div>Script Detail</div>);
jest.mock('./pages/ScriptCreate', () => () => <div>Script Create</div>);
jest.mock('./pages/ExecutionList', () => () => <div>Execution List</div>);

describe('App Component', () => {
    test('renders navigation bar', () => {
        render(<App />);
        const heading = screen.getByText(/OpsCraft/i);
        expect(heading as HTMLElement).toBeInTheDocument();
    });

    test('renders navigation links', () => {
        render(<App />);
        expect(screen.getByRole('link', { name: /Dashboard/i }) as HTMLElement).toBeInTheDocument();
        expect(screen.getByRole('link', { name: /Scripts/i }) as HTMLElement).toBeInTheDocument();
        expect(screen.getByRole('link', { name: /Executions/i }) as HTMLElement).toBeInTheDocument();
        expect(screen.getByRole('link', { name: /New Script/i }) as HTMLElement).toBeInTheDocument();
    });
});

afterAll(() => {
    // Restore the original console.warn after all tests run
    console.warn = originalWarn;
});