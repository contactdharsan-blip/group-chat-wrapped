import { motion } from 'motion/react';
import { ArrowLeft, CirclePlay, Trophy } from 'lucide-react';
import type { Profile, Wrapped } from '../types';
import { Avatar, Bubble, Stat, usePersonPop } from '../components/bits';
import { staggerContainer, staggerItem } from '../motion';
import { awardPop } from '../util';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

export function ProfilePage({ data, p, onBack, onPlay }: { data: Wrapped; p: Profile; onBack: () => void; onPlay: (who: string) => void }) {
  const bio = data.captions.bios[p.name] ?? '';
  const color = usePersonPop(p);
  return (
    <section data-testid="screen-profile" data-profile={p.name} className="mx-auto w-full max-w-xl px-4 pb-32 pt-4">
      <Button variant="outline" size="sm" onClick={onBack} className="min-h-10 bg-white duration-100" data-testid="profile-back">
        <ArrowLeft aria-hidden="true" /> Back
      </Button>

      <motion.div variants={staggerContainer} initial="hidden" animate="visible">
        <motion.header variants={staggerItem} className="mt-4">
          <Card className="gap-0 py-0">
          <div className="pop-fill h-24 border-b-2 border-black" style={color} />
          <div className="-mt-12 px-5 pb-5">
            <div className="flex flex-col items-start gap-3">
              <button type="button" onClick={() => onPlay(p.name)} aria-label={`Play ${p.name}'s story`} className="story-ring-btn" data-testid="profile-story">
                <Avatar m={p} size={88} ring />
              </button>
              <div className="w-full min-w-0">
                <h1 className="truncate text-3xl leading-tight">{p.name}</h1>
                <p className="mt-1 truncate text-sm text-muted-foreground">{p.handle}</p>
              </div>
            </div>
            <div className="mt-5 grid grid-cols-4 gap-2 rounded-lg border-2 border-black bg-accent py-3 shadow-sm" data-testid="profile-stats">
              <Stat n={p.messages} label="messages" />
              <Stat n={p.posts} label="posts" />
              <Stat n={p.awards.length} label="awards" />
              <Stat n={p.peak_hour ?? '–'} label="peak hour" />
            </div>
            {bio && <p className="mt-4 text-[15px] leading-relaxed" data-testid="profile-bio">{bio}</p>}
            <Button variant="secondary" className="mt-5 min-h-11 w-full duration-100" onClick={() => onPlay(p.name)}>
              <CirclePlay aria-hidden="true" /> Watch {p.name}'s story
            </Button>
          </div>
          </Card>
        </motion.header>

        {p.awards.length > 0 && (
          <motion.div variants={staggerItem} className="mt-4">
            <h2 className="mb-2 text-xs uppercase tracking-wider">Badges</h2>
            <div className="flex flex-wrap gap-2">
              {p.awards.map((a) => (
                <span key={a.key} className="pop-fill inline-flex items-center gap-1.5 rounded-full border-2 border-black px-3 py-1.5 text-sm font-bold shadow-sm" style={awardPop(a.key)}>
                  <Trophy size={14} strokeWidth={2.5} aria-hidden="true" /> {a.title}
                </span>
              ))}
            </div>
          </motion.div>
        )}

        <motion.div variants={staggerItem} className="mt-4 grid grid-cols-2 gap-3">
          <div className="brut p-4">
            <h2 className="text-xs uppercase tracking-wider">Top emoji</h2>
            {p.top_emoji.length ? (
              <ul className="mt-2 space-y-1">
                {p.top_emoji.map((e) => (
                  <li key={e.emoji} className="flex items-center justify-between"><span className="text-2xl">{e.emoji}</span><span className="font-mono text-sm font-bold">{e.count}</span></li>
                ))}
              </ul>
            ) : <p className="mt-2 text-sm text-muted-foreground">Words only. Respect.</p>}
          </div>
          <div className="brut p-4">
            <h2 className="text-xs uppercase tracking-wider">Top words</h2>
            <ul className="mt-2 space-y-1">
              {p.top_words.map((w) => (
                <li key={w.word} className="flex items-center justify-between gap-2"><span className="truncate font-medium">{w.word}</span><span className="font-mono text-sm font-bold">{w.count}</span></li>
              ))}
            </ul>
          </div>
        </motion.div>

        <motion.div variants={staggerItem} className="mt-6">
          <h2 className="mb-3 text-xs uppercase tracking-wider">Posts · the receipts</h2>
          {p.receipts.length === 0 && <p className="brut p-4 text-sm text-muted-foreground">No receipts this time.</p>}
          <div className="grid gap-3 sm:grid-cols-2">
            {p.receipts.map((r) => {
              const reactions = Object.entries(r.reactions);
              return (
                <article key={r.award_key + r.ts} className="brut p-4" data-testid="profile-post">
                  <p className="pop-fill mb-3 inline-block rounded border-2 border-black px-2 py-0.5 font-head text-[11px] uppercase tracking-wider" style={awardPop(r.award_key)}>{r.award_title}</p>
                  <Bubble r={{ author: p.name, ts: r.ts, text: r.text }} lines={5} size="text-sm" />
                  {reactions.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1.5" aria-label="Reactions from the chat">
                      {reactions.map(([emo, n]) => (
                        <span key={emo} className="rounded-full border-2 border-black bg-white px-2 py-0.5 text-xs font-bold">{emo} <span className="font-mono">{n}</span></span>
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
