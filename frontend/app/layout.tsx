import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "Litigation Prep Assistant",
  description: "AI-powered litigation preparation (Kenya)",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
