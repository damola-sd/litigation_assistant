export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <section style={{ padding: "2rem" }}>{children}</section>;
}
