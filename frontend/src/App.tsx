import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components/Layout';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { ChatPage } from './pages/ChatPage';
import { GuidedDemoPage } from './pages/GuidedDemoPage';
import { StegoBenchPage } from './pages/StegoBenchPage';
import { AnalysisPage } from './pages/AnalysisPage';
import { RecommendationPage } from './pages/RecommendationPage';
import { HistoryPage } from './pages/HistoryPage';

export const App: React.FC = () => {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      {/* Protected Routes inside Layout */}
      <Route path="/" element={<Layout />}>
        <Route index element={<Navigate to="/chat" replace />} />
        <Route path="chat" element={<ChatPage />} />
        <Route path="demo" element={<GuidedDemoPage />} />
        <Route path="bench" element={<StegoBenchPage />} />
        <Route path="analysis" element={<AnalysisPage />} />
        <Route path="recommender" element={<RecommendationPage />} />
        <Route path="history" element={<HistoryPage />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};
