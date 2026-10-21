"use client"

// Adapted from Magic UI's Number Ticker (MIT, https://magicui.design/docs/components/number-ticker).
// Changes for this project: the text shown at rest is always `format(value)`, the exact bound value;
// screen readers get that final text only (the counting digits are aria-hidden); with
// prefers-reduced-motion the final value is shown at once with no animation.

import { useEffect, useRef, type ComponentPropsWithoutRef } from "react"
import { useInView, useMotionValue, useReducedMotion, useSpring } from "motion/react"

import { cn } from "@/lib/utils"

interface NumberTickerProps extends Omit<ComponentPropsWithoutRef<"span">, "children"> {
  value: number
  /** Formats the counting value and, exactly, the final one. */
  format: (n: number) => string
  startValue?: number
  delay?: number
}

export function NumberTicker({ value, format, startValue = 0, delay = 0, className, ...props }: NumberTickerProps) {
  const ref = useRef<HTMLSpanElement>(null)
  const reduced = useReducedMotion()
  const motionValue = useMotionValue(startValue)
  const springValue = useSpring(motionValue, { damping: 60, stiffness: 100 })
  const isInView = useInView(ref, { once: true, margin: "0px" })
  const final = format(value)

  const startedFor = useRef<number | null>(null)

  // Count once per value. A re-render must not reset the text, and the exact final text is always
  // written at the end, even if the spring never reports completion.
  useEffect(() => {
    const el = ref.current
    if (reduced || !isInView || !el || startedFor.current === value) return
    startedFor.current = value
    el.textContent = format(startValue)
    motionValue.jump(startValue)
    const start = setTimeout(() => motionValue.set(value), delay * 1000)
    const settle = setTimeout(() => {
      el.textContent = final
    }, (delay + 4) * 1000)
    return () => {
      clearTimeout(start)
      clearTimeout(settle)
      el.textContent = final
      startedFor.current = null
    }
  }, [motionValue, isInView, delay, value, startValue, reduced, format, final])

  useEffect(() => {
    if (reduced) return
    const stopChange = springValue.on("change", (latest) => {
      if (ref.current) ref.current.textContent = format(latest)
    })
    const stopDone = springValue.on("animationComplete", () => {
      if (ref.current) ref.current.textContent = final
    })
    return () => {
      stopChange()
      stopDone()
    }
  }, [springValue, format, final, reduced])

  return (
    <span className={cn("inline-block tabular-nums", className)} {...props}>
      <span ref={ref} aria-hidden="true">
        {final}
      </span>
      <span className="sr-only">{final}</span>
    </span>
  )
}
