import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PageGist - Summarize any web page",
  description: "Paste a link to any article or web page and get a short summary with the key points.",
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f6f7f9" },
    { media: "(prefers-color-scheme: dark)", color: "#0f1012" },
  ],
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      {/* Browser extensions often add attributes to <body> before React loads. */}
      <body suppressHydrationWarning>{children}</body>
    </html>
  );
}
