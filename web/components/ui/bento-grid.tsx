// From Magic UI's Bento Grid (MIT, https://magicui.design/docs/components/bento-grid): the grid
// container only. Its BentoCard is not used (its grey body text fails contrast); cards here are plain panels.

import { type ComponentPropsWithoutRef, type ReactNode } from "react"

import { cn } from "@/lib/utils"

interface BentoGridProps extends ComponentPropsWithoutRef<"div"> {
  children: ReactNode
}

export function BentoGrid({ children, className, ...props }: BentoGridProps) {
  return (
    <div className={cn("grid w-full grid-cols-1 gap-4 md:grid-cols-3", className)} {...props}>
      {children}
    </div>
  )
}
