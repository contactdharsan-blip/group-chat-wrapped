// Brutalist motion: short ease-out tweens and hard slide-ins, no springs, no blur.
import { type Variants } from 'motion/react';
import { useEffect, useState } from 'react';

/** true only when motion is safe: not reduced-motion. */
export function useMotionSafe(): boolean {
  const reduced = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const [safe, setSafe] = useState(() => !reduced());
  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    const handler = () => setSafe(!reduced());
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);
  return safe;
}

const snap = { duration: 0.18, ease: 'easeOut' } as const;

export const fadeIn: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { duration: 0.15 } },
  exit: { opacity: 0, transition: { duration: 0.1 } },
};
export const slideUp: Variants = {
  hidden: { opacity: 0, y: 14 },
  visible: { opacity: 1, y: 0, transition: snap },
  exit: { opacity: 0, transition: { duration: 0.1 } },
};
export const staggerContainer: Variants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.04, delayChildren: 0.02 } },
};
export const staggerItem: Variants = {
  hidden: { opacity: 0, x: -14 },
  visible: { opacity: 1, x: 0, transition: snap },
};
