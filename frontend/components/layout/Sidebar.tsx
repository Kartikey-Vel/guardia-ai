"use client";

import { Button, Tooltip } from "@heroui/react";
import { 
  LayoutDashboard, 
  Video, 
  Activity, 
  Settings,
  HelpCircle,
  LogOut,
  ChevronLeft,
  ChevronRight,
  Bell
} from "lucide-react";
import { usePathname } from "next/navigation";
import Link from "next/link";
import { buttonVariants } from "@heroui/styles";
import { cn } from "@heroui/styles";
import { motion, AnimatePresence } from "framer-motion";

interface SidebarProps {
  isMobileOpen: boolean;
  isCollapsed: boolean;
  onCollapse: () => void;
}

export function Sidebar({ isMobileOpen, isCollapsed, onCollapse }: SidebarProps) {
  const pathname = usePathname();

  const navItems = [
    { name: "Dashboard", href: "/", icon: <LayoutDashboard size={20} /> },
    { name: "Live Feeds", href: "/live-feeds", icon: <Video size={20} /> },
    { name: "Analytics", href: "/analytics", icon: <Activity size={20} /> },
    { name: "Settings", href: "/settings", icon: <Settings size={20} /> },
  ];

  const sidebarWidth = isCollapsed ? 80 : 256;

  return (
    <motion.aside
      initial={false}
      animate={{ 
        width: sidebarWidth,
        x: isMobileOpen ? 0 : (isCollapsed ? 0 : 0) // Mobile logic is handled by Tailwind classes below, motion width is for desktop
      }}
      transition={{ type: "spring", bounce: 0, duration: 0.3 }}
      className={cn(
        "fixed inset-y-0 left-0 z-40 transform border-r border-divider bg-background/60 backdrop-blur-xl transition-transform duration-300 ease-in-out md:static md:translate-x-0 flex flex-col shrink-0",
        isMobileOpen ? "translate-x-0 w-64" : "-translate-x-full md:w-auto" // Fallback widths
      )}
    >
      <div className={cn("flex items-center h-16 shrink-0", isCollapsed ? "justify-center px-4" : "justify-between px-6")}>
        {!isCollapsed && (
          <motion.div 
            initial={{ opacity: 0 }} 
            animate={{ opacity: 1 }} 
            exit={{ opacity: 0 }}
            className="flex items-center gap-2"
          >
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-primary to-accent flex items-center justify-center text-white shadow-lg shadow-primary/30">
              <span className="font-outfit font-bold text-lg">G</span>
            </div>
            <span className="font-outfit font-bold text-lg tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-foreground to-foreground/70">GUARDIA</span>
          </motion.div>
        )}
        
        {isCollapsed && (
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-primary to-accent flex items-center justify-center text-white shadow-md">
            <span className="font-outfit font-bold text-lg">G</span>
          </div>
        )}

        {/* Desktop collapse toggle */}
        {!isCollapsed && (
          <Button 
            isIconOnly 
            variant="tertiary" 
            size="sm" 
            onClick={onCollapse}
            className="hidden md:flex text-default-400 hover:text-foreground"
          >
            <ChevronLeft size={18} />
          </Button>
        )}
      </div>

      <div className="flex flex-col gap-6 px-3 py-6 flex-1 overflow-y-auto scrollbar-hide">
        <div className="flex flex-col gap-2">
          {!isCollapsed && (
            <p className="px-3 text-[10px] font-bold text-default-400 uppercase tracking-widest mb-1 font-outfit">
              Menu
            </p>
          )}
          
          {navItems.map((item) => {
            const isActive = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
            
            const linkContent = (
              <Link
                key={item.name}
                href={item.href}
                className={cn(
                  buttonVariants({ variant: isActive ? "primary" : "tertiary" }),
                  "relative flex items-center h-10 w-full transition-all duration-200 overflow-hidden group",
                  isCollapsed ? "justify-center px-0 w-10 mx-auto" : "justify-start px-3",
                  isActive ? "bg-primary/10 text-primary hover:bg-primary/20" : "text-default-500 hover:text-foreground hover:bg-default-100/50"
                )}
              >
                {isActive && !isCollapsed && (
                  <motion.div
                    layoutId="sidebar-active-indicator"
                    className="absolute left-0 w-1 h-6 bg-primary rounded-r-full"
                  />
                )}
                
                <span className={cn("flex items-center justify-center", isCollapsed ? "" : "w-6 h-6 mr-3")}>
                  {item.icon}
                </span>
                
                {!isCollapsed && (
                  <span className="font-medium text-sm truncate">{item.name}</span>
                )}
              </Link>
            );

            return isCollapsed ? (
              <Tooltip key={item.name}>
                <Tooltip.Trigger>
                  {linkContent}
                </Tooltip.Trigger>
                <Tooltip.Content placement="right" showArrow className="font-outfit text-xs font-semibold">
                  {item.name}
                </Tooltip.Content>
              </Tooltip>
            ) : linkContent;
          })}
        </div>
      </div>

      <div className="p-3 mt-auto shrink-0 flex flex-col gap-2">
        <div className="mb-2 h-px w-full bg-divider/50" />
        
        {isCollapsed ? (
          <>
            <Tooltip>
              <Tooltip.Trigger>
                <Button isIconOnly variant="tertiary" className="w-10 h-10 mx-auto text-default-500 hover:text-foreground">
                  <HelpCircle size={20} />
                </Button>
              </Tooltip.Trigger>
              <Tooltip.Content placement="right" showArrow className="font-outfit text-xs font-semibold">
                Help & Support
              </Tooltip.Content>
            </Tooltip>

            <Tooltip>
              <Tooltip.Trigger>
                <Button isIconOnly variant="tertiary" className="w-10 h-10 mx-auto text-danger hover:text-danger-fg">
                  <LogOut size={20} />
                </Button>
              </Tooltip.Trigger>
              <Tooltip.Content placement="right" showArrow className="bg-danger text-white font-outfit text-xs font-semibold">
                Logout
              </Tooltip.Content>
            </Tooltip>
          </>
        ) : (
          <>
            <Button variant="tertiary" className="justify-start px-3 text-default-500 hover:text-foreground">
              <span className="w-6 h-6 mr-3 flex items-center justify-center"><HelpCircle size={20} /></span>
              <span className="font-medium text-sm">Help & Support</span>
            </Button>
            <Button variant="tertiary" className="justify-start px-3 text-danger/80 hover:text-danger">
              <span className="w-6 h-6 mr-3 flex items-center justify-center"><LogOut size={20} /></span>
              <span className="font-medium text-sm">Logout</span>
            </Button>
          </>
        )}
      </div>
    </motion.aside>
  );
}
