"use client";

import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { Card } from "@heroui/react";

export default function SettingsPage() {
  return (
    <DashboardLayout>
      <div className="flex flex-col gap-6 w-full h-full pb-8">
        <div>
          <h1 className="text-3xl font-outfit font-bold tracking-tight">Configuration Settings</h1>
          <p className="text-default-500 mt-1">Manage Guardia AI preferences and integrations.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
           <Card className="p-6 bg-background/50 backdrop-blur-md border border-white/10">
              <h3 className="font-bold text-lg mb-4">Profile Settings</h3>
              <p className="text-sm text-default-500">Configure your personal account.</p>
           </Card>
           <Card className="p-6 bg-background/50 backdrop-blur-md border border-white/10">
              <h3 className="font-bold text-lg mb-4">System Integration</h3>
              <p className="text-sm text-default-500">Manage camera and NLP API keys.</p>
           </Card>
        </div>
      </div>
    </DashboardLayout>
  );
}
