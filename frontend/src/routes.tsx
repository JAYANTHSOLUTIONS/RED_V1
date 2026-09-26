import { createBrowserRouter } from 'react-router';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import PropertiesPage from './pages/PropertiesPage';
import PropertyDetailPage from './pages/PropertyDetailPage';
import ClientsPage from './pages/ClientsPage';
import ClientDetailPage from './pages/ClientDetailPage';
import LeadsPage from './pages/LeadsPage';
import LeadDetailPage from './pages/LeadDetailPage';
import RequirementsPage from './pages/RequirementsPage';
import RequirementDetailPage from './pages/RequirementDetailPage';
import SiteVisitsPage from './pages/SiteVisitsPage';
import FollowUpsPage from './pages/FollowUpsPage';
import DocumentsPage from './pages/DocumentsPage';
import NotificationsPage from './pages/NotificationsPage';
import AuditLogsPage from './pages/AuditLogsPage';
import PublicPropertiesPage from './pages/PublicPropertiesPage';
import PublicPropertyDetailPage from './pages/PublicPropertyDetailPage';
import CadastralSketchesPage from './pages/CadastralSketchesPage';
import { AppLayout } from './components/layout/AppLayout';

export const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/public/properties',
    element: <PublicPropertiesPage />,
  },
  {
    path: '/public/properties/:ref',
    element: <PublicPropertyDetailPage />,
  },
  {
    path: '/',
    element: <AppLayout />,
    children: [
      {
        index: true,
        element: <DashboardPage />,
      },
      {
        path: 'dashboard',
        element: <DashboardPage />,
      },
      {
        path: 'properties',
        element: <PropertiesPage />,
      },
      {
        path: 'properties/:id',
        element: <PropertyDetailPage />,
      },
      {
        path: 'sketches',
        element: <CadastralSketchesPage />,
      },
      {
        path: 'clients',
        element: <ClientsPage />,
      },
      {
        path: 'clients/:id',
        element: <ClientDetailPage />,
      },
      {
        path: 'leads',
        element: <LeadsPage />,
      },
      {
        path: 'leads/:id',
        element: <LeadDetailPage />,
      },
      {
        path: 'requirements',
        element: <RequirementsPage />,
      },
      {
        path: 'requirements/:id',
        element: <RequirementDetailPage />,
      },
      {
        path: 'site-visits',
        element: <SiteVisitsPage />,
      },
      {
        path: 'follow-ups',
        element: <FollowUpsPage />,
      },
      {
        path: 'documents',
        element: <DocumentsPage />,
      },
      {
        path: 'notifications',
        element: <NotificationsPage />,
      },
      {
        path: 'audit-logs',
        element: <AuditLogsPage />,
      },
    ],
  },
]);
