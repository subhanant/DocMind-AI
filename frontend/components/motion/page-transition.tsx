"use client";

import * as React from "react";
import { usePathname } from "next/navigation";

/**
 * PAGE TRANSITION — a short, quiet route entrance.
 *
 * Keyed on the pathname so navigating remounts the subtree and replays the
 * entrance. There is no exit animation and no artificial loading gate: the
 * new route is interactive immediately, which is what keeps navigation from
 * feeling slow. Routing itself is untouched.
 *
 * Under `prefers-reduced-motion: reduce` the wrapper renders with no animation.
 */
export function PageTransition({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  const pathname = usePathname();
  return (
    <div key={pathname} className={className ? `motion-page-in ${className}` : "motion-page-in"}>
      {children}
    </div>
  );
}
