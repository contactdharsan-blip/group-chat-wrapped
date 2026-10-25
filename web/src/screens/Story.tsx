import { AnimatePresence, motion } from 'motion/react';
import { Pause, Play, RotateCcw, X } from 'lucide-react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { Award, Profile, Wrapped } from '../types';
import { Avatar, Bubble, CountValue } from '../components/bits';
import { useMotionSafe } from '../motion';
import { KICKERS, heroText, shortDate, tint } from '../util';

const SLIDE_MS = 5000;

type Slide =
  | { kind: 'cover' }
  | { kind: 'totals' }
  | { kind: 'person'; p: Profile }
  | { kind: 'award'; a: Award; i: number; n: number }
  | { kind: 'closing' };

export function buildDeck(data: Wrapped, who: string | null): Slide[] {
  const awards = data.result.awards;
  if (who) {
    const p = data.profiles.find((x) => x.name === who);
    if (!p) return [{ kind: 'cover' }];
    const mine = awards.filter((a) => a.winner === who);
    return [{ kind: 'person', p }, ...mine.map((a, i) => ({ kind: 'award' as const, a, i: i + 1, n: mine.length }))];
  }
  const deck: Slide[] = [{ kind: 'cover' }];
  if (data.result.group.messages) deck.push({ kind: 'totals' });
  awards.forEach((a, i) => deck.push({ kind: 'award', a, i: i + 1, n: awards.length }));
  deck.push({ kind: 'closing' });
  return deck;
}

function slideTint(s: Slide): [string, string] {
  if (s.kind === 'award') return tint(s.a.key);
  if (s.kind === 'totals') return ['56, 189, 248', '167, 139, 250'];
  if (s.kind === 'closing') return ['232, 121, 249', '56, 189, 248'];
  return ['124, 58, 237', '232, 121, 249'];
}

function receiptSize(text: string): { size: string; lines: number } {
  const n = text.length;
  if (n <= 90) return { size: 'text-[17px]', lines: 5 };
  if (n <= 200) return { size: 'text-[15px]', lines: 6 };
  return { size: 'text-[13px]', lines: 7 };
}

