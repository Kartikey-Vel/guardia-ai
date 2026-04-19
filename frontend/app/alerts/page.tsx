"use client";

import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { InsightPanel } from "@/components/dashboard/InsightPanel";

export default function AlertsPage() {
  return (
    <DashboardLayout>
      <div className="flex flex-col gap-6 w-full h-full pb-8">
        <div>
          <h1 className="text-3xl font-outfit font-bold tracking-tight">Alerts & Incidents</h1>
          <p className="text-default-500 mt-1">Manage and review system security alerts.</p>
        </div>

        <div className="w-full xl:w-2/3 h-[600px]">
          <InsightPanel />
        </div>
      </div>
    </DashboardLayout>
  );
}
