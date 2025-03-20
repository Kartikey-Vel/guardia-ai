"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import DashboardMetrics from "@/components/dashboard/DashboardMetrics";
import RecentAlerts from "@/components/dashboard/RecentAlerts";
import CameraOverview from "@/components/dashboard/CameraOverview";

export default function Dashboard() {
  const { isAuthenticated, user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isAuthenticated, loading, router]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-gray-900"></div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>

      {user && (
        <div className="mb-6">
          <p className="text-lg">
            Welcome back, {user.full_name || user.username}
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <DashboardMetrics />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <CameraOverview />
        </div>
        <div>
          <RecentAlerts />
        </div>
      </div>
    </div>
  );
}
