import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from '@/context/AuthContext';
import { AppLayout } from '@/components/layout/AppLayout';
import { LoginPage } from '@/pages/LoginPage';
import { HealthPage } from '@/pages/HealthPage';
import { MetricsPage } from '@/pages/MetricsPage';
import { DashboardPage } from '@/pages/DashboardPage';
import { StatsPage } from '@/pages/StatsPage';
import { QueryPage } from '@/pages/QueryPage';

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 30_000 } },
});

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route element={<AppLayout />}>
              <Route index element={<Navigate to="/dashboard" replace />} />
              <Route path="/health"    element={<HealthPage />}    />
              <Route path="/metrics"   element={<MetricsPage />}   />
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/stats"     element={<StatsPage />}     />
              <Route path="/query"     element={<QueryPage />}     />
            </Route>
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}
