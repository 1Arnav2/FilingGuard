import type { Metadata } from "next";

import Overview from "@/components/pages/Overview";

export const metadata: Metadata = { title: { absolute: "Overview · FilingGuard" } };

export default function Page() {
  return <Overview />;
}
