import { motion } from 'motion/react';
import { Heart, Sparkles } from 'lucide-react';
import { useState } from 'react';
import type { Award, Profile, Wrapped } from '../types';
import { Avatar, Bubble, CountValue } from '../components/bits';
import { staggerContainer, staggerItem } from '../motion';
import { KICKERS, heroText, tint } from '../util';

export function StoriesRow({ data, onPlay }: { data: Wrapped; onPlay: (who: string | null) => void }) {
  const others = data.group.others;
  return (
    <div className="no-scrollbar -mx-4 flex gap-4 overflow-x-auto px-4 py-2" data-testid="stories-row" aria-label="Stories">
      <button type="button" className="story-ring-btn flex w-[72px] flex-none flex-col items-center gap-1.5" onClick={() => onPlay(null)} data-testid="story-ring-group">
        <span className="story-ring inline-flex">
          <span className="avatar h-16 w-16 text-sm" style={{ background: 'linear-gradient(135deg,#7c3aed,#e879f9 60%,#38bdf8)' }}>
            {data.group.members.length + others}
          </span>
        </span>
        <span className="w-full truncate text-center text-xs text-slate-300">Group</span>
      </button>
      {data.profiles.map((p) => (
        <button key={p.name} type="button" className="story-ring-btn flex w-[72px] flex-none flex-col items-center gap-1.5" onClick={() => onPlay(p.name)} data-testid="story-ring">
          <Avatar m={p} size={64} ring />
          <span className="w-full truncate text-center text-xs text-slate-300">{p.name}</span>
        </button>
      ))}
    </div>
  );
}

function PostCard({ a, p, caption, featured, onProfile }: { a: Award; p: Profile | undefined; caption: string; featured: boolean; onProfile: (n: string) => void }) {
  const [liked, setLiked] = useState(false);
  const [rgb] = tint(a.key);
  return (
    <motion.article variants={staggerItem} className={`glass overflow-hidden ${featured ? 'featured' : ''}`} data-testid="feed-post">
      <header className="flex items-center gap-3 px-4 pt-4">
        {p ? (
          <button type="button" onClick={() => onProfile(p.name)} className="flex min-w-0 items-center gap-3 text-left" data-testid="post-avatar" aria-label={`Open ${p.name}'s profile`}>
            <Avatar m={p} size={40} />
            <span className="min-w-0">
              <span className="block truncate font-semibold leading-tight">{p.name}</span>
              <span className="block truncate text-xs text-slate-400">{p.handle}</span>
            </span>
          </button>
        ) : null}
        <span className="ml-auto flex-none rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wider" style={{ background: `rgba(${rgb},0.16)`, color: `rgb(${rgb})`, border: `1px solid rgba(${rgb},0.35)` }}>
          Award
        </span>
      </header>
      <div className="relative mx-4 mt-3 overflow-hidden rounded-2xl px-4 py-5" style={{ background: `radial-gradient(120% 120% at 0% 0%, rgba(${rgb},0.30), transparent 60%), rgba(255,255,255,0.03)`, border: '1px solid rgba(255,255,255,0.08)' }}>
        <p className="text-xs font-medium uppercase tracking-wider text-slate-300">{KICKERS[a.key] ?? ''}</p>
        <h2 className="mt-1 font-display text-[28px] font-extrabold leading-none">{a.title}</h2>
        {a.key === 'emoji' || a.key === 'group_word' || a.key === 'busiest_day' ? (
          <p className="mt-3 font-display text-4xl font-bold leading-none">{heroText(a)}</p>
        ) : null}
        <p className="mt-3 text-[15px] leading-snug text-slate-200"><CountValue text={a.value_text} /></p>
      </div>
      <div className="space-y-3 px-4 pt-4">
        {a.detail && <p className="text-sm text-slate-400">{a.detail}</p>}
        {a.context && <Bubble r={a.context} lines={3} />}
        <Bubble r={a.receipt} reply={!!a.context} lines={5} />
      </div>
      <footer className="mt-3 flex items-start gap-3 border-t border-white/5 px-4 py-3">
        <button
          type="button"
          onClick={() => setLiked(!liked)}
          aria-pressed={liked}
          aria-label={liked ? 'Unlike' : 'Like'}
          className="flex min-h-[44px] flex-none items-center gap-1.5 rounded-full px-1 text-sm text-slate-300"
          data-testid="like"
        >
          <Heart size={22} className={`transition-transform duration-150 ${liked ? 'scale-110 fill-fuchsia-400 text-fuchsia-400' : ''}`} aria-hidden="true" />
          <span className="font-mono tabular">{liked ? 1 : 0}</span>
        </button>
        <p className="min-w-0 flex-1 pt-2.5 text-sm leading-relaxed text-slate-200">
          <Sparkles size={13} className="mr-1 inline text-violet-300" aria-hidden="true" />
          {caption}
        </p>
      </footer>
    </motion.article>
  );
}

export function Feed({ data, onProfile, onPlay }: { data: Wrapped; onProfile: (n: string) => void; onPlay: (who: string | null) => void }) {
  const byName = new Map(data.profiles.map((p) => [p.name, p]));
  const g = data.result.group;
  return (
    <section data-testid="screen-feed" className="mx-auto w-full max-w-xl px-4 pb-32 pt-4">
      <header className="mb-2 flex items-end justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Wrapped</p>
          <h1 className="truncate font-display text-2xl font-bold">{data.chat_name}</h1>
        </div>
        {data.demo && <span className="glass-subtle flex-none rounded-full px-2.5 py-1 text-[11px] text-slate-300">invented demo chat</span>}
      </header>
      <StoriesRow data={data} onPlay={onPlay} />
      <p className="mt-3 font-mono text-xs text-slate-400">
        {g.messages.toLocaleString('en-US')} messages · {data.result.awards.length} awards · captions: {data.captions.source === 'claude' ? 'AI, from the computed facts' : 'templates'}
      </p>
      <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="mt-4 space-y-5">
        {data.result.awards.map((a, i) => (
          <PostCard key={a.key} a={a} p={byName.get(a.winner)} caption={data.captions.awards[a.key] ?? ''} featured={i === 0} onProfile={onProfile} />
        ))}
      </motion.div>
      {data.result.awards.length === 0 && (
        <p className="glass mt-4 p-5 text-slate-300">Nobody opted in, so there are no awards. The group totals are on the Group tab.</p>
      )}
    </section>
  );
}
