"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { UserButton } from "@clerk/nextjs";

import { AppSidebar } from "@/components/app-sidebar";

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const plansActive = pathname.startsWith("/subscriptions");

  return (
    <div className="flex h-svh min-h-0 bg-gray-50 dark:bg-gray-950">
      <AppSidebar />
      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center justify-end gap-3 border-b border-gray-200 bg-white px-4 dark:border-gray-800 dark:bg-[#1a222f]">
          <Link
            href="/subscriptions"
            className={`inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium transition-colors ${
              plansActive
                ? "border-blue-500 bg-blue-50 text-blue-800 dark:border-blue-400 dark:bg-blue-950/50 dark:text-blue-200"
                : "border-gray-300 text-gray-800 hover:border-blue-500 hover:bg-blue-50 hover:text-blue-700 dark:border-white/20 dark:text-white dark:hover:border-blue-400 dark:hover:bg-blue-950/40 dark:hover:text-blue-200"
            }`}
          >
            Plans
          </Link>
          <UserButton showName />
        </header>
        <main className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden p-6">{children}</main>
      </div>
    </div>
  );
}
