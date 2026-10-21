import type { Metadata } from "next";

import Items from "@/components/pages/Items";

export const metadata: Metadata = { title: "Items" };

export default function Page() {
  return <Items />;
}
