"use client";

import { useState } from "react";
import { Navbar } from "./Navbar";
import { Sidebar } from "./Sidebar";
import { motion, AnimatePresence } from "framer-motion";

export function DashboardLayout({ children }: { children: React.ReactNode }) {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);

  return (
    <div className="flex h-screen overflow-hidden bg-background relative selection:bg-primary/30">
      {/* Decorative Background Elements */}
      <div className="fixed inset-0 z-0 pointer-events-none opacity-40 dark:opacity-20 overflow-hidden mix-blend-screen overflow-hidden hidden md:block">
        <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-primary/20 rounded-full blur-[120px] -translate-y-1/2 translate-x-1/3" />
        <div className="absolute bottom-0 left-0 w-[600px] h-[600px] bg-accent/20 rounded-full blur-[150px] translate-y-1/3 -translate-x-1/3" />
      </div>

      {/* Mobile sidebar backdrop */}
      <AnimatePresence>
        {isMobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-30 bg-black/60 backdrop-blur-sm md:hidden"
            onClick={() => setIsMobileMenuOpen(false)}
          />
        )}
      </AnimatePresence>

      <Sidebar 
        isMobileOpen={isMobileMenuOpen} 
        isCollapsed={isCollapsed} 
        onCollapse={() => setIsCollapsed(!isCollapsed)}
      />

      <div className="flex flex-1 flex-col overflow-hidden z-10 relative">
        <Navbar 
          onMenuClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)} 
          isCollapsed={isCollapsed}
          onCollapse={() => setIsCollapsed(!isCollapsed)}
        />
        
        <main className="flex-1 overflow-x-hidden overflow-y-auto p-4 md:p-6 lg:p-8 bg-transparent scrollbar-hide">
          <div className="mx-auto max-w-7xl h-full">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
