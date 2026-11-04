import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { PlanProvider, usePlan } from "./contexts/PlanContext";
import LoginPage from "./pages/LoginPage";
import OnboardingPage from "./pages/OnboardingPage";
import EventSelectPage from "./pages/EventSelectPage";
import CourseSelectPage from "./pages/CourseSelectPage";
import CourseResultPage from "./pages/CourseResultPage";
import BookingPage from "./pages/BookingPage";
import CompletePage from "./pages/CompletePage";
import type { ReactNode } from "react";

function ProtectedRoute({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  return user ? <>{children}</> : <Navigate to="/login" replace />;
}

/** 온보딩을 거쳐 코스가 생성된 뒤에만 들어갈 수 있는 페이지 */
function RequirePlan({ children }: { children: ReactNode }) {
  const { plan } = usePlan();
  return plan ? <>{children}</> : <Navigate to="/" replace />;
}

/** 이벤트 선택 후 실제 코스를 받은 뒤에만 (샘플 코스로 보여주지 않음) */
function RequireCourses({ children }: { children: ReactNode }) {
  const { plan } = usePlan();
  return plan?.coursesReady ? <>{children}</> : <Navigate to={plan ? "/events" : "/"} replace />;
}

const planPage = (page: ReactNode) => <ProtectedRoute><RequirePlan>{page}</RequirePlan></ProtectedRoute>;
const coursePage = (page: ReactNode) => <ProtectedRoute><RequireCourses>{page}</RequireCourses></ProtectedRoute>;

function App() {
  return (
    <AuthProvider>
      <PlanProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/" element={<ProtectedRoute><OnboardingPage /></ProtectedRoute>} />
            <Route path="/events" element={planPage(<EventSelectPage />)} />
            <Route path="/courses" element={coursePage(<CourseSelectPage />)} />
            <Route path="/result" element={coursePage(<CourseResultPage />)} />
            <Route path="/booking" element={coursePage(<BookingPage />)} />
            {/* 공유 링크(?share=)로도 열리므로 RequirePlan 대신 페이지 안에서 처리 */}
            <Route path="/complete" element={<ProtectedRoute><CompletePage /></ProtectedRoute>} />
          </Routes>
        </BrowserRouter>
      </PlanProvider>
    </AuthProvider>
  );
}
export default App;
