import { Outlet, Route, Routes } from 'react-router-dom';
import Layout from './components/Layout';
import { ToastProvider } from './components/Toast';
import { AdminAuthProvider } from './contexts/AdminAuthContext';
import ProtectedRoute from './components/admin/ProtectedRoute';
import Home from './pages/Home';
import Report from './pages/Report';
import Reports from './pages/Reports';
import ReportDetail from './pages/ReportDetail';
import AdminLogin from './pages/admin/Login';
import AdminDashboard from './pages/admin/AdminDashboard';
import AdminReportsList from './pages/admin/ReportsList';
import AdminReportDetailPage from './pages/admin/ReportDetail';
import PlaceholderPage from './pages/admin/PlaceholderPage';

function PublicLayout() {
  return (
    <Layout>
      <Outlet />
    </Layout>
  );
}

export default function App() {
  return (
    <ToastProvider>
      <AdminAuthProvider>
        <Routes>
          <Route element={<PublicLayout />}>
            <Route path="/" element={<Home />} />
            <Route path="/report" element={<Report />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/reports/:id" element={<ReportDetail />} />
            <Route path="/admin/login" element={<AdminLogin />} />
          </Route>

          <Route
            path="/admin/*"
            element={
              <ProtectedRoute>
                <Routes>
                  <Route path="/" element={<AdminDashboard />} />
                  <Route path="/dashboard" element={<AdminDashboard />} />
                  <Route path="/reports" element={<AdminReportsList />} />
                  <Route path="/reports/:reportId" element={<AdminReportDetailPage />} />
                  <Route
                    path="/match-review"
                    element={<PlaceholderPage title="AI Match Review" description="Match review and moderation will be available in a later phase." />}
                  />
                  <Route
                    path="/incidents"
                    element={<PlaceholderPage title="Incidents" description="Incident management will be available in a later phase." />}
                  />
                  <Route path="*" element={<AdminDashboard />} />
                </Routes>
              </ProtectedRoute>
            }
          />
        </Routes>
      </AdminAuthProvider>
    </ToastProvider>
  );
}
