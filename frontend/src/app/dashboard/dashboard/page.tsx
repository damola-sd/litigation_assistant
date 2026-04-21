import Link from "next/link";

export default function DashboardPage() {
  return (
    <main>
      <h1>Dashboard</h1>
      <p>Main input / case list placeholder.</p>
      <ul>
        <li>
          <Link href="/dashboard/new">New analysis</Link>
        </li>
        <li>
          <Link href="/dashboard/history">History</Link>
        </li>
      </ul>
    </main>
  );
}
