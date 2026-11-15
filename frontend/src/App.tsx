import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { DashboardLayout } from "./layouts/DashboardLayout";
import { DashboardPage } from "./pages/DashboardPage";
import { FixSuggestionPage } from "./pages/FixSuggestionPage";
import { LandingPage } from "./pages/LandingPage";
import { LiveExecutionPage } from "./pages/LiveExecutionPage";
import { LoginPage } from "./pages/LoginPage";
import { NewReviewPage } from "./pages/NewReviewPage";
import { ReviewHistoryPage } from "./pages/ReviewHistoryPage";
import { ReviewResultsPage } from "./pages/ReviewResultsPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public Landing & Authentication */}
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />

        {/* Dashboard Workspace */}
        <Route element={<DashboardLayout />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/app" element={<Navigate to="/dashboard" replace />} />
          <Route path="/new" element={<NewReviewPage />} />
          <Route path="/history" element={<ReviewHistoryPage />} />
          <Route path="/reviews/:reviewId/live" element={<LiveExecutionPage />} />
          <Route path="/reviews/:reviewId" element={<ReviewResultsPage />} />
          <Route path="/reviews/:reviewId/patch" element={<FixSuggestionPage />} />
        </Route>

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
