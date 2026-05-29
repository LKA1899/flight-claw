import { useQuery } from "@tanstack/react-query";
import { Navigate, useLocation } from "react-router-dom";
import { authApi, getToken, clearToken } from "@/api/authApi";
import { LoadingState } from "@/components/common/LoadingState";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const token = getToken();

  if (!token) {
    return <Navigate to={`/login?redirect=${encodeURIComponent(location.pathname + location.search)}`} replace />;
  }

  return <AuthGuardInner>{children}</AuthGuardInner>;
}

function AuthGuardInner({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const { isLoading, isError } = useQuery({
    queryKey: ["auth-me"],
    queryFn: () => authApi.getMe(),
    retry: 1,
    staleTime: 5 * 60 * 1000,
  });

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <LoadingState />
      </div>
    );
  }

  if (isError) {
    clearToken();
    return <Navigate to={`/login?redirect=${encodeURIComponent(location.pathname + location.search)}`} replace />;
  }

  return <>{children}</>;
}
