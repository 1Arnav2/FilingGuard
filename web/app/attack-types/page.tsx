import type { Metadata } from "next";

import { AttackTypesRedirect } from "@/components/site/AttackTypesRedirect";

export const metadata: Metadata = { title: "By attack type" };

export default function Page() {
  return <AttackTypesRedirect />;
}
