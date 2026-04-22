"use client";

import { useState, type FormEvent } from "react";
import { useAuth } from "@clerk/nextjs";
import DatePicker from "react-datepicker";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkBreaks from "remark-breaks";
import { fetchEventSource } from "@microsoft/fetch-event-source";
import { Protect, PricingTable } from "@clerk/nextjs";

import "react-datepicker/dist/react-datepicker.css";

/** Clerk Billing plan id — must match plans in the Clerk Dashboard (format `user:…` or `org:…`). */
const PREMIUM_PLAN = "user:premium_subscription" as const;

function CaseAnalysisForm() {
  const { getToken } = useAuth();

  const [matterName, setMatterName] = useState("");
  const [referenceDate, setReferenceDate] = useState<Date | null>(new Date());
  const [caseFacts, setCaseFacts] = useState("");

  const [output, setOutput] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setOutput("");
    setLoading(true);

    const jwt = await getToken();
    if (!jwt) {
      setOutput("Authentication required");
      setLoading(false);
      return;
    }

    const controller = new AbortController();
    let buffer = "";

    await fetchEventSource("/api", {
      signal: controller.signal,
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${jwt}`,
      },
      body: JSON.stringify({
        matter_name: matterName,
        reference_date: referenceDate?.toISOString().slice(0, 10),
        case_facts: caseFacts,
      }),
      onmessage(ev) {
        buffer += ev.data;
        setOutput(buffer);
      },
      onclose() {
        setLoading(false);
      },
      onerror(err) {
        console.error("SSE error:", err);
        controller.abort();
        setLoading(false);
      },
    });
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <h1 className="mb-8 text-4xl font-bold text-gray-900 dark:text-gray-100">
        Case analysis
      </h1>

      <form
        onSubmit={handleSubmit}
        className="space-y-6 rounded-xl bg-white p-8 shadow-lg dark:bg-gray-800"
      >
        <div className="space-y-2">
          <label
            htmlFor="matter"
            className="block text-sm font-medium text-gray-700 dark:text-gray-300"
          >
            Matter / client name
          </label>
          <input
            id="matter"
            type="text"
            required
            value={matterName}
            onChange={(e) => setMatterName(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            placeholder="e.g. Acme Ltd v. …"
          />
        </div>

        <div className="space-y-2">
          <label
            htmlFor="date"
            className="block text-sm font-medium text-gray-700 dark:text-gray-300"
          >
            Reference date
          </label>
          <DatePicker
            id="date"
            selected={referenceDate}
            onChange={(d: Date | null) => setReferenceDate(d)}
            dateFormat="yyyy-MM-dd"
            placeholderText="Select date"
            required
            className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
          />
        </div>

        <div className="space-y-2">
          <label
            htmlFor="facts"
            className="block text-sm font-medium text-gray-700 dark:text-gray-300"
          >
            Case facts & notes
          </label>
          <textarea
            id="facts"
            required
            rows={8}
            value={caseFacts}
            onChange={(e) => setCaseFacts(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            placeholder="Paste facts, chronology, and any documents summary…"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full cursor-pointer rounded-lg bg-blue-600 px-6 py-3 font-semibold text-white shadow-sm transition-all duration-150 ease-out hover:bg-blue-700 hover:shadow-md active:scale-[0.99] active:bg-blue-800 active:shadow-inner disabled:cursor-not-allowed disabled:bg-blue-400"
        >
          {loading ? "Generating…" : "Generate structured output"}
        </button>
      </form>

      {output ? (
        <section className="mt-8 rounded-xl bg-gray-50 p-8 shadow-lg dark:bg-gray-800">
          <div className="markdown-content prose prose-blue max-w-none dark:prose-invert">
            <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>
              {output}
            </ReactMarkdown>
          </div>
        </section>
      ) : null}
    </div>
  );
}

function PremiumUpgradeHint() {
  return (
    <div className="rounded-xl border border-blue-200 bg-blue-50/80 p-6 text-center dark:border-blue-900 dark:bg-blue-950/40">
      <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
        Premium feature
      </h2>
      <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
        Case analysis below is included with Premium. Use{" "}
        <a
          href="#plans"
          className="font-medium text-blue-600 underline hover:text-blue-700 dark:text-blue-400"
        >
          Plans above
        </a>{" "}
        to upgrade, or switch back to Free anytime.
      </p>
    </div>
  );
}

export default function SubscriptionsPage() {
  return (
    <div className="mx-auto max-w-5xl space-y-16 pb-12">
      <section id="plans" className="scroll-mt-6">
        <header className="mb-8 text-center">
          <h1 className="mb-3 bg-linear-to-r from-blue-600 to-indigo-600 bg-clip-text text-4xl font-bold text-transparent sm:text-5xl">
            Plans & billing
          </h1>
          <p className="mx-auto max-w-2xl text-lg text-gray-600 dark:text-gray-400">
            Choose Free or Premium, or change your plan whenever you like.
            Updates apply through Clerk Billing.
          </p>
        </header>
        <div className="mx-auto max-w-4xl rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-gray-900">
          <PricingTable />
        </div>
      </section>

      <section className="border-t border-gray-200 pt-12 dark:border-gray-800">
        {/* <header className="mb-6 text-center">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            Premium case tools
          </h2>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
            Available on Premium. Free users can still manage plans in the
            section above.
          </p>
        </header> */}
        {/* <Protect plan={PREMIUM_PLAN} fallback={<PremiumUpgradeHint />}>
          <CaseAnalysisForm />
        </Protect> */}
      </section>
    </div>
  );
}
