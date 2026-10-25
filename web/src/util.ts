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

export function avatarGradient(hue: number): string {
  return `linear-gradient(135deg, hsl(${hue} 72% 62%), hsl(${(hue + 45) % 360} 68% 44%))`;
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

// One glow tint per award, all inside the violet / fuchsia / sky family.
const TINTS: Record<string, [string, string]> = {
  main_character: ['167, 139, 250', '232, 121, 249'],
  novelist: ['129, 140, 248', '56, 189, 248'],
  three_am: ['99, 102, 241', '30, 64, 175'],
  omw: ['232, 121, 249', '244, 114, 182'],
  left_on_read: ['148, 163, 184', '129, 140, 248'],
  hype: ['217, 70, 239', '250, 204, 21'],
  speed_demon: ['56, 189, 248', '45, 212, 191'],
  ghost: ['203, 213, 225', '167, 139, 250'],
  emoji: ['244, 114, 182', '167, 139, 250'],
  group_word: ['192, 132, 252', '56, 189, 248'],
  busiest_day: ['236, 72, 153', '124, 58, 237'],
};
export function tint(key: string): [string, string] {
  return TINTS[key] ?? ['167, 139, 250', '56, 189, 248'];
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
