"use client";

import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { Card, Input, Button, Switch, Avatar } from "@heroui/react";
import { User, Bell, Shield, Key } from "lucide-react";
import { useState } from "react";

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState("profile");

  const tabs = [
    { id: "profile", label: "Profile", icon: <User size={18} /> },
    { id: "notifications", label: "Notifications", icon: <Bell size={18} /> },
    { id: "security", label: "Security", icon: <Shield size={18} /> },
    { id: "api", label: "API Keys", icon: <Key size={18} /> },
  ];

  return (
    <DashboardLayout>
      <div className="flex flex-col gap-6 w-full h-full pb-8 max-w-5xl mx-auto">
        <div>
          <h1 className="text-3xl font-outfit font-bold tracking-tight">Configuration Settings</h1>
          <p className="text-default-500 mt-1">Manage Guardia AI preferences and integrations.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 items-start">
          
          {/* Settings Sidebar Tabs */}
          <Card className="col-span-1 p-2 bg-background/50 backdrop-blur-md border border-white/10 flex flex-col gap-1">
             {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors ${
                    activeTab === tab.id 
                      ? "bg-primary text-primary-foreground shadow-md" 
                      : "text-default-500 hover:text-foreground hover:bg-default-100/50"
                  }`}
                >
                  {tab.icon}
                  {tab.label}
                </button>
             ))}
          </Card>

          {/* Settings Content Area */}
          <Card className="md:col-span-3 p-6 bg-background/50 backdrop-blur-md border border-white/10 min-h-[400px]">
            {activeTab === "profile" && (
              <div className="flex flex-col gap-6 animate-in fade-in duration-300">
                 <div className="flex items-center gap-6 pb-6 border-b border-divider/50">
                    <Avatar className="w-20 h-20 text-large">
                      <Avatar.Image src="https://i.pravatar.cc/150?u=a042581f4e29026704d" />
                      <Avatar.Fallback>AD</Avatar.Fallback>
                    </Avatar>
                    <div className="flex flex-col gap-2">
                       <h3 className="text-xl font-bold font-outfit">Admin User</h3>
                       <div className="flex gap-2">
                          <Button size="sm" variant="primary">Change Avatar</Button>
                          <Button size="sm" variant="tertiary">Remove</Button>
                       </div>
                    </div>
                 </div>

                 <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="flex flex-col gap-1.5"><label className="text-sm font-medium">First Name</label><Input defaultValue="Admin" variant="secondary" /></div>
                    <div className="flex flex-col gap-1.5"><label className="text-sm font-medium">Last Name</label><Input defaultValue="User" variant="secondary" /></div>
                    <div className="flex flex-col gap-1.5 sm:col-span-2"><label className="text-sm font-medium">Email Address</label><Input defaultValue="admin@guardia-ai.com" type="email" variant="secondary" /></div>
                 </div>

                 <div className="mt-4 flex justify-end gap-2">
                    <Button variant="tertiary">Cancel</Button>
                    <Button variant="primary">Save Changes</Button>
                 </div>
              </div>
            )}

            {activeTab === "notifications" && (
              <div className="flex flex-col gap-6 animate-in fade-in duration-300">
                 <h3 className="text-xl font-bold font-outfit mb-2">Notification Preferences</h3>
                 
                 <div className="flex flex-col gap-4">
                    <div className="flex items-center justify-between p-4 border border-divider/50 rounded-lg">
                       <div className="flex flex-col gap-1">
                          <span className="font-semibold text-sm">Critical Security Alerts</span>
                          <span className="text-xs text-default-500">Receive SMS and Email immediately.</span>
                       </div>
                       <Switch defaultSelected />
                    </div>

                    <div className="flex items-center justify-between p-4 border border-divider/50 rounded-lg">
                       <div className="flex flex-col gap-1">
                          <span className="font-semibold text-sm">System Health Weekly Updates</span>
                          <span className="text-xs text-default-500">Summary of server uptime and camera health.</span>
                       </div>
                       <Switch defaultSelected />
                    </div>

                    <div className="flex items-center justify-between p-4 border border-divider/50 rounded-lg">
                       <div className="flex flex-col gap-1">
                          <span className="font-semibold text-sm">Marketing & Product Updates</span>
                          <span className="text-xs text-default-500">New features and Guardia AI news.</span>
                       </div>
                       <Switch />
                    </div>
                 </div>
              </div>
            )}

            {activeTab === "security" && (
              <div className="flex flex-col gap-6 animate-in fade-in duration-300">
                 <h3 className="text-xl font-bold font-outfit mb-2">Account Security</h3>
                 <div className="flex flex-col gap-4">
                    <div className="flex flex-col gap-1.5"><label className="text-sm font-medium">Current Password</label><Input type="password" variant="secondary" /></div>
                    <div className="flex flex-col gap-1.5"><label className="text-sm font-medium">New Password</label><Input type="password" variant="secondary" /></div>
                    <div className="flex flex-col gap-1.5"><label className="text-sm font-medium">Confirm Password</label><Input type="password" variant="secondary" /></div>
                    <Button variant="primary" className="self-end mt-2">Update Password</Button>
                 </div>
              </div>
            )}

            {activeTab === "api" && (
              <div className="flex flex-col gap-6 animate-in fade-in duration-300">
                 <h3 className="text-xl font-bold font-outfit mb-2">API Integration</h3>
                 <p className="text-sm text-default-500 mb-2">Manage your Vision API and NLP integration endpoints.</p>

                 <div className="flex flex-col gap-4">
                    <div className="flex flex-col gap-1.5">
                      <label className="text-sm font-medium">Guardia Vision API Key</label>
                      <Input 
                        defaultValue="sk_live_vsn_8d92nd9n29d2nd9n" 
                        type="password" 
                        variant="secondary"
                        readOnly 
                      />
                    </div>
                    <div className="flex gap-2">
                       <Button variant="tertiary" size="sm">Regenerate Key</Button>
                       <Button variant="tertiary" size="sm">Copy</Button>
                    </div>
                 </div>
              </div>
            )}

          </Card>
        </div>
      </div>
    </DashboardLayout>
  );
}
