import { GeistMono } from "geist/font/mono";
import { GeistSans } from "geist/font/sans";
import type { Metadata } from "next";
import { ThemeProvider } from "next-themes";
import { Suspense } from "react";

import { SiteFooter } from "@/components/site/SiteFooter";
import { SiteHeader } from "@/components/site/SiteHeader";
import { copy } from "@/lib/content";

import "./globals.css";

// Link previews: one static image (public/og.png, 1200 x 630); every URL absolute on the live site.
const shareImage = { url: "/og.png", width: 1200, height: 630, alt: copy.site.share_image_alt };

export const metadata: Metadata = {
  metadataBase: new URL(copy.site.url),
  title: { default: "FilingGuard", template: "%s · FilingGuard" },
  description: copy.site.subtitle,
  openGraph: {
    type: "website",
    url: "/",
    siteName: copy.site.name,
    title: copy.site.name,
    description: copy.site.share,
    images: [shareImage],
  },
  twitter: { card: "summary_large_image", title: copy.site.name, description: copy.site.share, images: [shareImage] },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${GeistSans.variable} ${GeistMono.variable}`} suppressHydrationWarning>
      <body className="min-h-screen">
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
          <a
            href="#main"
            className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:rounded-md focus:bg-background focus:px-4 focus:py-2 focus:shadow"
          >
            {copy.site.skip}
          </a>
          <Suspense>
            <SiteHeader />
            <main id="main" tabIndex={-1} className="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-12">
              {children}
            </main>
          </Suspense>
          <SiteFooter />
        </ThemeProvider>
      </body>
    </html>
  );
}
