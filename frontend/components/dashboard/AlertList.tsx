"use client";

import React, { useState } from "react";
import { Chip, ScrollShadow, Modal, Button } from "@heroui/react";
import { MOCK_ALERTS, SeverityType, MockAlert } from "@/lib/data";
import { AlertCircle, Clock, Info, ShieldAlert, AlertTriangle, ArrowRight, Activity, Bell, MonitorPlay } from "lucide-react";
import { motion } from "framer-motion";

export const getSeverityStyles = (severity: SeverityType): { color: "danger" | "warning" | "accent" | "default", icon: React.ReactNode, bg: string, border: string } => {
  switch (severity) {
    case "CRITICAL":
      return { color: "danger", icon: <ShieldAlert size={16} />, bg: "bg-danger/10 text-danger", border: "border-danger/20" };
    case "HIGH":
      return { color: "warning", icon: <AlertTriangle size={16} />, bg: "bg-warning/10 text-warning", border: "border-warning/20" };
    case "MEDIUM":
      return { color: "accent", icon: <AlertCircle size={16} />, bg: "bg-accent/10 text-accent", border: "border-accent/20" };
    case "LOW":
      return { color: "default", icon: <Info size={16} />, bg: "bg-default-200 text-default-600", border: "border-default-200/50" };
    default:
      return { color: "default", icon: <Info size={16} />, bg: "bg-default-200 text-default-600", border: "border-default-200/50" };
  }
};

export function AlertList() {
  const [selectedAlert, setSelectedAlert] = useState<MockAlert | null>(null);

  const handleClose = () => setSelectedAlert(null);

  return (
    <>
      <div className="flex flex-col w-[350px]">
        <div className="flex justify-between items-center p-4 border-b border-divider/50 bg-background/50 backdrop-blur-md">
          <div className="flex items-center gap-2">
            <Bell size={18} className="text-default-500" />
            <h3 className="text-base font-bold font-outfit">Notifications</h3>
          </div>
          <Chip size="sm" variant="soft" color="danger" className="font-medium animate-pulse">
            {MOCK_ALERTS.filter(a => a.severity === "CRITICAL").length} Critical
          </Chip>
        </div>
        
        <ScrollShadow className="max-h-[400px]">
          <div className="flex flex-col p-2 gap-1.5">
            {MOCK_ALERTS.length === 0 ? (
              <div className="p-8 text-center text-default-400">
                <Activity size={32} className="mx-auto mb-2 opacity-50" />
                <p className="text-sm">No new alerts.</p>
              </div>
            ) : null}
            
            {MOCK_ALERTS.map((alert, idx) => {
              const styles = getSeverityStyles(alert.severity);
              return (
                <div 
                  key={alert.id}
                  onClick={() => setSelectedAlert(alert)}
                  className={`p-3 rounded-lg border ${styles.border} bg-background/40 hover:bg-default-100/50 transition-colors group cursor-pointer`}
                >
                  <div className="flex gap-3">
                    <div className="shrink-0 mt-0.5">
                      <div className={`p-1.5 rounded-md ${styles.bg}`}>
                        {styles.icon}
                      </div>
                    </div>
                    
                    <div className="flex flex-col flex-1 gap-1">
                      <div className="flex justify-between items-start">
                        <p className="font-semibold text-sm leading-tight text-foreground/90 group-hover:text-primary transition-colors">{alert.type}</p>
                        <div className="flex items-center gap-1 text-default-400 text-[10px] uppercase font-semibold">
                          <Clock size={10} />
                          {alert.timestamp}
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-2 mt-0.5">
                        <p className="text-[11px] font-medium text-default-500">{alert.source}</p>
                        <Chip 
                          size="sm" 
                          color={styles.color} 
                          variant="soft"
                          className="h-4 px-1 text-[9px] border-none"
                        >
                          {alert.severity}
                        </Chip>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </ScrollShadow>
        <div className="p-2 border-t border-divider/50 bg-background/50">
          <Button variant="tertiary" className="w-full text-xs font-semibold text-default-500 hover:text-foreground uppercase tracking-widest h-8">
            Mark all as read
          </Button>
        </div>
      </div>

      <Modal isOpen={!!selectedAlert} onOpenChange={(open) => !open && handleClose()}>
        <Modal.Backdrop variant="blur" />
        <Modal.Container placement="center" size="md">
          <Modal.Dialog className="border border-white/10 bg-background/80 backdrop-blur-xl shadow-2xl">
            <Modal.CloseTrigger className="mt-2 mr-2" />
            <Modal.Header>
              <Modal.Heading className="flex items-center gap-2 font-outfit text-xl">
                {selectedAlert && getSeverityStyles(selectedAlert.severity).icon}
                {selectedAlert?.type}
              </Modal.Heading>
            </Modal.Header>
            <Modal.Body className="pb-6">
              <div className="flex flex-col gap-4">
                <div className="flex items-center justify-between border-b border-divider/50 pb-4">
                  <div className="flex flex-col gap-1">
                    <span className="text-xs text-default-500 font-medium uppercase tracking-wider">Source</span>
                    <span className="text-sm font-semibold">{selectedAlert?.source}</span>
                  </div>
                  <div className="flex flex-col gap-1 items-end">
                    <span className="text-xs text-default-500 font-medium uppercase tracking-wider">Time</span>
                    <span className="text-sm font-semibold flex items-center gap-1">
                      <Clock size={14} className="text-default-400" />
                      {selectedAlert?.timestamp}
                    </span>
                  </div>
                </div>
                
                <div className="flex flex-col gap-2">
                  <span className="text-xs text-default-500 font-medium uppercase tracking-wider">Details</span>
                  <p className="text-sm leading-relaxed text-default-600 bg-black/5 dark:bg-white/5 p-4 rounded-xl border border-divider/50">
                    {selectedAlert?.description}
                  </p>
                </div>
                
                <div className="h-[200px] w-full rounded-xl bg-black/20 mt-2 border border-white/5 relative overflow-hidden flex items-center justify-center">
                   {/* Simulated Video Snapshot */}
                   <div className="absolute inset-0 bg-gradient-to-t from-background/80 to-transparent z-10 pointer-events-none" />
                   <MonitorPlay size={32} className="text-default-400 opacity-50 z-0" />
                   <div className="absolute bottom-3 left-3 z-20 flex gap-2">
                      <Chip color="danger" size="sm" className="h-6">REC</Chip>
                      <Chip color="default" variant="soft" size="sm" className="h-6 border-white/10 text-white backdrop-blur-md bg-black/30">00:00:15</Chip>
                   </div>
                </div>
              </div>
            </Modal.Body>
            <Modal.Footer className="border-t border-divider/50">
              <Button variant="tertiary" onPress={handleClose}>
                Close
              </Button>
              <Button variant="primary" onPress={handleClose}>
                Investigate
              </Button>
            </Modal.Footer>
          </Modal.Dialog>
        </Modal.Container>
      </Modal>
    </>
  );
}
