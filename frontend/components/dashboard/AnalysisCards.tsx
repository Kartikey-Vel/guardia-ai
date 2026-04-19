"use client";

import React, { useEffect, useState } from "react";
import { Card } from "@heroui/react";
import { 
  AlertTriangle, ShieldCheck, Activity, MonitorPlay, TrendingUp, TrendingDown, Minus
} from "lucide-react";
import { motion } from "framer-motion";
import { api, AnalyticsSummary } from "@/lib/api-client";
import { useAlerts } from "@/components/providers/AlertProvider";

const iconMap = {
  AlertTriangle,
  ShieldCheck,
  Activity,
  MonitorPlay,
};

export function AnalysisCards() {
  const { alerts, isConnected } = useAlerts();
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);

  useEffect(() => {
    const fetchSummary = async () => {
      try {
        const data = await api.getAnalyticsSummary();
        setSummary(data);
      } catch (err) {
        console.error("Failed to fetch summary:", err);
      }
    };
    
    fetchSummary();
    const interval = setInterval(fetchSummary, 30000); // 30s poll for summary
    return () => clearInterval(interval);
  }, []);

  const insights = [
    {
      title: "Total Anomalies",
      value: summary?.total_events ?? 0,
      description: "Detected in the last 24h",
      trend: "up",
      icon: "AlertTriangle",
      color: "danger"
    },
    {
      title: "System Status",
      value: isConnected ? "Optimal" : "Disconnected",
      description: isConnected ? "Stable latency < 50ms" : "Re-establishing link...",
      icon: "ShieldCheck",
      color: "success"
    },
    {
      title: "Active Cameras",
      value: `${summary?.cameras_active ?? 0} Active`,
      description: "Across all monitored zones",
      trend: "neutral",
      icon: "MonitorPlay",
      color: "primary"
    },
    {
      title: "AI Integrity",
      value: summary ? `${Math.round(summary.avg_severity * 10)}%` : "...",
      description: "Mean severity weighting",
      trend: "down",
      icon: "Activity",
      color: "warning"
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
      {insights.map((insight, idx) => {
        const Icon = iconMap[insight.icon as keyof typeof iconMap] || Activity;
        
        return (
          <motion.div 
            key={idx}
            whileHover={{ y: -4, scale: 1.01 }}
            transition={{ type: "spring", stiffness: 400, damping: 25 }}
          >
            <Card className="border border-white/10 dark:border-white/5 bg-background/50 backdrop-blur-md shadow-lg shadow-black/5 overflow-hidden">
               <div className={`absolute top-0 left-0 w-full h-0.5 bg-${insight.color}/30`} />
              <Card.Header className="flex flex-row items-center justify-between pb-2 px-4 pt-4">
                <p className="text-[10px] font-bold text-default-400 uppercase tracking-widest leading-none">{insight.title}</p>
                <div className={`p-1.5 rounded-lg bg-${insight.color}/10 text-${insight.color}`}>
                  <Icon size={16} />
                </div>
              </Card.Header>
              <Card.Content className="pb-4 px-4">
                <div className="flex items-end gap-2">
                  <h4 className="text-2xl font-bold font-outfit tracking-tighter">{insight.value}</h4>
                  <div className={`flex items-center text-[10px] font-bold mb-1 px-1.5 py-0.5 rounded-full ${
                    insight.trend === "up" ? "bg-danger/10 text-danger" : 
                    insight.trend === "down" ? "bg-success/10 text-success" : 
                    "bg-white/5 text-default-400"
                  }`}>
                    {insight.trend === "up" && <TrendingUp size={10} className="mr-1" />}
                    {insight.trend === "down" && <TrendingDown size={10} className="mr-1" />}
                    {insight.trend === "neutral" && <Minus size={10} className="mr-1" />}
                    {insight.trend === "up" ? "LIVE" : insight.trend === "down" ? "SYNC" : "0%"}
                  </div>
                </div>
                <p className="text-[10px] font-medium text-default-400 mt-1 opacity-70 uppercase tracking-tight">{insight.description}</p>
              </Card.Content>
            </Card>
          </motion.div>
        );
      })}
    </div>
  );
}

