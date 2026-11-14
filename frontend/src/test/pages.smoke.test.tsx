import { describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/react';
import React from 'react';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from '../contexts/AuthContext';

// Pages
import { LoginPage } from '../pages/LoginPage';
import { RegisterPage } from '../pages/RegisterPage';
import { AnalysisPage } from '../pages/AnalysisPage';
import { RecommendationPage } from '../pages/RecommendationPage';
import { StegoBenchPage } from '../pages/StegoBenchPage';
import { HashToolPage } from '../pages/HashToolPage';
import { HistoryPage } from '../pages/HistoryPage';
import { GuidedDemoPage } from '../pages/GuidedDemoPage';

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value.toString();
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();
Object.defineProperty(window, 'localStorage', { value: localStorageMock });

// Mock globalThis.fetch to return empty json cleanly
globalThis.fetch = vi.fn().mockImplementation(() =>
  Promise.resolve({
    ok: true,
    status: 200,
    json: () => Promise.resolve({ items: [], history: [], results: [] }),
    text: () => Promise.resolve(''),
  })
);

describe('Frontend Pages Smoke Tests', () => {
  it('renders LoginPage without crashing', () => {
    const { container } = render(
      <AuthProvider>
        <BrowserRouter>
          <LoginPage />
        </BrowserRouter>
      </AuthProvider>
    );
    expect(container).toBeDefined();
    expect(container.querySelector('form')).toBeInTheDocument();
  });

  it('renders RegisterPage without crashing', () => {
    const { container } = render(
      <AuthProvider>
        <BrowserRouter>
          <RegisterPage />
        </BrowserRouter>
      </AuthProvider>
    );
    expect(container).toBeDefined();
    expect(container.querySelector('form')).toBeInTheDocument();
  });

  it('renders AnalysisPage without crashing', () => {
    const { container } = render(
      <AuthProvider>
        <BrowserRouter>
          <AnalysisPage />
        </BrowserRouter>
      </AuthProvider>
    );
    expect(container).toBeDefined();
  });

  it('renders RecommendationPage without crashing', () => {
    const { container } = render(
      <AuthProvider>
        <BrowserRouter>
          <RecommendationPage />
        </BrowserRouter>
      </AuthProvider>
    );
    expect(container).toBeDefined();
  });

  it('renders StegoBenchPage without crashing', () => {
    const { container } = render(
      <AuthProvider>
        <BrowserRouter>
          <StegoBenchPage />
        </BrowserRouter>
      </AuthProvider>
    );
    expect(container).toBeDefined();
  });

  it('renders HashToolPage without crashing', () => {
    const { container } = render(
      <AuthProvider>
        <BrowserRouter>
          <HashToolPage />
        </BrowserRouter>
      </AuthProvider>
    );
    expect(container).toBeDefined();
  });

  it('renders HistoryPage without crashing', () => {
    const { container } = render(
      <AuthProvider>
        <BrowserRouter>
          <HistoryPage />
        </BrowserRouter>
      </AuthProvider>
    );
    expect(container).toBeDefined();
  });

  it('renders GuidedDemoPage without crashing', () => {
    const { container } = render(
      <AuthProvider>
        <BrowserRouter>
          <GuidedDemoPage />
        </BrowserRouter>
      </AuthProvider>
    );
    expect(container).toBeDefined();
  });
});