function SlideBody({ s, data }: { s: Slide; data: Wrapped }) {
  const g = data.result.group;
  if (s.kind === 'cover') {
    const range = g.first && g.last ? `${shortDate(g.first)} – ${shortDate(g.last)}` : '';
    return (
      <div className="flex h-full flex-col justify-end gap-4 pb-6">
        <p className="text-sm font-semibold text-slate-300">{data.chat_name}</p>
        <h2 className="font-display text-[44px] font-extrabold leading-[0.95]">Your group chat, <span className="bg-gradient-to-r from-violet-300 to-fuchsia-300 bg-clip-text text-transparent">wrapped.</span></h2>
        <p className="text-lg font-medium text-slate-200">{range}<br /><CountValue text={`${g.messages.toLocaleString('en-US')} messages`} /></p>
        <p className="text-sm text-slate-400">Only friends who opted in are named. Every award quotes a real message.</p>
      </div>
    );
  }
  if (s.kind === 'totals') {
    const cells: [string, string][] = [
      [`${g.messages}`, 'messages'], [`${g.words ?? 0}`, 'words'], [`${g.days ?? 0}`, 'days'], [g.busiest_hour ?? '–', 'busiest hour'],
    ];
    return (
      <div className="flex h-full flex-col gap-5 pt-6">
        <p className="text-sm font-semibold text-slate-300">The semester in numbers</p>
        <h2 className="font-display text-4xl font-extrabold leading-none">You did <span className="text-sky-300">not</span> stop talking.</h2>
        <div className="mt-2 grid grid-cols-2 gap-3">
          {cells.map(([v, l]) => (
            <div key={l} className="glass p-3">
              <p className="font-display text-3xl font-extrabold leading-none"><CountValue text={v} /></p>
              <p className="mt-1 text-xs text-slate-300">{l}</p>
            </div>
          ))}
        </div>
        <p className="mt-auto pb-4 text-sm text-slate-300">Busiest on {g.busiest_weekday}s.</p>
      </div>
    );
  }
  if (s.kind === 'person') {
    const p = s.p;
    return (
      <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
        <Avatar m={p} size={112} ring />
        <div>
          <h2 className="font-display text-4xl font-extrabold leading-none">{p.name}</h2>
          <p className="mt-1 text-sm text-slate-300">{p.handle}</p>
        </div>
        <p className="max-w-[18rem] text-[15px] leading-relaxed text-slate-200">{data.captions.bios[p.name]}</p>
        <p className="font-mono text-xs text-slate-400">
          {p.awards.length ? `${p.awards.length} award${p.awards.length > 1 ? 's' : ''} this semester` : 'No awards this time. Next semester.'}
        </p>
      </div>
    );
  }
  if (s.kind === 'closing') {
    const names = data.result.members;
    const who = names.length > 1 ? `${names.slice(0, -1).join(', ')} and ${names[names.length - 1]}` : names[0] ?? 'everyone';
    return (
      <div className="flex h-full flex-col justify-end gap-4 pb-6">
        <p className="text-sm font-semibold text-slate-300">That’s a wrap</p>
        <h2 className="font-display text-[44px] font-extrabold leading-[0.95]">Same chat, <span className="text-fuchsia-300">next semester.</span></h2>
        <p className="text-lg text-slate-200">Starring {who}.</p>
      </div>
    );
  }
  const a = s.a;
  const big = heroText(a);
  const rs = receiptSize(a.receipt.text);
  return (
    <div className="flex h-full flex-col">
      <p className="font-mono text-xs text-slate-300">Award {s.i} of {s.n}</p>
      <h2 className="mt-2 font-display text-[34px] font-extrabold leading-none">{a.title}</h2>
      <p className="mt-1 text-sm font-medium text-slate-300">{KICKERS[a.key]}</p>
      <p className={`mt-4 font-display font-extrabold leading-none ${big.length > 9 ? 'text-5xl' : 'text-6xl'} break-words`}>{big}</p>
      <p className="mt-3 text-base leading-snug text-slate-100"><CountValue text={a.value_text} /></p>
      <div className="mt-auto space-y-2 pb-2">
        {a.detail && <p className="text-[13px] text-slate-300">{a.detail}</p>}
        {a.context && <Bubble r={a.context} lines={2} size="text-[13px]" expandable={false} />}
        <Bubble r={a.receipt} reply={!!a.context} lines={rs.lines} size={rs.size} expandable={false} />
        <p className="pt-1 text-[13px] italic leading-snug text-violet-100/90">{data.captions.awards[a.key]}</p>
      </div>
    </div>
  );
}

