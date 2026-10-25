import { animate, useInView } from 'motion/react';
import { createContext, useContext, useEffect, useRef, useState } from 'react';
import type { Member, Receipt } from '../types';
import { pop, splitValue, when } from '../util';
import { useMotionSafe } from '../motion';

/**
 * Each named person's pop, by their place in the Wrapped's profiles, so up to six people
 * get six different colours. Someone outside the map (nobody, in practice) falls back to
 * their hue.
 */
export const PeopleColors = createContext<Map<string, number>>(new Map());

export function usePersonPop(m: Pick<Member, 'name' | 'hue'>) {
  const i = useContext(PeopleColors).get(m.name);
  return pop(i ?? m.hue);
}

export function Avatar({ m, size = 40, ring = false }: { m: Member; size?: number; ring?: boolean }) {
  const style = usePersonPop(m);
  const face = (
    <span className="avatar" style={{ ...style, width: size, height: size, fontSize: size * 0.36 }} aria-hidden="true">
      {m.initials}
    </span>
  );
  return ring ? <span className="story-ring" style={style}>{face}</span> : face;
}

/** A receipt as a black-keyline chat bubble, with who and when. Long ones clamp and expand on tap. */
export function Bubble({ r, reply = false, lines = 6, size = 'text-[15px]', expandable = true, onFill = false }: { r: Receipt; reply?: boolean; lines?: number; size?: string; expandable?: boolean; onFill?: boolean }) {
  const [open, setOpen] = useState(false);
  const long = expandable && r.text.length > lines * 38;
  // On a coloured slide the caption lines take the slide's foreground; elsewhere, ink and muted.
  const meta = onFill ? 'opacity-90' : 'text-muted-foreground';
  return (
    <figure className={`flex flex-col ${reply ? 'items-end' : 'items-start'} gap-1`}>
      <figcaption className={`px-1 text-xs font-bold ${onFill ? '' : 'text-foreground'}`}>{r.author}</figcaption>
      <blockquote className={`bubble ${reply ? 'reply' : ''} max-w-full px-4 py-2.5 leading-snug ${size}`}>
        {/* The clamp sits on an inner box: WebKit paints clamped lines into the padding otherwise. */}
        <span className={`block ${open ? '' : 'clamp'}`} style={{ ['--lines' as string]: lines }}>
          {r.text || <span className="italic text-muted-foreground">(a photo or sticker)</span>}
        </span>
      </blockquote>
      <div className="flex items-center gap-2 px-1">
        <time className={`font-mono text-[11px] ${meta}`} dateTime={r.ts}>{when(r.ts)}</time>
        {long && (
          <button type="button" className="text-[11px] font-bold underline underline-offset-2" onClick={(e) => { e.stopPropagation(); setOpen(!open); }}>
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
    // A background tab never paints the animation's frames, so show the real number there.
    if (!safe || document.hidden) { setShown(n); return; }
    const c = animate(0, n, { duration: 0.8, ease: [0.16, 1, 0.3, 1], onUpdate: setShown });
    return () => c.stop();
  }, [n, inView, safe]);
  if (n === null) return <span className={className}>{text}</span>;
  const fmt = shown.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
  return (
    <span className={className} aria-label={text}>
      {before}
      <span ref={ref} className="font-bold tabular">{fmt}</span>
      {after}
    </span>
  );
}

export function Stat({ n, label }: { n: string | number; label: string }) {
  return (
    <div className="flex min-w-0 flex-col items-center">
      <span className="font-head text-lg tabular">{typeof n === 'number' ? n.toLocaleString('en-US') : n}</span>
      <span className="text-[11px] font-medium text-muted-foreground">{label}</span>
    </div>
  );
}
