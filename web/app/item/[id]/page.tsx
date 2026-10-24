import type { Metadata } from "next";

import ItemDetail from "@/components/pages/ItemDetail";
import { allItems, itemById } from "@/lib/items.server";

type Params = { params: Promise<{ id: string }> };

// One static page per test item; any other ID is not a page.
export const dynamicParams = false;

export function generateStaticParams(): { id: string }[] {
  return allItems().map((item) => ({ id: item.id }));
}

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  return { title: `${(await params).id} · Items` };
}

export default async function Page({ params }: Params) {
  const item = itemById((await params).id);
  if (!item) throw new Error("generateStaticParams lists only exported items");
  return <ItemDetail item={item} />;
}
