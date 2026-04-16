import { useSyncExternalStore } from 'react';

/**
 * Tailwind breakpoint widths (must stay in sync with tailwind.config.js `screens`).
 * `xs` is a custom breakpoint added for iPhone SE (375px). The rest are Tailwind defaults.
 */
const BREAKPOINTS = {
  xs: 375,
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
  '2xl': 1536,
} as const;

export type Breakpoint = keyof typeof BREAKPOINTS;

/**
 * Subscribe to a `matchMedia` query. SSR-safe via useSyncExternalStore — returns
 * `false` during server render, then hydrates to the live value on mount.
 *
 * @example
 * const prefersReducedMotion = useMediaQuery('(prefers-reduced-motion: reduce)');
 * const isTouchDevice = useMediaQuery('(hover: none) and (pointer: coarse)');
 */
export function useMediaQuery(query: string): boolean {
  return useSyncExternalStore(
    (onChange) => {
      if (typeof window === 'undefined') return () => {};
      const mql = window.matchMedia(query);
      mql.addEventListener('change', onChange);
      return () => mql.removeEventListener('change', onChange);
    },
    () => {
      if (typeof window === 'undefined') return false;
      return window.matchMedia(query).matches;
    },
    () => false,
  );
}

/**
 * Returns `true` when the viewport is at or above the given Tailwind breakpoint.
 * The mapping mirrors tailwind.config.js exactly.
 *
 * @example
 * const isDesktop = useBreakpoint('lg'); // true when >= 1024px
 * const isMobile = !useBreakpoint('md');  // true when < 768px
 */
export function useBreakpoint(bp: Breakpoint): boolean {
  return useMediaQuery(`(min-width: ${BREAKPOINTS[bp]}px)`);
}
