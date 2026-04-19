"use client";

import { Card, Chip, Tooltip } from "@heroui/react";
import { MOCK_CAMERAS } from "@/lib/data";
import { Video, VideoOff, Maximize2, MoreHorizontal } from "lucide-react";
import { motion } from "framer-motion";

export function CameraGrid() {
  return (
    <div className="flex flex-col gap-4 mb-6">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-xl font-bold font-outfit">Live Feeds</h3>
        <Chip variant="soft" color="accent" className="font-medium h-7">
          {MOCK_CAMERAS.filter(c => c.status === "active").length} Active
        </Chip>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {MOCK_CAMERAS.map((camera, idx) => (
          <motion.div 
            key={camera.id}
            whileHover={{ scale: 1.01 }}
            transition={{ type: "spring", stiffness: 400, damping: 30 }}
          >
            <Card className="bg-background/40 backdrop-blur-md border border-white/10 shadow-xl overflow-hidden group">
              <div className="flex justify-between items-center px-4 py-3 border-b border-white/5 bg-black/5 dark:bg-white/5">
                <div className="flex items-center gap-3">
                  <div className={`p-1.5 rounded-lg ${camera.status === 'active' ? 'bg-primary/20 text-primary' : 'bg-default-200 text-default-500'}`}>
                    {camera.status === "active" ? (
                      <Video size={16} />
                    ) : (
                      <VideoOff size={16} />
                    )}
                  </div>
                  <div className="flex flex-col">
                    <p className="text-sm font-semibold leading-tight">{camera.name}</p>
                    <p className="text-[10px] text-default-500 font-medium uppercase tracking-wider">{camera.zone}</p>
                  </div>
                </div>
                <div className="flex gap-2 items-center">
                  <Chip 
                    size="sm" 
                    color={camera.status === "active" ? "success" : "default"}
                    variant="soft"
                    className="border-none"
                  >
                    {camera.status === "active" ? "Live" : "Offline"}
                  </Chip>
                  <Tooltip>
                    <Tooltip.Trigger>
                      <button className="text-default-400 hover:text-foreground transition-colors p-1">
                        <MoreHorizontal size={16} />
                      </button>
                    </Tooltip.Trigger>
                    <Tooltip.Content placement="top">
                      More options
                    </Tooltip.Content>
                  </Tooltip>
                </div>
              </div>
              
              <div className="aspect-video relative overflow-hidden bg-content2/50 flex items-center justify-center">
                {camera.status === "active" ? (
                  <div className="absolute inset-0 w-full h-full">
                    {/* Placeholder image for feed */}
                    <motion.img 
                      initial={{ scale: 1.05 }}
                      animate={{ scale: 1 }}
                      transition={{ duration: 1 }}
                      src={`https://images.unsplash.com/photo-1557597774-9d273605dfa9?auto=format&fit=crop&w=600&q=80`}
                      alt={camera.name}
                      className="w-full h-full object-cover dark:opacity-80"
                      onError={(e) => {
                        e.currentTarget.style.display = 'none';
                      }}
                    />
                    {/* Gradient Overlay for better text legibility */}
                    <div className="absolute inset-x-0 top-0 h-1/3 bg-gradient-to-b from-black/60 to-transparent pointer-events-none" />
                    
                    {/* Scan line effect */}
                    <div className="absolute inset-0 bg-[linear-gradient(transparent_50%,rgba(0,0,0,0.1)_50%)] bg-[length:100%_4px] pointer-events-none opacity-20" />
                    
                    <div className="absolute inset-0 flex items-center justify-center">
                       <span className="text-white/60 font-medium tracking-[0.2em] text-xs uppercase backdrop-blur-md px-3 py-1 rounded-full bg-black/30 border border-white/10">Simulated Feed</span>
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-col items-center gap-3 text-default-400">
                    <VideoOff size={32} className="opacity-50" />
                    <p className="text-sm font-medium">Connection Lost</p>
                  </div>
                )}
                
                {/* Overlay info */}
                {camera.status === "active" && (
                  <div className="absolute top-3 right-3 flex gap-2">
                    {camera.riskLevel > 3 && (
                      <Chip color="danger" size="sm" className="backdrop-blur-md bg-danger/80 border-none font-medium shadow-lg">
                        High Risk
                      </Chip>
                    )}
                  </div>
                )}
                
                {/* Recording indicator */}
                {camera.status === "active" && (
                  <div className="absolute top-3 left-3 flex items-center gap-2 bg-black/40 backdrop-blur-md px-2 py-1 rounded-md border border-white/10">
                    <motion.div 
                      animate={{ opacity: [1, 0.4, 1] }} 
                      transition={{ duration: 2, repeat: Infinity }}
                      className="w-2 h-2 rounded-full bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.8)]" 
                    />
                    <span className="text-[10px] font-bold text-white tracking-widest leading-none">REC</span>
                  </div>
                )}

                {/* Expand button on hover */}
                {camera.status === "active" && (
                  <div className="absolute bottom-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity">
                     <button className="p-2 bg-black/50 hover:bg-black/70 backdrop-blur-md rounded-lg text-white border border-white/20 transition-colors">
                       <Maximize2 size={16} />
                     </button>
                  </div>
                )}
              </div>
            </Card>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
