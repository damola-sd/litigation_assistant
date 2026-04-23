"use client";

import Link from "next/link";

import { HomeAppDetails } from "@/components/home-app-details";

export default function DashboardHomePage() {
  return (
    <div className="mx-auto max-w-5xl">
      <div className="rounded-2xl border border-gray-200 bg-white p-8 shadow-sm dark:border-gray-800 dark:bg-gray-900">
        <div className="mb-8 flex flex-col items-center justify-between gap-4 sm:flex-row sm:items-start">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              Home
            </h1>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
              Overview and quick actions
            </p>
          </div>
        </div>

        <HomeAppDetails workspaceHref="/dashboard/new-scan" />
      </div>
    </div>
  );
}
