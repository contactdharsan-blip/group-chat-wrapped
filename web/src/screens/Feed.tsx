import { motion } from 'motion/react';
import { Sparkles } from 'lucide-react';
import type { Award, Profile, Wrapped } from '../types';
import { Avatar, Bubble, CountValue } from '../components/bits';
import { staggerContainer, staggerItem } from '../motion';
import { KICKERS, awardPop, heroText, pop } from '../util';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';

export function StoriesRow({ data, onPlay }: { data: Wrapped; onPlay: (who: string | null) => void }) {
  const others = data.group.others;
  return (
    <div className="no-scrollbar -mx-4 flex gap-4 overflow-x-auto px-4 pb-3 pt-2" data-testid="stories-row" aria-label="Stories">
      <button type="button" className="story-ring-btn flex w-[82px] flex-none flex-col items-center gap-1.5" onClick={() => onPlay(null)} data-testid="story-ring-group">
        <span className="story-ring" style={pop(5)}>
          <span className="avatar h-16 w-16 text-lg" style={{ ['--pop' as string]: '#000', ['--pop-fg' as string]: '#fff' }}>
            {data.group.members.length + others}
          </span>
        </span>
        <span className="w-full truncate text-center text-xs font-bold">Group</span>
      </button>
      {data.profiles.map((p) => (
        <button key={p.name} type="button" className="story-ring-btn flex w-[82px] flex-none flex-col items-center gap-1.5" onClick={() => onPlay(p.name)} data-testid="story-ring">
          <Avatar m={p} size={64} ring />
          <span className="w-full truncate text-center text-xs font-bold">{p.name}</span>
        </button>
      ))}
    </div>
  );
}

function PostCard({ a, p, caption, featured, onProfile }: { a: Award; p: Profile | undefined; caption: string; featured: boolean; onProfile: (n: string) => void }) {
  return (
    <motion.article variants={staggerItem} data-testid="feed-post">
    <Card className={`gap-0 py-0 text-base ${featured ? 'shadow-lg' : ''}`}>
      <header className="flex items-center gap-3 px-4 pt-4">
        {p ? (
          <button type="button" onClick={() => onProfile(p.name)} className="flex min-w-0 items-center gap-3 text-left" data-testid="post-avatar" aria-label={`Open ${p.name}'s profile`}>
            <Avatar m={p} size={40} />
            <span className="min-w-0">
              <span className="block truncate font-bold leading-tight">{p.name}</span>
              <span className="block truncate text-xs text-muted-foreground">{p.handle}</span>
            </span>
          </button>
        ) : null}
        <Badge className="ml-auto uppercase tracking-wider">{featured ? 'Top award' : 'Award'}</Badge>
      </header>
      <div className="pop-fill relative mx-4 mt-3 overflow-hidden rounded-lg border-2 border-black px-4 py-5 shadow-sm" style={awardPop(a.key)}>
        <p className="text-xs font-bold uppercase tracking-wider">{KICKERS[a.key] ?? ''}</p>
        <h2 className="mt-1.5 text-[28px] leading-none">{a.title}</h2>
        {a.key === 'emoji' || a.key === 'group_word' || a.key === 'busiest_day' ? (
          <p className="mt-3 font-head text-4xl leading-none">{heroText(a)}</p>
        ) : null}
        <p className="mt-3 text-[15px] font-medium leading-snug"><CountValue text={a.value_text} /></p>
      </div>
      <div className="space-y-3 px-4 pt-4">
        {a.detail && <p className="text-sm text-muted-foreground">{a.detail}</p>}
        {a.context && <Bubble r={a.context} lines={3} />}
        <Bubble r={a.receipt} reply={!!a.context} lines={5} />
      </div>
      <footer className="mt-4 border-t-2 border-black bg-muted/50 px-4 py-3">
        <p className="text-sm leading-relaxed">
          <Sparkles size={13} className="mr-1 inline" aria-hidden="true" />
          {caption}
        </p>
      </footer>
    </Card>
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
          <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Wrapped</p>
          <h1 className="text-2xl leading-tight [overflow-wrap:anywhere]">{data.chat_name}</h1>
        </div>
        {data.demo && <Badge variant="outline" className="flex-none bg-white">invented demo chat</Badge>}
      </header>
      <StoriesRow data={data} onPlay={onPlay} />
      <p className="mt-3 font-mono text-xs text-muted-foreground">
        {g.messages.toLocaleString('en-US')} messages · {data.result.awards.length} awards · captions: {data.captions.source === 'claude' ? 'AI, from the computed facts' : 'templates'}
      </p>
      <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="mt-4 space-y-5">
        {data.result.awards.map((a, i) => (
          <PostCard key={a.key} a={a} p={byName.get(a.winner)} caption={data.captions.awards[a.key] ?? ''} featured={i === 0} onProfile={onProfile} />
        ))}
      </motion.div>
      {data.result.awards.length === 0 && (
        <p className="brut mt-4 p-5">Nobody opted in, so there are no awards. The group totals are on the Group tab.</p>
      )}
    </section>
  );
}
