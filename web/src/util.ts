import type { CSSProperties } from 'react';
import type { Award } from './types';

export function when(iso: string): string {
  const d = new Date(iso);
  const day = d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' });
  const time = d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
  return `${day} · ${time}`;
}

export function shortDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

// The six flat pops in styles.css (--pop-0..5, each with its own black or white --pop-N-fg).
export const POPS = 6;

/** Inline style that sets --pop / --pop-fg to pop i; pair with .pop-fill, .avatar or .story-ring. */
export function pop(i: number): CSSProperties {
  const n = ((i % POPS) + POPS) % POPS;
  return { ['--pop' as string]: `var(--pop-${n})`, ['--pop-fg' as string]: `var(--pop-${n}-fg)` };
}

/** The same pop as --slide / --slide-fg, for the story phone. */
export function slidePop(i: number): CSSProperties {
  const n = ((i % POPS) + POPS) % POPS;
  return { ['--slide' as string]: `var(--pop-${n})`, ['--slide-fg' as string]: `var(--pop-${n}-fg)` };
}

/** Split value_text around its largest number, so the number can count up and the rest stays put. */
export function splitValue(text: string): { before: string; n: number | null; decimals: number; after: string } {
  const matches = [...text.matchAll(/\d[\d,]*(?:\.\d+)?/g)];
  if (!matches.length) return { before: text, n: null, decimals: 0, after: '' };
  const best = matches.reduce((a, b) => (parseFloat(b[0].replace(/,/g, '')) > parseFloat(a[0].replace(/,/g, '')) ? b : a));
  const raw = best[0];
  const i = best.index ?? 0;
  return {
    before: text.slice(0, i),
    n: parseFloat(raw.replace(/,/g, '')),
    decimals: raw.includes('.') ? raw.split('.')[1].length : 0,
    after: text.slice(i + raw.length),
  };
}

// One pop per award, in the order the awards run, so neighbours in the feed differ.
const AWARD_POP: Record<string, number> = {
  main_character: 0, novelist: 1, three_am: 2, omw: 3, left_on_read: 4, hype: 5,
  speed_demon: 0, ghost: 1, emoji: 2, group_word: 3, busiest_day: 4,
};
export function awardPop(key: string): CSSProperties {
  return pop(AWARD_POP[key] ?? 5);
}

export const KICKERS: Record<string, string> = {
  main_character: 'Said the most',
  novelist: 'Wrote the most per message',
  three_am: 'Awake when nobody else was',
  omw: 'Was always on the way',
  left_on_read: 'Asked into the void',
  hype: 'Never used an indoor voice',
  speed_demon: 'Replied before you finished typing',
  ghost: 'Said the least',
  emoji: 'Sent one emoji more than any other',
  group_word: 'Your group’s word',
  busiest_day: 'The day the chat lost it',
};

export function heroText(a: Award): string {
  if (a.key === 'emoji' && a.emoji) return a.emoji;
  if (a.key === 'group_word' && a.word) return `“${a.word}”`;
  if (a.key === 'busiest_day' && a.date) return shortDate(a.date + 'T12:00:00');
  return a.winner;
}
