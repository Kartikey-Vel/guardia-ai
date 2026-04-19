"use client";

import { Card, Chip } from "@heroui/react";
import { Activity, Server, Database, ShieldAlert, Cpu } from "lucide-react";
import { motion } from "framer-motion";

const hourlyData = [
  { time: "12am", value: 12 }, { time: "2am", value: 5 }, { time: "4am", value: 2 },
  { time: "6am", value: 8 }, { time: "8am", value: 35 }, { time: "10am", value: 42 },
  { time: "12pm", value: 28 }, { time: "2pm", value: 30 }, { time: "4pm", value: 45 },
  { time: "6pm", value: 50 }, { time: "8pm", value: 25 }, { time: "10pm", value: 15 },
];

export function PerformanceMetrics() {
  const maxValue = Math.max(...hourlyData.map(d => d.value));

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Main Chart */}
      <Card className="lg:col-span-2 col-span-1 p-6 bg-background/50 backdrop-blur-md border border-white/10 shadow-xl">
        <div className="flex justify-between items-start mb-8">
          <div>
            <h3 className="text-xl font-bold font-outfit">Detection Volume</h3>
            <p className="text-default-500 text-sm mt-1">Anomalies detected over the last 24 hours.</p>
          </div>
          <Chip color="accent" variant="soft" size="sm">Today</Chip>
        </div>
        
        <div className="h-[250px] w-full flex items-end justify-between gap-1 sm:gap-2">
          {hourlyData.map((d, i) => {
            const height = (d.value / maxValue) * 100;
            return (
              <div key={i} className="flex flex-col items-center flex-1 gap-2 group">
                <div className="w-full relative flex items-end h-[200px] rounded-t-sm group-hover:bg-default-100/50 transition-colors">
                  <motion.div 
                    initial={{ height: 0 }}
                    animate={{ height: `${height}%` }}
                    transition={{ duration: 1.2, delay: i * 0.05, type: "spring", bounce: 0.2 }}
                    className="w-full bg-gradient-to-t from-primary/20 to-primary rounded-t-sm relative"
                  >
                    <div className="absolute -top-8 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity bg-black text-white text-xs py-1 px-2 rounded font-semibold whitespace-nowrap shadow-lg">
                      {d.value} events
                    </div>
                  </motion.div>
                </div>
                <span className="text-[10px] sm:text-xs text-default-400 font-medium">{d.time}</span>
              </div>
            );
          })}
        </div>
      </Card>

      {/* Resource Allocation */}
      <Card className="p-6 bg-background/50 backdrop-blur-md border border-white/10 shadow-xl flex flex-col gap-6">
        <div>
          <h3 className="text-xl font-bold font-outfit">System Health</h3>
          <p className="text-default-500 text-sm mt-1">Live infrastructure resource usage.</p>
        </div>

        <div className="flex flex-col gap-5 flex-1 justify-center">
          {[
            { label: "AI Engine Processing", value: 78, icon: <Cpu size={16} />, color: "primary" },
            { label: "Memory (RAM)", value: 45, icon: <Database size={16} />, color: "success" },
            { label: "Storage Capacity", value: 92, icon: <Server size={16} />, color: "danger" },
            { label: "Active Connections", value: 65, icon: <Activity size={16} />, color: "warning" },
          ].map((stat, i) => (
            <div key={i} className="flex flex-col gap-2">
              <div className="flex justify-between items-center">
                <div className="flex items-center gap-2 text-sm font-semibold">
                  <span className={`text-${stat.color}`}>{stat.icon}</span>
                  {stat.label}
                </div>
                <span className="text-sm font-bold font-outfit">{stat.value}%</span>
              </div>
              <div className="w-full h-2 rounded-full bg-default-100 overflow-hidden">
                <motion.div 
                  initial={{ width: 0 }}
                  animate={{ width: `${stat.value}%` }}
                  transition={{ duration: 1.5, delay: i * 0.2 }}
                  className={`h-full bg-${stat.color} rounded-full`}
                />
              </div>
            </div>
          ))}
        </div>
        
        <div className="mt-auto pt-4 border-t border-divider/50 flex justify-between items-center text-sm">
           <span className="text-default-500 flex items-center gap-1"><ShieldAlert size={14} className="text-success" /> All Systems Nominal</span>
        </div>
      </Card>
    </div>
  );
}
