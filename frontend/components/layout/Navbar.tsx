"use client";

import { Button } from "@heroui/react";
import { ShieldAlert, Bell, Menu } from "lucide-react";
import { ThemeToggle } from "./ThemeToggle";

interface NavbarProps {
  onMenuClick: () => void;
}

export function Navbar({ onMenuClick }: NavbarProps) {
  return (
    <header className="sticky top-0 z-50 w-full border-b border-divider bg-background/70 backdrop-blur-lg">
      <div className="flex h-16 items-center px-4 md:px-6 w-full justify-between">
        <div className="flex items-center gap-2 md:gap-4 justify-start">
          <Button
            isIconOnly
            variant="tertiary"
            className="md:hidden"
            onClick={onMenuClick}
          >
            <Menu size={20} />
          </Button>
          <div className="flex items-center gap-2 shrink-0">
            <ShieldAlert className="text-primary hidden sm:block" size={24} />
            <p className="font-bold text-lg tracking-tight">GUARDIA AI</p>
          </div>
        </div>

        <div className="flex items-center gap-2 justify-end">
          <Button isIconOnly variant="tertiary" aria-label="Notifications">
            <Bell size={20} />
          </Button>
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
