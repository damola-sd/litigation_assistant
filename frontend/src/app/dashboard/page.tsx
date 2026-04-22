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
              Litigation Prep Assistant
            </h1>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
              Home · overview and quick actions
            </p>
          </div>
          <Link
            href="/dashboard/new-scan"
            className="inline-flex shrink-0 cursor-pointer items-center justify-center rounded-lg bg-blue-600 px-6 py-3 font-semibold text-white shadow-sm transition-all duration-150 ease-out hover:bg-blue-700 hover:shadow-md active:scale-[0.98] active:bg-blue-800"
          >
            New scan
          </Link>
        </div>

        <HomeAppDetails workspaceHref="/dashboard/new-scan" />
      </div>
    </div>
  );
}
