import { ProtectedRoute, AdminRoute } from "../components/guards";
import { FieldsProvider } from "../hooks/useFields";
import DashboardLayout from "./DashboardLayout";

export function ProtectedLayout() {
  return (
    <ProtectedRoute>
      <FieldsProvider>
        <DashboardLayout />
      </FieldsProvider>
    </ProtectedRoute>
  );
}

export function AdminLayout() {
  return (
    <AdminRoute>
      <FieldsProvider>
        <DashboardLayout />
      </FieldsProvider>
    </AdminRoute>
  );
}