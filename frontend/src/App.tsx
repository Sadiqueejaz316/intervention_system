import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import { ApiError } from '@/api/client'
import { AuthProvider } from '@/auth/AuthProvider'
import { AppLayout } from '@/components/AppLayout'
import { RequireAuth, RequireRole } from '@/components/guards'
import { EmptyState } from '@/components/ui'
import { LoginPage } from '@/pages/LoginPage'
import { MyJobsPage } from '@/pages/MyJobsPage'
import { NewTicketPage } from '@/pages/NewTicketPage'
import { NotificationsPage } from '@/pages/NotificationsPage'
import { RegisterPage } from '@/pages/RegisterPage'
import { TicketDetailPage } from '@/pages/TicketDetailPage'
import { TicketsPage } from '@/pages/TicketsPage'
import { WorkersPage } from '@/pages/WorkersPage'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 15_000,
      // Retrying a 401 or a 403 only repeats a refusal the API already gave.
      retry: (failureCount, error) => {
        if (error instanceof ApiError && error.status < 500) return false

        return failureCount < 2
      },
    },
  },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />

            <Route
              element={
                <RequireAuth>
                  <AppLayout />
                </RequireAuth>
              }
            >
              <Route index element={<Navigate to="/tickets" replace />} />
              <Route path="/tickets" element={<TicketsPage />} />
              <Route path="/tickets/new" element={<NewTicketPage />} />
              <Route path="/tickets/:ticketId" element={<TicketDetailPage />} />
              <Route
                path="/my-jobs"
                element={
                  <RequireRole roles={['CONTRACTOR']}>
                    <MyJobsPage />
                  </RequireRole>
                }
              />
              <Route
                path="/workers"
                element={
                  <RequireRole roles={['DISPATCHER']}>
                    <WorkersPage />
                  </RequireRole>
                }
              />
              <Route path="/notifications" element={<NotificationsPage />} />
              <Route
                path="*"
                element={
                  <EmptyState
                    title="Page not found"
                    hint="The link may be out of date."
                  />
                }
              />
            </Route>
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
