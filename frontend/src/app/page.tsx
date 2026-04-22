"use client";

import Link from "next/link";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { SignInButton, SignedIn, SignedOut, useAuth } from "@clerk/nextjs";

import { HomeAppDetails } from "@/components/home-app-details";

function SignedInRedirectToDashboard() {
  const router = useRouter();
  const { isLoaded, userId } = useAuth();

  useEffect(() => {
    if (isLoaded && userId) {
      router.replace("/dashboard");
    }
  }, [isLoaded, userId, router]);

  return (
    <div className="flex min-h-[50vh] items-center justify-center text-gray-500 dark:text-gray-400">
      Opening workspace…
    </div>
  );
}

export default function Home() {
  return (
    <>
      <SignedOut>
        <main className="min-h-screen bg-linear-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
          <div className="container mx-auto px-4 py-12">
            <nav className="mb-12 flex items-center justify-between">
              <h1 className="text-2xl font-bold text-gray-800 dark:text-gray-200">
                Litigation Prep Assistant
              </h1>
              <div className="flex items-center gap-4">
                <Link
                  href="/subscriptions"
                  className="inline-flex cursor-pointer items-center justify-center rounded-lg border border-gray-300 bg-white px-6 py-2 font-medium text-gray-800 shadow-sm transition-all duration-150 ease-out hover:border-blue-500 hover:bg-blue-50 hover:text-blue-800 active:scale-[0.97] dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 dark:hover:border-blue-400 dark:hover:bg-gray-700"
                >
                  Plans
                </Link>
                <SignInButton mode="modal">
                  <button
                    type="button"
                    className="cursor-pointer rounded-lg bg-blue-600 px-6 py-2 font-medium text-white shadow-sm transition-all duration-150 ease-out hover:bg-blue-700 hover:shadow-md active:scale-[0.97] active:bg-blue-800 active:shadow-inner"
                  >
                    Sign In
                  </button>
                </SignInButton>
              </div>
            </nav>

            <HomeAppDetails workspaceHref="/dashboard/new-scan" />
          </div>
        </main>
      </SignedOut>

      <SignedIn>
        <SignedInRedirectToDashboard />
      </SignedIn>
    </>
  );
}
