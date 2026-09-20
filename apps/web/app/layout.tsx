import React from "react";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Project Relay Console",
  description: "Operator console and governed execution action center.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="bg-slate-950 font-sans antialiased text-slate-100">{children}</body>
    </html>
  );
}
