import { Outlet } from "react-router-dom";

export default function AuthLayout() {
  return (
    <div className="flex min-h-svh items-center justify-center bg-muted px-4">
      <div className="w-full max-w-sm">
        <Outlet />
      </div>
    </div>
  );
}
