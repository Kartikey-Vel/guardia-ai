"use client";

import React from "react";
import { Card, Chip, ScrollShadow } from "@heroui/react";
import { SeverityType } from "@/lib/data";
import { AlertCircle, Clock, Info, ShieldAlert, AlertTriangle, ArrowRight } from "lucide-react";
import { motion } from "framer-motion";
import { useAlerts } from "@/components/providers/AlertProvider";
import { formatRelativeTime } from "@/lib/time";

const getSeverityStyles = (severity: SeverityType): { color: "danger" | "warning" | "accent" | "default", icon: React.ReactNode, bg: string, border: string } => {
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

const getSeverityLabel = (severity: number): SeverityType => {
  if (severity >= 8) return "CRITICAL";
  if (severity >= 5) return "HIGH";
  if (severity >= 3) return "MEDIUM";
  return "LOW";
};

export function InsightPanel() {
  const { recentAlerts } = useAlerts();
  const criticalCount = recentAlerts.filter((alert) => alert.severity >= 8).length;

  return (
    <Card className="bg-background/50 backdrop-blur-md border border-white/10 h-full shadow-xl flex flex-col">
      <Card.Header className="flex justify-between items-center p-5 border-b border-white/5 shrink-0 bg-black/5 dark:bg-white/5">
        <div className="flex items-center gap-2">
          <div className="p-1.5 bg-primary/20 text-primary rounded-md">
            <AlertCircle size={18} />
          </div>
          <h3 className="text-lg font-bold font-outfit">Recent Incidents</h3>
        </div>
        <Chip size="sm" variant="soft" color="danger" className="font-medium animate-pulse">
          {criticalCount} Critical
        </Chip>
      </Card.Header>
      
      <Card.Content className="p-0 flex-1 overflow-hidden">
        <ScrollShadow className="h-[430px]">
          <div className="flex flex-col p-2 gap-2">
            {recentAlerts.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 px-6 text-center text-default-400">
                <AlertCircle size={32} className="mb-3 opacity-20" />
                <p className="text-sm font-semibold text-foreground/80">No recent incidents yet</p>
                <p className="text-xs mt-1 max-w-xs leading-relaxed">
                  Backend alerts will appear here as soon as detections are raised and broadcast.
                </p>
              </div>
            ) : (
              recentAlerts.map((alert, idx) => {
                const severityLabel = getSeverityLabel(alert.severity);
                const styles = getSeverityStyles(severityLabel);

                return (
                  <motion.div 
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: idx * 0.1 }}
                    key={alert.event_id}
                    className={`p-3.5 rounded-xl border ${styles.border} bg-background/40 hover:bg-default-100/50 transition-colors group cursor-pointer`}
                  >
                    <div className="flex gap-3">
                      <div className="shrink-0 mt-0.5">
                        <div className={`p-2 rounded-lg ${styles.bg}`}>
                          {styles.icon}
                        </div>
                      </div>
                      
                      <div className="flex flex-col flex-1 gap-1">
                        <div className="flex justify-between items-start">
                          <p className="font-semibold text-sm leading-tight text-foreground/90 group-hover:text-primary transition-colors capitalize">
                            {alert.classification.replace(/_/g, " ")}
                          </p>
                          <div className="flex items-center gap-1 text-default-400 text-[10px] uppercase font-semibold">
                            <Clock size={10} />
                            {formatRelativeTime(alert.timestamp)}
                          </div>
                        </div>
                        
                        <div className="flex items-center gap-2 mt-0.5">
                          <p className="text-xs font-medium text-default-500">{alert.camera_id}</p>
                          <Chip 
                            size="sm" 
                            color={styles.color} 
                            variant="soft"
                            className="h-5 text-[10px] border-none"
                          >
                            Sev {alert.severity}
                          </Chip>
                        </div>
                        
                        <p className="text-xs text-default-500 mt-1.5 line-clamp-2 leading-relaxed">{alert.description}</p>
                      </div>
                      
                      <div className="shrink-0 self-center opacity-0 group-hover:opacity-100 transition-opacity -translate-x-2 group-hover:translate-x-0 duration-300">
                        <ArrowRight size={16} className="text-default-400" />
                      </div>
                    </div>
                  </motion.div>
                );
              })
            )}
          </div>
        </ScrollShadow>
      </Card.Content>
      <div className="p-3 border-t border-white/5 text-center bg-black/5 dark:bg-white/5 mt-auto">
        <button className="text-xs font-semibold text-primary hover:text-primary-500 uppercase tracking-widest transition-colors">
          View All Alerts
        </button>
      </div>
    </Card>
  );
}