export function Story({ data, who, onClose }: { data: Wrapped; who: string | null; onClose: () => void }) {
  const deck = useMemo(() => buildDeck(data, who), [data, who]);
  const [idx, setIdx] = useState(0);
  const [progress, setProgress] = useState(0);
  const [paused, setPaused] = useState(false);
  const safe = useMotionSafe();
  const holdTimer = useRef<number | null>(null);
  const held = useRef(false);
  const ended = idx === deck.length - 1 && progress >= 1;
  const progressRef = useRef(0);
  progressRef.current = progress;

  useEffect(() => { setIdx(0); setProgress(0); }, [deck]);

  const go = useCallback((d: number) => {
    setIdx((i) => Math.max(0, Math.min(deck.length - 1, i + d)));
    setProgress(0);
  }, [deck.length]);

  useEffect(() => {
    if (paused || ended) return;
    let raf = 0;
    let last = performance.now();
    let p = progressRef.current;
    const tick = (now: number) => {
      p += (now - last) / SLIDE_MS;
      last = now;
      if (p >= 1) {
        if (idx < deck.length - 1) { setIdx(idx + 1); setProgress(0); } else setProgress(1);
        return;
      }
      setProgress(p);
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [paused, ended, idx, deck.length]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight') { e.preventDefault(); go(1); }
      else if (e.key === 'ArrowLeft') { e.preventDefault(); go(-1); }
      else if (e.key === ' ') { e.preventDefault(); setPaused((p) => !p); }
      else if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [go, onClose]);

  const down = () => {
    held.current = false;
    holdTimer.current = window.setTimeout(() => { held.current = true; setPaused(true); }, 220);
  };
  const up = (dir: number) => {
    if (holdTimer.current) clearTimeout(holdTimer.current);
    if (held.current) { held.current = false; setPaused(false); return; }
    go(dir);
  };

  const s = deck[idx];
  const [c1, c2] = slideTint(s);
  const side = s.kind === 'award' ? s.a : null;
  const title = who ? `${who}'s story` : `${data.chat_name}`;

  return (
    <section data-testid="screen-story" className="mx-auto flex w-full max-w-5xl flex-col items-center gap-6 px-4 pb-32 pt-4 md:flex-row md:items-start md:justify-center md:pt-8">
      <div
        className="phone flex-none"
        style={{ ['--slide-rgb' as string]: c1, ['--slide-rgb-2' as string]: c2 }}
        data-testid="phone"
        data-slide={idx}
        data-slides={deck.length}
      >
        <div className="phone-glow" aria-hidden="true" />
        <div className="absolute inset-x-3 top-3 z-20 flex gap-1" aria-hidden="true">
          {deck.map((_, i) => (
            <span key={i} className="progress-seg">
              <i style={{ transform: `scaleX(${i < idx ? 1 : i === idx ? progress : 0})` }} />
            </span>
          ))}
        </div>
        <div className="absolute inset-x-3 top-6 z-30 flex items-center justify-between">
          <span className="truncate text-xs font-semibold text-white/90">{title}</span>
          <span className="flex gap-1">
            <button type="button" className="rounded-full p-2 text-white/90 hover:bg-white/10" onClick={() => (ended ? (setIdx(0), setProgress(0)) : setPaused(!paused))} aria-label={ended ? 'Replay' : paused ? 'Play' : 'Pause'} data-testid="story-pause">
              {ended ? <RotateCcw size={18} /> : paused ? <Play size={18} /> : <Pause size={18} />}
            </button>
            <button type="button" className="rounded-full p-2 text-white/90 hover:bg-white/10" onClick={onClose} aria-label="Close story" data-testid="story-close">
              <X size={18} />
            </button>
          </span>
        </div>

        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={idx}
            className="absolute inset-0 z-10 px-6 pb-6 pt-16"
            initial={safe ? { opacity: 0, scale: 0.97, filter: 'blur(8px)' } : false}
            animate={{ opacity: 1, scale: 1, filter: 'blur(0px)' }}
            exit={safe ? { opacity: 0, scale: 0.98, filter: 'blur(6px)', transition: { duration: 0.15 } } : { opacity: 0, transition: { duration: 0 } }}
            transition={safe ? { type: 'spring', damping: 26, stiffness: 300 } : { duration: 0 }}
            data-testid="story-slide"
          >
            <SlideBody s={s} data={data} />
          </motion.div>
        </AnimatePresence>

        {/* Tap zones: left third back, the rest forward. Hold anywhere to pause. */}
        <button type="button" aria-label="Previous slide" data-testid="story-prev" className="absolute bottom-0 left-0 top-16 z-20 w-1/3 cursor-w-resize"
          onPointerDown={down} onPointerUp={() => up(-1)} onPointerLeave={() => { if (holdTimer.current) clearTimeout(holdTimer.current); if (held.current) { held.current = false; setPaused(false); } }} onContextMenu={(e) => e.preventDefault()} />
        <button type="button" aria-label="Next slide" data-testid="story-next" className="absolute bottom-0 right-0 top-16 z-20 w-2/3 cursor-e-resize"
          onPointerDown={down} onPointerUp={() => up(1)} onPointerLeave={() => { if (holdTimer.current) clearTimeout(holdTimer.current); if (held.current) { held.current = false; setPaused(false); } }} onContextMenu={(e) => e.preventDefault()} />
      </div>

      <aside className="hidden w-full max-w-sm flex-col gap-4 md:flex" aria-label="Receipts">
        <div className="glass p-5">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Slide {idx + 1} of {deck.length}</p>
          {side ? (
            <>
              <h3 className="mt-2 font-display text-2xl font-bold">{side.title}</h3>
              <p className="mt-1 text-sm text-slate-300">{side.value_text}</p>
              <p className="mt-3 text-sm leading-relaxed text-slate-200">{data.captions.awards[side.key]}</p>
            </>
          ) : (
            <p className="mt-2 text-sm text-slate-300">Tap the right side or press → to go on, ← to go back. Hold to pause, space to pause too.</p>
          )}
        </div>
        {side && (
          <div className="glass space-y-3 p-5">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">The receipt, in full</p>
            {side.context && <Bubble r={side.context} lines={20} size="text-sm" />}
            <Bubble r={side.receipt} reply={!!side.context} lines={30} size="text-sm" />
          </div>
        )}
      </aside>
    </section>
  );
}
