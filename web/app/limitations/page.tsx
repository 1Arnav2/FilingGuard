import type { Metadata } from "next";

import Limitations from "@/components/pages/Limitations";

export const metadata: Metadata = { title: "Limitations" };

export default function Page() {
  return <Limitations />;
}
