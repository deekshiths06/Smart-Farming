import { Navigate, Route, Routes } from "react-router-dom";
import { AdminLayout, ProtectedLayout } from "./layouts/ProtectedLayout";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Overview from "./pages/Overview";
import Fields from "./pages/Fields";
import CreateField from "./pages/CreateField";
import FieldDetail from "./pages/FieldDetail";
import FieldEdit from "./pages/FieldEdit";
import Weather from "./pages/Weather";
import SoilIntelligence from "./pages/SoilIntelligence";
import CropRecommendations from "./pages/CropRecommendations";
import ActionPlanner from "./pages/ActionPlanner";
import CropDisease from "./pages/CropDisease";
import Settings from "./pages/Settings";
import Admin from "./pages/Admin";

function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route element={<ProtectedLayout />}>
        <Route path="/dashboard" element={<Overview />} />
        <Route path="/fields" element={<Fields />} />
        <Route path="/fields/create" element={<CreateField />} />
        <Route path="/fields/:id" element={<FieldDetail />} />
        <Route path="/fields/:id/edit" element={<FieldEdit />} />
        <Route path="/weather" element={<Weather />} />
        <Route path="/soil" element={<SoilIntelligence />} />
        <Route path="/crops" element={<CropRecommendations />} />
        <Route path="/actions" element={<ActionPlanner />} />
        <Route path="/disease" element={<CropDisease />} />
        <Route path="/settings" element={<Settings />} />
      </Route>
      <Route element={<AdminLayout />}>
        <Route path="/admin" element={<Admin />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;