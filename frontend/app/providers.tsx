"use client";

import { ThemeProvider as NextThemesProvider } from "next-themes";
import { useRouter } from "next/navigation";
import { HeroUIProvider } from "@heroui/system";

import { AlertProvider } from "@/components/providers/AlertProvider";

export function Providers({ children }: { children: React.ReactNode }) {
  const router = useRouter();

  return (
    <HeroUIProvider navigate={router.push}>
      <NextThemesProvider attribute="class" defaultTheme="dark">
        <AlertProvider>
          {children}
        </AlertProvider>
      </NextThemesProvider>
    </HeroUIProvider>
  );
}

