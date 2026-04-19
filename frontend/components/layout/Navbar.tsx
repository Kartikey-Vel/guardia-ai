"use client";

import { Button, Badge, Avatar, Popover } from "@heroui/react";
import { Menu, Bell, Search, PanelLeftOpen } from "lucide-react";
import { ThemeToggle } from "./ThemeToggle";
import { usePathname } from "next/navigation";
import { AlertList } from "../dashboard/AlertList";
import { MOCK_ALERTS } from "@/lib/data";

interface NavbarProps {
  onMenuClick: () => void;
  isCollapsed: boolean;
  onCollapse: () => void;
}

export function Navbar({ onMenuClick, isCollapsed, onCollapse }: NavbarProps) {
  const pathname = usePathname();
  
  // Very simple breadcrumb logic
  const getPageTitle = () => {
    if (pathname === "/") return "Dashboard Overview";
    if (pathname.includes("/live-feeds")) return "Live Camera Feeds";
    if (pathname.includes("/alerts")) return "Alerts & Incidents";
    if (pathname.includes("/analytics")) return "System Analytics";
    if (pathname.includes("/settings")) return "Configuration Settings";
    return "Dashboard";
  };

  return (
    <header className="sticky top-0 z-30 w-full h-16 border-b border-divider/50 bg-background/50 backdrop-blur-xl shrink-0">
      <div className="flex h-full items-center px-4 md:px-6 w-full justify-between">
        
        {/* Left section */}
        <div className="flex items-center gap-4 justify-start">
          <Button
            isIconOnly
            variant="tertiary"
            className="md:hidden text-default-600"
            onClick={onMenuClick}
            size="sm"
          >
            <Menu size={20} />
          </Button>
          
          {isCollapsed && (
            <Button 
              isIconOnly 
              variant="tertiary" 
              className="hidden md:flex text-default-500 hover:text-foreground" 
              onClick={onCollapse}
              size="sm"
            >
              <PanelLeftOpen size={18} />
            </Button>
          )}

          <div className="flex flex-col hidden sm:flex">
            <h1 className="font-outfit font-semibold text-lg tracking-tight leading-tight">{getPageTitle()}</h1>
          </div>
        </div>

        {/* Right section */}
        <div className="flex items-center gap-2 sm:gap-4 justify-end">
          <Button isIconOnly variant="tertiary" aria-label="Search" className="text-default-500">
            <Search size={18} />
          </Button>
          
          <Popover>
            <Popover.Trigger>
              <Badge.Anchor>
                <Button isIconOnly variant="tertiary" aria-label="Notifications" className="text-default-500">
                  <Bell size={18} />
                </Button>
                <Badge color="danger" placement="top-right">{MOCK_ALERTS.filter(a => a.severity === "CRITICAL").length}</Badge>
              </Badge.Anchor>
            </Popover.Trigger>
            <Popover.Content className="p-0 border border-white/10 shadow-2xl bg-background/80 backdrop-blur-xl">
              <Popover.Dialog className="p-0 border-none">
                <AlertList />
              </Popover.Dialog>
            </Popover.Content>
          </Popover>
          
          <div className="w-px h-6 bg-divider mx-1" />
          
          <ThemeToggle />
          
          <Avatar size="sm" className="cursor-pointer ml-1 ring-2 ring-primary/20">
            <Avatar.Image 
              src="https://i.pravatar.cc/150?u=a042581f4e29026704d" 
              alt="User" 
            />
            <Avatar.Fallback>JD</Avatar.Fallback>
          </Avatar>
        </div>
      </div>
    </header>
  );
}
