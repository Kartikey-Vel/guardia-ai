"use client";

import { Card, Chip, Separator } from "@heroui/react";
import { MOCK_CAMERAS } from "@/lib/data";
import { Video, VideoOff } from "lucide-react";

export function CameraGrid() {
  return (
    <div className="flex flex-col gap-4 mb-6">
      <div className="flex items-center justify-between">
        <h3 className="text-xl font-bold">Live Feeds</h3>
        <Chip variant="soft" color="accent">
          {MOCK_CAMERAS.filter(c => c.status === "active").length} Active
        </Chip>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {MOCK_CAMERAS.map((camera) => (
          <Card key={camera.id} className="bg-background border-none shadow-sm">
            <Card.Header className="flex justify-between items-center p-4 pb-2">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded bg-default-100">
                  {camera.status === "active" ? (
                    <Video size={16} className="text-primary" />
                  ) : (
                    <VideoOff size={16} className="text-default-400" />
                  )}
                </div>
                <div className="flex flex-col">
                  <p className="text-sm font-semibold">{camera.name}</p>
                  <p className="text-xs text-default-500">{camera.zone}</p>
                </div>
              </div>
              <Chip 
                size="sm" 
                color={camera.status === "active" ? "success" : "default"}
                variant="soft"
              >
                {camera.status === "active" ? "Live" : "Offline"}
              </Chip>
            </Card.Header>
            <Separator />
            <Card.Content className="p-0 overflow-hidden relative group">
              <div className="aspect-video bg-content2 flex items-center justify-center relative">
                {camera.status === "active" ? (
                  <div className="absolute inset-0 bg-default-200 animate-pulse">
                    <img 
                      src={`https://images.unsplash.com/photo-1557597774-9d273605dfa9?auto=format&fit=crop&w=600&q=80`}
                      alt={camera.name}
                      className="w-full h-full object-cover opacity-80 mix-blend-overlay dark:opacity-60"
                      onError={(e) => {
                        e.currentTarget.style.display = 'none';
                      }}
                    />
                    <div className="absolute inset-0 flex items-center justify-center">
                      <span className="text-default-400 font-medium tracking-widest text-sm uppercase">Simulated Feed</span>
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-col items-center gap-2 text-default-400">
                    <VideoOff size={32} />
                    <p className="text-sm">Connection Lost</p>
                  </div>
                )}
                
                {/* Overlay info */}
                {camera.status === "active" && (
                  <div className="absolute top-2 right-2 flex gap-2">
                    {camera.riskLevel > 3 && (
                      <Chip color="danger" size="sm" variant="soft" className="backdrop-blur-md">
                        High Risk Zone
                      </Chip>
                    )}
                  </div>
                )}
                
                {/* Recording indicator */}
                {camera.status === "active" && (
                  <div className="absolute top-3 left-3 flex items-center gap-1.5">
                    <div className="w-2 h-2 rounded-full bg-danger animate-pulse" />
                    <span className="text-[10px] font-bold text-white drop-shadow-md">REC</span>
                  </div>
                )}
              </div>
            </Card.Content>
          </Card>
        ))}
      </div>
    </div>
  );
}
