import { useEffect, useRef, useState } from 'react';

interface UseInViewOptions {
  threshold?: number;
  rootMargin?: string;
  /** Fallback timeout (ms) — force visible if observer hasn't fired */
  fallbackDelay?: number;
}

export function useInView({ threshold = 0.15, rootMargin = '0px', fallbackDelay = 1200 }: UseInViewOptions = {}) {
  const ref = useRef<HTMLDivElement>(null);
  const [isInView, setIsInView] = useState(false);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;

    // Fallback: if IntersectionObserver never fires (e.g. element is already
    // past the viewport, browser throttles the callback, or SSR hydration
    // mismatch), force visibility after a short delay so content is never
    // permanently hidden.
    const fallbackTimer = setTimeout(() => setIsInView(true), fallbackDelay);

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsInView(true);
          clearTimeout(fallbackTimer);
          observer.unobserve(node);
        }
      },
      { threshold, rootMargin }
    );

    observer.observe(node);
    return () => {
      clearTimeout(fallbackTimer);
      observer.disconnect();
    };
  }, [threshold, rootMargin, fallbackDelay]);

  return { ref, isInView };
}
