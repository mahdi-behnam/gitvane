import type { Metadata } from "next";
import { AppShell } from "@/components/app/app-shell";
import { StoreProvider } from "@/components/store/store-provider";
import { ThemeProvider } from "@/components/theme/theme-provider";
import { ToastProvider } from "@/components/ui/toast";
import "./globals.css";

export const metadata: Metadata = {
  title: "RepoLens",
  description: "Trace change before it spreads.",
  icons: {
    icon: [
      { url: "/repolens-light-logo.png", media: "(prefers-color-scheme: light)" },
      { url: "/repolens-dark-logo.png", media: "(prefers-color-scheme: dark)" },
    ],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <StoreProvider>
          <ThemeProvider>
            <ToastProvider>
              <AppShell>{children}</AppShell>
            </ToastProvider>
          </ThemeProvider>
        </StoreProvider>
      </body>
    </html>
  );
}
