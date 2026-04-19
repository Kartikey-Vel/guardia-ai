"use client";

import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { AnalysisCards } from "@/components/dashboard/AnalysisCards";
import { CameraGrid } from "@/components/dashboard/CameraGrid";
import { InsightPanel } from "@/components/dashboard/InsightPanel";
import { motion, Variants } from "framer-motion";

const container: Variants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.1 }
  }
};

const item: Variants = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 300, damping: 24 } }
};

export default function Home() {
  return (
    <DashboardLayout>
      <motion.div 
        variants={container}
        initial="hidden"
        animate="show"
        className="flex flex-col gap-6 w-full h-full pb-8"
      >
        <motion.div variants={item}>
          <h1 className="text-3xl font-outfit font-bold tracking-tight">System Overview</h1>
          <p className="text-default-500 mt-1">Real-time multimodal surveillance and threat analysis.</p>
        </motion.div>

        <motion.div variants={item}>
          <AnalysisCards />
        </motion.div>

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          <motion.div variants={item} className="xl:col-span-2">
            <CameraGrid />
          </motion.div>
          <motion.div variants={item} className="xl:col-span-1">
            <InsightPanel />
          </motion.div>
        </div>
      </motion.div>
    </DashboardLayout>
  );
}
