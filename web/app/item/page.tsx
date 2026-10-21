import type { Metadata } from "next";

import ItemDetail from "@/components/pages/ItemDetail";

export const metadata: Metadata = { title: "Question" };

export default function Page() {
  return <ItemDetail />;
}
