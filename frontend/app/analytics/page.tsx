"use client";

import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { AnalysisCards } from "@/components/dashboard/AnalysisCards";
import { PerformanceMetrics } from "@/components/dashboard/PerformanceMetrics";

export default function AnalyticsPage() {
  return (
    <DashboardLayout>
      <div className="flex flex-col gap-6 w-full h-full pb-8">
        <div>
          <h1 className="text-3xl font-outfit font-bold tracking-tight">System Analytics</h1>
          <p className="text-default-500 mt-1">Deep dive into physical security data.</p>
        </div>

        <AnalysisCards />
        
        <PerformanceMetrics />
      </div>
    </DashboardLayout>
  );
}
