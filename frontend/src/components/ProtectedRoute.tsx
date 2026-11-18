import { Navigate, Outlet, useLocation } from "react-router-dom";
import { getStoredToken, getStoredUser } from "../services/auth";

export function ProtectedRoute() {
  const user = getStoredUser();
  const token = getStoredToken();
  const location = useLocation();

  if (!user || !token) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <Outlet />;
}

