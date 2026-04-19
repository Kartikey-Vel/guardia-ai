"use client";

import React, { useEffect, useState } from "react";
import { Card, Chip, Tooltip } from "@heroui/react";
import { Video, VideoOff, Maximize2, MoreHorizontal } from "lucide-react";
import { motion } from "framer-motion";
import { api, APICamera } from "@/lib/api-client";

export function CameraGrid() {
  const [cameras, setCameras] = useState<APICamera[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchCameras = async () => {
      try {
        const data = await api.getCameras();
        setCameras(data);
      } catch (err) {
        console.error("Failed to fetch cameras:", err);
      } finally {
        setIsLoading(false);
      }
    };
    fetchCameras();
  }, []);

  const activeCount = cameras.filter(c => c.is_active).length;

  return (
    <div className="flex flex-col gap-4 mb-6">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-xl font-bold font-outfit uppercase tracking-tight">Security Posture — Live Feeds</h3>
        <Chip variant="soft" color="accent" className="font-bold h-7 uppercase tracking-widest text-[10px]">
          {activeCount} / {cameras.length} Active
        </Chip>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {isLoading ? (
           [1,2,3,4].map(i => (
             <div key={i} className="aspect-video rounded-2xl bg-white/5 animate-pulse border border-white/10" />
           ))
        ) : (
          cameras.map((camera) => (
            <motion.div 
              key={camera.camera_id}
              whileHover={{ scale: 1.01 }}
              transition={{ type: "spring", stiffness: 400, damping: 30 }}
            >
              <Card className="bg-background/40 backdrop-blur-md border border-white/10 shadow-xl overflow-hidden group">
                <div className="flex justify-between items-center px-4 py-3 border-b border-white/5 bg-black/10 dark:bg-white/5">
                  <div className="flex items-center gap-3">
                    <div className={`p-1.5 rounded-lg ${camera.is_active ? 'bg-primary/20 text-primary' : 'bg-default-200 text-default-500'}`}>
                      {camera.is_active ? (
                        <Video size={16} />
                      ) : (
                        <VideoOff size={16} />
                      )}
                    </div>
                    <div className="flex flex-col">
                      <p className="text-sm font-bold leading-tight">{camera.name}</p>
                      <p className="text-[10px] text-default-400 font-bold uppercase tracking-wider">{camera.zone}</p>
                    </div>
                  </div>
                  <div className="flex gap-2 items-center">
                    <Chip 
                      size="sm" 
                      color={camera.is_active ? "success" : "default"}
                      variant="soft"
                      className="text-[10px] font-black uppercase tracking-widest"
                    >
                      {camera.is_active ? "Live" : "Offline"}
                    </Chip>
                  </div>
                </div>
                
                <div className="aspect-video relative overflow-hidden bg-black/60 flex items-center justify-center">
                  {camera.is_active ? (
                    <div className="absolute inset-0 w-full h-full">
                      <motion.img 
                        initial={{ scale: 1.05, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        src={`https://images.unsplash.com/photo-1557597774-9d273605dfa9?auto=format&fit=crop&w=800&q=80`}
                        alt={camera.name}
                        className="w-full h-full object-cover grayscale opacity-40 mix-blend-screen"
                      />
                      <div className="absolute inset-0 bg-gradient-to-t from-black/80 to-transparent pointer-events-none" />
                      
                      {/* Scan line effect */}
                      <div className="absolute inset-0 bg-[linear-gradient(transparent_50%,rgba(0,0,0,0.1)_50%)] bg-[length:100%_4px] pointer-events-none opacity-20" />
                      
                      <div className="absolute inset-0 flex items-center justify-center">
                         <span className="text-white/40 font-black tracking-[0.4em] text-[10px] uppercase backdrop-blur-md px-4 py-1.5 rounded-full bg-black/40 border border-white/5">
                            Stream Intercept Active
                         </span>
                      </div>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center gap-3 text-default-400 p-8 border-2 border-dashed border-white/5 rounded-2xl">
                      <VideoOff size={32} className="opacity-20" />
                      <p className="text-[10px] font-black uppercase tracking-[0.2em]">Signal Lost</p>
                    </div>
                  )}
                  
                  {/* Overlay info */}
                  {camera.is_active && (
                    <div className="absolute top-3 right-3 flex gap-2">
                       <Chip color="accent" size="sm" variant="soft" className="text-[9px] font-bold">RTSP</Chip>
                      {camera.risk_level > 3 && (
                        <Chip color="danger" size="sm" className="backdrop-blur-md bg-danger/80 border-none font-black text-[9px] uppercase tracking-widest shadow-lg">
                          Extreme Risk
                        </Chip>
                      )}
                    </div>
                  )}
                  
                  {/* Recording indicator */}
                  {camera.is_active && (
                    <div className="absolute top-3 left-3 flex items-center gap-2 bg-black/60 backdrop-blur-md px-2.5 py-1 rounded-full border border-white/10 shadow-xl">
                      <motion.div 
                        animate={{ opacity: [1, 0, 1] }} 
                        transition={{ duration: 1.5, repeat: Infinity }}
                        className="w-1.5 h-1.5 rounded-full bg-red-600 shadow-[0_0_10px_rgba(220,38,38,0.8)]" 
                      />
                      <span className="text-[9px] font-black text-white tracking-[0.2em] leading-none">RECORDING</span>
                    </div>
                  )}

                  {camera.is_active && (
                    <div className="absolute bottom-4 left-4 z-20 flex flex-col gap-1">
                       <div className="flex items-center gap-1.5">
                          <div className="w-1.5 h-1.5 rounded-full bg-success animate-pulse" />
                          <span className="text-[10px] font-bold text-white/50 uppercase tracking-widest">Vision Node: {camera.camera_id}</span>
                       </div>
                    </div>
                  )}
                </div>
              </Card>
            </motion.div>
          ))
        )}
      </div>
    </div>
  );
}
