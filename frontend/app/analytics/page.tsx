"use client";

import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { AnalysisCards } from "@/components/dashboard/AnalysisCards";
import { Card } from "@heroui/react";
import { Activity } from "lucide-react";

export default function AnalyticsPage() {
  return (
    <DashboardLayout>
      <div className="flex flex-col gap-6 w-full h-full pb-8">
        <div>
          <h1 className="text-3xl font-outfit font-bold tracking-tight">System Analytics</h1>
          <p className="text-default-500 mt-1">Deep dive into physical security data.</p>
        </div>

        <AnalysisCards />
        
        <Card className="w-full h-96 flex items-center justify-center bg-background/50 backdrop-blur-md border border-white/10">
          <div className="flex flex-col items-center text-default-400 gap-4">
            <Activity size={48} className="opacity-20" />
            <p>Detailed charts module coming soon.</p>
          </div>
        </Card>
      </div>
    </DashboardLayout>
  );
}
