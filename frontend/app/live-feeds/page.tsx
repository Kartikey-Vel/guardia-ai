"use client";

import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { CameraGrid } from "@/components/dashboard/CameraGrid";

export default function LiveFeedsPage() {
  return (
    <DashboardLayout>
      <div className="flex flex-col gap-6 w-full h-full pb-8">
        <div>
          <h1 className="text-3xl font-outfit font-bold tracking-tight">Live Camera Feeds</h1>
          <p className="text-default-500 mt-1">Real-time multiview camera monitoring.</p>
        </div>

        <div className="w-full">
          <CameraGrid />
        </div>
      </div>
    </DashboardLayout>
  );
}
