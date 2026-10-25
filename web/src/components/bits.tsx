import { animate, useInView } from 'motion/react';
import { useEffect, useRef, useState } from 'react';
import type { Member, Receipt } from '../types';
import { avatarGradient, splitValue, when } from '../util';
import { useMotionSafe } from '../motion';

export function Avatar({ m, size = 40, ring = false }: { m: Member; size?: number; ring?: boolean }) {
  const face = (
    <span
      className="avatar"
      style={{ width: size, height: size, fontSize: size * 0.4, background: avatarGradient(m.hue) }}
      aria-hidden="true"
    >
      {m.initials}
    </span>
  );
  return ring ? <span className="story-ring inline-flex">{face}</span> : face;
}

/** A receipt as a glass chat bubble, with who and when. Long ones clamp and expand on tap. */
export function Bubble({ r, reply = false, lines = 6, size = 'text-[15px]', expandable = true }: { r: Receipt; reply?: boolean; lines?: number; size?: string; expandable?: boolean }) {
  const [open, setOpen] = useState(false);
  const long = expandable && r.text.length > lines * 38;
  return (
    <figure className={`flex flex-col ${reply ? 'items-end' : 'items-start'} gap-1`}>
      <figcaption className="px-1 text-xs font-semibold text-slate-300/80">{r.author}</figcaption>
      <blockquote className={`bubble ${reply ? 'reply' : ''} max-w-full px-4 py-2.5 leading-snug ${size} text-slate-50`}>
        {/* The clamp sits on an inner box: WebKit paints clamped lines into the padding otherwise. */}
        <span className={`block ${open ? '' : 'clamp'}`} style={{ ['--lines' as string]: lines }}>
          {r.text || <span className="italic text-slate-400">(a photo or sticker)</span>}
        </span>
      </blockquote>
      <div className="flex items-center gap-2 px-1">
        <time className="font-mono text-[11px] text-slate-400" dateTime={r.ts}>{when(r.ts)}</time>
        {long && (
          <button type="button" className="text-[11px] font-semibold text-violet-300" onClick={(e) => { e.stopPropagation(); setOpen(!open); }}>
            {open ? 'less' : 'read all'}
          </button>
        )}
      </div>
    </figure>
  );
}

/** value_text with its largest number counting up once it scrolls into view. */
export function CountValue({ text, className = '' }: { text: string; className?: string }) {
  const { before, n, decimals, after } = splitValue(text);
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true });
  const safe = useMotionSafe();
  const [shown, setShown] = useState(safe && n !== null ? 0 : n ?? 0);
  useEffect(() => {
    if (n === null || !inView) return;
    if (!safe) { setShown(n); return; }
    const c = animate(0, n, { duration: 1.1, ease: [0.16, 1, 0.3, 1], onUpdate: setShown });
    return () => c.stop();
  }, [n, inView, safe]);
  if (n === null) return <span className={className}>{text}</span>;
  const fmt = shown.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
  return (
    <span className={className} aria-label={text}>
      {before}
      <span ref={ref} className="font-mono font-semibold tabular text-white">{fmt}</span>
      {after}
    </span>
  );
}

export function Stat({ n, label }: { n: string | number; label: string }) {
  return (
    <div className="flex min-w-0 flex-col items-center">
      <span className="font-mono text-lg font-semibold tabular text-white">{typeof n === 'number' ? n.toLocaleString('en-US') : n}</span>
      <span className="text-[11px] text-slate-400">{label}</span>
    </div>
  );
}
