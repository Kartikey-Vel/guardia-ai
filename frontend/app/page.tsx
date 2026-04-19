import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { AnalysisCards } from "@/components/dashboard/AnalysisCards";
import { CameraGrid } from "@/components/dashboard/CameraGrid";
import { InsightPanel } from "@/components/dashboard/InsightPanel";

export default function Home() {
  return (
    <DashboardLayout>
      <div className="flex flex-col gap-6 w-full h-full pb-8">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">System Overview</h1>
          <p className="text-default-500">Real-time surveillance and analysis metrics.</p>
        </div>

        <AnalysisCards />

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          <div className="xl:col-span-2">
            <CameraGrid />
          </div>
          <div className="xl:col-span-1">
            <InsightPanel />
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
