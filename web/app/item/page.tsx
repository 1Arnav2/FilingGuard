import type { Metadata } from "next";

import ItemRedirect from "@/components/pages/ItemRedirect";

export const metadata: Metadata = { title: "Question" };

export default function Page() {
  return <ItemRedirect />;
}
