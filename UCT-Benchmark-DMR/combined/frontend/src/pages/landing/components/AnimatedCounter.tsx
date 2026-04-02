import { useEffect, useState } from 'react';

interface AnimatedCounterProps {
  target: number;
  isInView: boolean;
  duration?: number;
  suffix?: string;
}

export function AnimatedCounter({ target, isInView, duration = 1200, suffix = '' }: AnimatedCounterProps) {
  const [count, setCount] = useState(0);

  useEffect(() => {
    if (!isInView) return;

    let start = 0;
    const startTime = performance.now();

    function step(now: number) {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // Ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = Math.round(eased * target);

      if (current !== start) {
        setCount(current);
        start = current;
      }

      if (progress < 1) {
        requestAnimationFrame(step);
      }
    }

    requestAnimationFrame(step);
  }, [isInView, target, duration]);

  return (
    <span className="font-display font-bold text-3xl sm:text-4xl text-gradient-cosmic tabular-nums">
      {count}{suffix}
    </span>
  );
}
