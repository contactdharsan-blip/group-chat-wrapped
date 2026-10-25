import { motion } from 'motion/react';
import { ArrowLeft, CirclePlay, Trophy } from 'lucide-react';
import type { Profile, Wrapped } from '../types';
import { Avatar, Bubble, Stat } from '../components/bits';
import { staggerContainer, staggerItem } from '../motion';
import { tint } from '../util';

export function ProfilePage({ data, p, onBack, onPlay }: { data: Wrapped; p: Profile; onBack: () => void; onPlay: (who: string) => void }) {
  const bio = data.captions.bios[p.name] ?? '';
  return (
    <section data-testid="screen-profile" data-profile={p.name} className="mx-auto w-full max-w-xl px-4 pb-32 pt-4">
      <button type="button" onClick={onBack} className="btn-glass min-h-[40px] px-3 py-1.5 text-sm" data-testid="profile-back">
        <ArrowLeft size={16} aria-hidden="true" /> Back
      </button>

      <motion.div variants={staggerContainer} initial="hidden" animate="visible">
        <motion.header variants={staggerItem} className="glass mt-4 overflow-hidden">
          <div className="h-24" style={{ background: `linear-gradient(120deg, hsl(${p.hue} 70% 45% / .55), hsl(${(p.hue + 60) % 360} 70% 50% / .25) 60%, transparent)` }} />
          <div className="-mt-12 px-5 pb-5">
            <div className="flex items-end gap-4">
              <button type="button" onClick={() => onPlay(p.name)} aria-label={`Play ${p.name}'s story`} className="story-ring-btn" data-testid="profile-story">
                <Avatar m={p} size={88} ring />
              </button>
              <div className="min-w-0 pb-1">
                <h1 className="truncate font-display text-3xl font-extrabold leading-none">{p.name}</h1>
                <p className="mt-1 truncate text-sm text-slate-400">{p.handle}</p>
              </div>
            </div>
            <div className="mt-5 grid grid-cols-4 gap-2 rounded-2xl border border-white/10 bg-white/[0.03] py-3" data-testid="profile-stats">
              <Stat n={p.messages} label="messages" />
              <Stat n={p.posts} label="posts" />
              <Stat n={p.awards.length} label="awards" />
              <Stat n={p.peak_hour ?? '–'} label="peak hour" />
            </div>
            {bio && <p className="mt-4 text-[15px] leading-relaxed text-slate-200" data-testid="profile-bio">{bio}</p>}
            <button type="button" className="btn-glass mt-4 w-full text-sm" onClick={() => onPlay(p.name)}>
              <CirclePlay size={16} aria-hidden="true" /> Watch {p.name}'s story
            </button>
          </div>
        </motion.header>

        {p.awards.length > 0 && (
          <motion.div variants={staggerItem} className="mt-4">
            <h2 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">Badges</h2>
            <div className="flex flex-wrap gap-2">
              {p.awards.map((a) => {
                const [rgb] = tint(a.key);
                return (
                  <span key={a.key} className="inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-medium" style={{ background: `rgba(${rgb},0.14)`, border: `1px solid rgba(${rgb},0.35)`, color: '#f8fafc' }}>
                    <Trophy size={14} style={{ color: `rgb(${rgb})` }} aria-hidden="true" /> {a.title}
                  </span>
                );
              })}
            </div>
          </motion.div>
        )}

        <motion.div variants={staggerItem} className="mt-4 grid grid-cols-2 gap-3">
          <div className="glass p-4">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400">Top emoji</h2>
            {p.top_emoji.length ? (
              <ul className="mt-2 space-y-1">
                {p.top_emoji.map((e) => (
                  <li key={e.emoji} className="flex items-center justify-between"><span className="text-2xl">{e.emoji}</span><span className="font-mono text-sm text-slate-300">{e.count}</span></li>
                ))}
              </ul>
            ) : <p className="mt-2 text-sm text-slate-400">Words only. Respect.</p>}
          </div>
          <div className="glass p-4">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400">Top words</h2>
            <ul className="mt-2 space-y-1">
              {p.top_words.map((w) => (
                <li key={w.word} className="flex items-center justify-between gap-2"><span className="truncate">{w.word}</span><span className="font-mono text-sm text-slate-300">{w.count}</span></li>
              ))}
            </ul>
          </div>
        </motion.div>

        <motion.div variants={staggerItem} className="mt-6">
          <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400">Posts · the receipts</h2>
          {p.receipts.length === 0 && <p className="glass p-4 text-sm text-slate-400">No receipts this time.</p>}
          <div className="grid gap-3 sm:grid-cols-2">
            {p.receipts.map((r) => {
              const [rgb] = tint(r.award_key);
              const reactions = Object.entries(r.reactions);
              return (
                <article key={r.award_key + r.ts} className="glass p-4" data-testid="profile-post">
                  <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider" style={{ color: `rgb(${rgb})` }}>{r.award_title}</p>
                  <Bubble r={{ author: p.name, ts: r.ts, text: r.text }} lines={5} size="text-sm" />
                  {reactions.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1.5" aria-label="Reactions from the chat">
                      {reactions.map(([emo, n]) => (
                        <span key={emo} className="glass-subtle rounded-full px-2 py-0.5 text-xs">{emo} <span className="font-mono">{n}</span></span>
                      ))}
                    </div>
                  )}
                </article>
              );
            })}
          </div>
        </motion.div>
      </motion.div>
    </section>
  );
}
