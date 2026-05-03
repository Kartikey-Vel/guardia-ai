"use client";

import { useEffect, useState } from "react";
import { Card, Chip } from "@heroui/react";
import { Camera, RefreshCw, Video, AlertTriangle } from "lucide-react";
import { motion } from "framer-motion";
import Image from "next/image";
import { api, LiveFrameResponse } from "@/lib/api-client";

export function DeviceCameraFeed() {
  const [cameraReady, setCameraReady] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [cameraKey, setCameraKey] = useState(0);
  const [frame, setFrame] = useState<LiveFrameResponse | null>(null);

  useEffect(() => {
    let cancelled = false;

    const fetchFrame = async () => {
      try {
        const data = await api.getLiveFrame();
        if (cancelled) {
          return;
        }

        setFrame(data);
        setCameraError(data.error);
        setCameraReady(Boolean(data.frame));
      } catch (error) {
        if (cancelled) {
          return;
        }

        const message = error instanceof Error ? error.message : "Unable to load backend camera feed.";
        setCameraError(message);
        setCameraReady(false);
      }
    };

    fetchFrame();
    const interval = window.setInterval(fetchFrame, 1000);

    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [cameraKey]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 260, damping: 24 }}
      className="mb-4"
    >
      <Card className="bg-background/50 backdrop-blur-md border border-white/10 shadow-xl overflow-hidden">
        <div className="flex items-center justify-between gap-3 px-4 py-3 border-b border-white/5 bg-black/10 dark:bg-white/5">
          <div className="flex items-center gap-3">
            <div className="p-1.5 rounded-lg bg-accent/20 text-accent">
              <Camera size={16} />
            </div>
            <div>
              <p className="text-sm font-bold leading-tight">Device Camera</p>
              <p className="text-[10px] text-default-400 font-bold uppercase tracking-wider">
                Browser-local live preview
              </p>
            </div>
          </div>
          <Chip
            size="sm"
            variant="soft"
            color={cameraError ? "danger" : cameraReady ? "success" : "accent"}
            className="text-[10px] font-black uppercase tracking-widest"
          >
            {cameraError ? "Feed Unavailable" : cameraReady ? "Backend Feed Live" : "Loading"}
          </Chip>
        </div>

        <div className="relative aspect-video overflow-hidden bg-black/80">
          {frame?.frame ? (
            <Image
              key={frame.timestamp ?? cameraKey}
              src={frame.frame}
              alt="Backend live camera feed"
              fill
              unoptimized
              sizes="(max-width: 768px) 100vw, 50vw"
              className="object-cover"
            />
          ) : (
            <div className="absolute inset-0 flex items-center justify-center bg-[radial-gradient(circle_at_center,rgba(255,255,255,0.06),transparent_60%)]">
              <div className="flex flex-col items-center gap-3 rounded-2xl border border-white/10 bg-black/55 px-5 py-4 text-center backdrop-blur-md">
                <Video size={28} className="text-white/50" />
                <p className="text-[10px] font-black uppercase tracking-[0.28em] text-white/60">
                  Requesting backend feed
                </p>
              </div>
            </div>
          )}

          {cameraError && (
            <div className="absolute inset-0 flex items-center justify-center bg-black/80 p-6 text-center">
              <div className="max-w-sm rounded-2xl border border-danger/20 bg-danger/10 px-5 py-4 backdrop-blur-md">
                <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-danger/20 text-danger">
                  <AlertTriangle size={18} />
                </div>
                <p className="text-sm font-bold text-foreground">Backend feed is unavailable</p>
                <p className="mt-1 text-xs leading-relaxed text-default-400">
                  {cameraError ?? "The backend camera stream is not ready yet."}
                </p>
                <button
                  type="button"
                  onClick={() => {
                    setCameraError(null);
                    setCameraReady(false);
                    setFrame(null);
                    setCameraKey((currentKey) => currentKey + 1);
                  }}
                  className="mt-4 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/10 px-4 py-2 text-[10px] font-black uppercase tracking-[0.22em] text-white transition-colors hover:bg-white/15"
                >
                  <RefreshCw size={12} />
                  Retry Access
                </button>
              </div>
            </div>
          )}

          <div className="absolute left-4 bottom-4 flex items-center gap-2 rounded-full border border-white/10 bg-black/60 px-3 py-1.5 text-[10px] font-black uppercase tracking-[0.2em] text-white/70 shadow-xl backdrop-blur-md">
            <div className={`h-1.5 w-1.5 rounded-full ${cameraReady ? "bg-success animate-pulse" : "bg-warning"}`} />
            {cameraReady ? "Backend feed streaming" : cameraError ? "Feed unavailable" : "Waiting for backend frame"}
          </div>
        </div>
      </Card>
    </motion.div>
  );
}