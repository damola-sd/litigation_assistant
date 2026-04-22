"use client";

import { SignedIn, SignedOut } from "@clerk/nextjs";

import { AppShell } from "@/components/app-shell";

export function AuthenticatedLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <SignedOut>{children}</SignedOut>
      <SignedIn>
        <AppShell>{children}</AppShell>
      </SignedIn>
    </>
  );
}
