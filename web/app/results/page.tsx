import type { Metadata } from "next";

import Results from "@/components/pages/Results";

export const metadata: Metadata = { title: "Results" };

export default function Page() {
  return <Results />;
}
