"use client";

import Link from "next/link";
import { SignInButton, SignedIn, SignedOut } from "@clerk/nextjs";

type HomeAppDetailsProps = {
  /** Primary workspace entry (e.g. `/dashboard/new-scan`). */
  workspaceHref?: string;
};

export function HomeAppDetails({
  workspaceHref = "/dashboard/new-scan",
}: HomeAppDetailsProps) {
  return (
    <div className="text-center py-16">
      <h2 className="mb-6 bg-linear-to-r from-blue-600 to-indigo-600 bg-clip-text text-6xl font-bold text-transparent">
        Transform Your
        <br />
        Case Preparation
      </h2>
      <p className="mx-auto mb-12 max-w-2xl text-xl text-gray-600 dark:text-gray-400">
        AI-powered assistant that turns case facts into timelines, legal
        reasoning, and structured briefs for Kenyan litigation workflows
      </p>

      <div className="mx-auto mb-12 grid max-w-4xl gap-8 md:grid-cols-3">
        <div className="group relative">
          <div className="absolute inset-0 rounded-xl bg-linear-to-r from-blue-600 to-cyan-600 opacity-25 blur transition duration-300 group-hover:opacity-40" />
          <div className="relative rounded-xl border border-gray-200 bg-white p-6 shadow-lg backdrop-blur-sm dark:border-gray-700 dark:bg-gray-800">
            <div className="mb-4 text-3xl">📋</div>
            <h3 className="mb-2 text-lg font-semibold text-gray-900 dark:text-gray-100">
              Fact extraction
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Pull entities, events, and timelines from messy notes and uploads
            </p>
          </div>
        </div>
        <div className="group relative">
          <div className="absolute inset-0 rounded-xl bg-linear-to-r from-emerald-600 to-green-600 opacity-25 blur transition duration-300 group-hover:opacity-40" />
          <div className="relative rounded-xl border border-gray-200 bg-white p-6 shadow-lg backdrop-blur-sm dark:border-gray-700 dark:bg-gray-800">
            <div className="mb-4 text-3xl">⚖️</div>
            <h3 className="mb-2 text-lg font-semibold text-gray-900 dark:text-gray-100">
              Strategy & law
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Map facts to issues, arguments, and applicable legal context
            </p>
          </div>
        </div>
        <div className="group relative">
          <div className="absolute inset-0 rounded-xl bg-linear-to-r from-purple-600 to-pink-600 opacity-25 blur transition duration-300 group-hover:opacity-40" />
          <div className="relative rounded-xl border border-gray-200 bg-white p-6 shadow-lg backdrop-blur-sm dark:border-gray-700 dark:bg-gray-800">
            <div className="mb-4 text-3xl">📄</div>
            <h3 className="mb-2 text-lg font-semibold text-gray-900 dark:text-gray-100">
              Structured briefs
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Draft issues, arguments, counterarguments, and conclusions with QA
              notes
            </p>
          </div>
        </div>
      </div>

      <SignedOut>
        <SignInButton mode="modal">
          <button
            type="button"
            className="cursor-pointer rounded-xl bg-linear-to-r from-blue-600 to-indigo-600 px-8 py-4 text-lg font-bold text-white shadow-md transition-all duration-150 ease-out hover:scale-105 hover:from-blue-700 hover:to-indigo-700 hover:shadow-lg active:scale-95 active:from-blue-800 active:to-indigo-800 active:shadow-inner"
          >
            Start Free Trial
          </button>
        </SignInButton>
      </SignedOut>
      <SignedIn>
        <Link
          href={workspaceHref}
          className="inline-block cursor-pointer rounded-xl bg-linear-to-r from-blue-600 to-indigo-600 px-8 py-4 text-lg font-bold text-white shadow-md transition-all duration-150 ease-out hover:scale-105 hover:from-blue-700 hover:to-indigo-700 hover:shadow-lg active:scale-95 active:from-blue-800 active:to-indigo-800 active:shadow-inner"
        >
          New scan
        </Link>
      </SignedIn>

      <div className="mt-12 text-center text-sm text-gray-500 dark:text-gray-400">
        <p>
          Secure • Structured outputs . Integrated with Kenyan law database.
        </p>
      </div>
    </div>
  );
}
