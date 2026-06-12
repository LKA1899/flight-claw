import { Navigate, createBrowserRouter } from "react-router-dom";
import { AppLayout } from "@/components/layout/AppLayout";
import { AuthGuard } from "@/components/auth/AuthGuard";
import { LoginPage } from "@/pages/auth/LoginPage";
import { OverviewPage } from "@/pages/OverviewPage";
import { MonitorListPage } from "@/pages/monitors/MonitorListPage";
import { MonitorCreatePage } from "@/pages/monitors/MonitorCreatePage";
import { MonitorEditPage } from "@/pages/monitors/MonitorEditPage";
import { MonitorDetailPage } from "@/pages/monitors/MonitorDetailPage";
import { MonitorSchedulePage } from "@/pages/monitors/MonitorSchedulePage";
import { MonitorPositioningsPage } from "@/pages/monitors/MonitorPositioningsPage";
import { MonitorTransfersPage } from "@/pages/monitors/MonitorTransfersPage";
import { ScanListPage } from "@/pages/scans/ScanListPage";
import { ScanDetailPage } from "@/pages/scans/ScanDetailPage";
import { BatchListPage } from "@/pages/batches/BatchListPage";
import { TaskListPage } from "@/pages/tasks/TaskListPage";
import { PriceListPage } from "@/pages/prices/PriceListPage";
import { PlanListPage } from "@/pages/plans/PlanListPage";
import { ResultsPage } from "@/pages/results/ResultsPage";
import { RoundTripResultsPage } from "@/pages/roundtrips/RoundTripResultsPage";
import { BestDealListPage } from "@/pages/best/BestDealListPage";
import { SettingsPage } from "@/pages/settings/SettingsPage";

export const router = createBrowserRouter([
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    path: "/",
    element: (
      <AuthGuard>
        <AppLayout />
      </AuthGuard>
    ),
    children: [
      { index: true, element: <Navigate to="/overview" replace /> },
      { path: "overview", element: <OverviewPage /> },
      { path: "monitors", element: <MonitorListPage /> },
      { path: "monitors/new", element: <MonitorCreatePage /> },
      { path: "monitors/:id", element: <MonitorDetailPage /> },
      { path: "monitors/:id/edit", element: <MonitorEditPage /> },
      { path: "monitors/:id/schedule", element: <MonitorSchedulePage /> },
      { path: "monitors/:id/positionings", element: <MonitorPositioningsPage /> },
      { path: "monitors/:id/transfers", element: <MonitorTransfersPage /> },
      { path: "scans", element: <ScanListPage /> },
      { path: "scans/:id", element: <ScanDetailPage /> },
      { path: "batches", element: <BatchListPage /> },
      { path: "tasks", element: <TaskListPage /> },
      { path: "prices", element: <PriceListPage /> },
      { path: "plans", element: <PlanListPage /> },
      { path: "results", element: <ResultsPage /> },
      { path: "round-trips", element: <RoundTripResultsPage /> },
      { path: "best", element: <BestDealListPage /> },
      { path: "settings", element: <SettingsPage /> },
    ],
  },
]);
