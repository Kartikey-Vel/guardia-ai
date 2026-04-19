"use client";

import { Button } from "@heroui/react";
import { 
  LayoutDashboard, 
  Video, 
  Activity, 
  Settings,
  HelpCircle
} from "lucide-react";
import { usePathname } from "next/navigation";
import Link from "next/link";
import { buttonVariants } from "@heroui/styles";
import { cn } from "@heroui/styles";

interface SidebarProps {
  isOpen: boolean;
}

export function Sidebar({ isOpen }: SidebarProps) {
  const pathname = usePathname();

  const navItems = [
    { name: "Dashboard", href: "/", icon: <LayoutDashboard size={20} /> },
    { name: "Live Feeds", href: "#", icon: <Video size={20} /> },
    { name: "Analytics", href: "#", icon: <Activity size={20} /> },
    { name: "Settings", href: "#", icon: <Settings size={20} /> },
  ];

  return (
    <aside
      className={`fixed inset-y-0 left-0 z-40 w-64 transform border-r border-default-200 bg-background transition-transform duration-300 ease-in-out md:translate-x-0 md:static ${
        isOpen ? "translate-x-0" : "-translate-x-full"
      }`}
    >
      <div className="flex h-full flex-col px-4 py-6 gap-6">
        <div className="flex flex-col gap-2 flex-grow">
          <p className="px-2 text-xs font-semibold text-default-500 uppercase tracking-wider mb-2">
            Main Menu
          </p>
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.name}
                href={item.href}
                className={cn(
                  buttonVariants({ variant: isActive ? "secondary" : "tertiary" }),
                  "w-full justify-start flex items-center gap-2 px-4 py-2",
                  isActive ? "font-medium" : ""
                )}
              >
                {item.icon}
                {item.name}
              </Link>
            );
          })}
        </div>

        <div className="mt-auto flex flex-col gap-2">
          <Link
            href="#"
            className={cn(
              buttonVariants({ variant: "tertiary" }),
              "w-full justify-start flex items-center gap-2 px-4 py-2 text-default-500"
            )}
          >
            <HelpCircle size={20} />
            Help & Support
          </Link>

        </div>
      </div>
    </aside>
  );
}
