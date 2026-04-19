"use client";

import React, { useState } from "react";
import { Chip, ScrollShadow, Modal, Button } from "@heroui/react";
import { useAlerts } from "@/components/providers/AlertProvider";
import { APIEvent } from "@/lib/api-client";
import { AlertCircle, Clock, ShieldAlert, AlertTriangle, Bell, MonitorPlay, CheckCircle } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export const getSeverityStyles = (severity: number): { color: "danger" | "warning" | "success" | "default", icon: React.ReactNode, bg: string, border: string } => {
  if (severity >= 8) {
    return { color: "danger", icon: <ShieldAlert size={16} />, bg: "bg-danger/10 text-danger", border: "border-danger/20" };
  } else if (severity >= 5) {
    return { color: "warning", icon: <AlertTriangle size={16} />, bg: "bg-warning/10 text-warning", border: "border-warning/20" };
  } else if (severity >= 3) {
    return { color: "success", icon: <AlertCircle size={16} />, bg: "bg-success/10 text-success", border: "border-success/20" };
  }
  return { color: "default", icon: <Clock size={16} />, bg: "bg-default-200 text-default-600", border: "border-default-200/50" };
};

const formatTime = (timestamp: string) => {
  const date = new Date(timestamp);
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
};

export function AlertList() {
  const { alerts, isConnected, markAsReviewed } = useAlerts();
  const [selectedAlert, setSelectedAlert] = useState<APIEvent | null>(null);

  const handleClose = () => setSelectedAlert(null);

  return (
    <>
      <div className="flex flex-col w-[350px] border-l border-divider/50 bg-background/30 backdrop-blur-md h-full">
        <div className="flex justify-between items-center p-4 border-b border-divider/50 bg-background/50">
          <div className="flex items-center gap-2">
            <Bell size={18} className={isConnected ? "text-primary" : "text-danger animate-pulse"} />
            <h3 className="text-base font-bold font-outfit uppercase tracking-wider">Live Alerts</h3>
          </div>
          <div className="flex items-center gap-2">
            <div className={`h-2 w-2 rounded-full ${isConnected ? 'bg-success' : 'bg-danger'} animate-pulse`} />
            <span className="text-[10px] font-bold text-default-400 uppercase">
              {isConnected ? "Live" : "Offline"}
            </span>
          </div>
        </div>
        
        <ScrollShadow className="flex-1">
          <div className="flex flex-col p-2 gap-2">
            <AnimatePresence initial={false}>
              {alerts.length === 0 ? (
                <motion.div 
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="p-12 text-center text-default-400"
                >
                  <MonitorPlay size={32} className="mx-auto mb-2 opacity-20" />
                  <p className="text-sm font-medium">Monitoring for threats...</p>
                </motion.div>
              ) : (
                alerts.map((alert) => {
                  const styles = getSeverityStyles(alert.severity);
                  return (
                    <motion.div 
                      key={alert.event_id}
                      layout
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, scale: 0.95 }}
                      onClick={() => setSelectedAlert(alert)}
                      className={`p-3 rounded-xl border ${styles.border} ${alert.is_reviewed ? 'bg-background/20 opacity-50' : 'bg-background/60 shadow-lg shadow-black/20'} hover:bg-default-100/50 transition-all group cursor-pointer relative overflow-hidden`}
                    >
                      {!alert.is_reviewed && (
                        <div className={`absolute top-0 left-0 w-1 h-full ${styles.bg}`} />
                      )}
                      <div className="flex gap-3">
                        <div className="shrink-0">
                          <div className={`p-2 rounded-lg ${styles.bg}`}>
                            {styles.icon}
                          </div>
                        </div>
                        
                        <div className="flex flex-col flex-1 gap-1">
                          <div className="flex justify-between items-start">
                            <p className="font-bold text-sm leading-tight text-foreground/90 capitalize">
                              {alert.classification.replace(/_/g, ' ')}
                            </p>
                            <span className="text-[10px] font-bold text-default-400">
                              {formatTime(alert.timestamp)}
                            </span>
                          </div>
                          
                          <div className="flex items-center gap-2 mt-0.5">
                            <p className="text-[11px] font-bold text-primary/80 uppercase tracking-tighter">{alert.camera_id}</p>
                            <Chip 
                              size="sm" 
                              color={styles.color} 
                              variant="soft"
                              className="h-4 px-1.5 text-[9px] font-bold uppercase tracking-widest"
                            >
                              Sev {alert.severity}
                            </Chip>
                          </div>
                        </div>
                      </div>
                    </motion.div>
                  );
                })
              )}
            </AnimatePresence>
          </div>
        </ScrollShadow>

        <div className="p-3 border-t border-divider/50 bg-background/50">
          <p className="text-[10px] text-center text-default-400 font-bold uppercase tracking-widest">
            Showing {alerts.length} signals
          </p>
        </div>
      </div>

      <Modal isOpen={!!selectedAlert} onOpenChange={(open) => !open && handleClose()}>
        <Modal.Backdrop variant="blur" />
        <Modal.Container placement="center" size="md">
          <Modal.Dialog className="border border-white/10 bg-background/80 backdrop-blur-xl shadow-2xl overflow-hidden">
            <Modal.CloseTrigger className="mt-2 mr-2" />
            <Modal.Header>
              <Modal.Heading className="flex items-center gap-3 font-outfit text-2xl uppercase tracking-tight">
                {selectedAlert && getSeverityStyles(selectedAlert.severity).icon}
                {selectedAlert?.classification.replace(/_/g, ' ')}
              </Modal.Heading>
            </Modal.Header>
            <Modal.Body className="pb-6">
              <div className="flex flex-col gap-6">
                <div className="flex items-center justify-between bg-white/5 p-4 rounded-2xl border border-divider/50">
                  <div className="flex flex-col gap-1">
                    <span className="text-[10px] text-default-400 font-bold uppercase tracking-widest">Origin</span>
                    <span className="text-sm font-bold text-primary">{selectedAlert?.camera_id}</span>
                  </div>
                  <div className="flex flex-col gap-1 items-end">
                    <span className="text-[10px] text-default-400 font-bold uppercase tracking-widest">Detected At</span>
                    <span className="text-sm font-bold flex items-center gap-1.5">
                      <Clock size={14} className="text-default-400" />
                      {selectedAlert && formatTime(selectedAlert.timestamp)}
                    </span>
                  </div>
                </div>
                
                <div className="flex flex-col gap-2">
                  <span className="text-[10px] text-default-400 font-bold uppercase tracking-widest">AI Intelligence</span>
                  <div className="text-sm leading-relaxed text-foreground/80 bg-black/30 p-5 rounded-2xl border border-white/5 font-medium shadow-inner">
                    {selectedAlert?.description}
                  </div>
                </div>

                {selectedAlert?.attribution && (
                   <div className="grid grid-cols-2 gap-3">
                      {Object.entries(selectedAlert.attribution).map(([key, value]) => (
                        <div key={key} className="bg-white/5 px-3 py-2 rounded-xl border border-white/5 flex justify-between items-center">
                           <span className="text-[10px] text-default-400 font-bold uppercase">{key.replace(/_/g, ' ')}</span>
                           <span className="text-[11px] font-bold text-foreground/80">{String(value)}</span>
                        </div>
                      ))}
                   </div>
                )}
                
                <div className="h-[220px] w-full rounded-2xl bg-black/40 border border-white/10 relative overflow-hidden flex items-center justify-center group">
                   <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent z-10" />
                   <MonitorPlay size={48} className="text-white/20 group-hover:text-primary/40 transition-colors z-0" />
                   <div className="absolute top-4 left-4 z-20 flex gap-2">
                      <div className="bg-red-600 px-2 py-0.5 rounded text-[10px] font-black animate-pulse">REC</div>
                      <div className="bg-black/40 backdrop-blur-md px-2 py-0.5 rounded text-[10px] font-bold border border-white/10">{selectedAlert?.camera_id}</div>
                   </div>
                   <div className="absolute bottom-4 right-4 z-20">
                      <Chip size="sm" variant="soft" color="accent" className="font-bold text-[10px]">AI ANALYSIS ACTIVE</Chip>
                   </div>
                </div>
              </div>
            </Modal.Body>
            <Modal.Footer className="border-t border-divider/50 bg-white/5 px-6 py-4">
              <Button variant="tertiary" onPress={handleClose} className="font-bold uppercase tracking-widest text-[11px]">
                Dismiss
              </Button>
              {!selectedAlert?.is_reviewed && (
                <Button 
                  variant="primary" 
                  className="bg-success text-white font-bold uppercase tracking-widest text-[11px] shadow-lg shadow-success/20 flex items-center gap-2"
                  onPress={() => {
                    if (selectedAlert) markAsReviewed(selectedAlert.event_id);
                    handleClose();
                  }}
                >
                  <CheckCircle size={16} />
                  Confirm Review
                </Button>
              )}
            </Modal.Footer>
          </Modal.Dialog>
        </Modal.Container>
      </Modal>
    </>
  );
}
