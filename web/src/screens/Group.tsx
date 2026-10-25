import { motion } from 'motion/react';
import { useContext } from 'react';
import type { Wrapped } from '../types';
import { Avatar, Bubble, CountValue, PeopleColors, Stat } from '../components/bits';
import { staggerContainer, staggerItem } from '../motion';
import { awardPop, heroText, pop, shortDate } from '../util';

export function Group({ data, onProfile }: { data: Wrapped; onProfile: (n: string) => void }) {
  const g = data.result.group;
  const { busiest_day: day, group_word: word, members, others } = data.group;
  const range = g.first && g.last ? `${shortDate(g.first)} – ${shortDate(g.last)}, ${new Date(g.last).getFullYear()}` : '';
  const share = Object.entries(g.share ?? {});
  const top = Math.max(1, ...share.map(([, n]) => n));
  const colors = useContext(PeopleColors);
  return (
    <section data-testid="screen-group" className="mx-auto w-full max-w-5xl px-4 pb-32 pt-4">
      <motion.div variants={staggerContainer} initial="hidden" animate="visible">
        <motion.header variants={staggerItem} className="brut p-5">
          <div className="flex items-center gap-4">
            <span className="avatar h-20 w-20 flex-none text-3xl shadow-md" style={pop(5)} aria-hidden="true">
              {data.group.name.slice(0, 1).toUpperCase()}
            </span>
            <div className="min-w-0">
              <h1 className="text-3xl leading-tight">{data.group.name}</h1>
              <p className="font-mono text-xs text-muted-foreground">{range}</p>
            </div>
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-2" data-testid="group-members">
            {members.map((m) => (
              <button key={m.name} type="button" onClick={() => onProfile(m.name)} className="press flex items-center gap-2 rounded-full border-2 border-black bg-white py-1 pl-1 pr-3 text-sm font-bold shadow-sm" data-testid="group-member">
                <Avatar m={m} size={28} /> {m.name}
              </button>
            ))}
            {others > 0 && (
              <span className="rounded-full border-2 border-dashed border-black bg-muted px-3 py-1.5 text-sm font-medium" data-testid="someone-chip">+{others} someone</span>
            )}
          </div>
          <div className="mt-5 grid grid-cols-3 gap-y-3 rounded-lg border-2 border-black bg-accent py-3 shadow-sm sm:grid-cols-6">
            <Stat n={g.messages} label="messages" />
            <Stat n={g.words ?? 0} label="words" />
            <Stat n={g.media ?? 0} label="photos & files" />
            <Stat n={g.days ?? 0} label="days" />
            <Stat n={g.busiest_hour ?? '–'} label="busiest hour" />
            <Stat n={(g.busiest_weekday ?? '–').slice(0, 3)} label="busiest day" />
          </div>
        </motion.header>

        <motion.h2 variants={staggerItem} className="mb-3 mt-8 text-2xl">Recap</motion.h2>
        <div className="grid auto-rows-auto grid-cols-2 gap-3 lg:grid-cols-4" data-testid="recap">
          {word && (
            <motion.article variants={staggerItem} className="brut pop-fill col-span-2 p-5 shadow-lg" style={awardPop(word.key)} data-testid="recap-featured">
              <p className="font-head text-xs uppercase tracking-wider">Group word</p>
              <p className="mt-2 font-head text-5xl leading-none">{heroText(word)}</p>
              <p className="mt-3 text-sm font-medium"><CountValue text={word.value_text} /></p>
              <p className="mt-1 text-xs">{word.detail}</p>
            </motion.article>
          )}
          {day && (
            <motion.article variants={staggerItem} className="brut pop-fill col-span-2 p-5" style={awardPop(day.key)}>
              <p className="font-head text-xs uppercase tracking-wider">Busiest day</p>
              <p className="mt-2 font-head text-3xl leading-none">{heroText(day)}</p>
              <p className="mt-2 text-sm font-medium"><CountValue text={day.value_text} /></p>
              <div className="mt-3"><Bubble r={day.receipt} lines={2} size="text-sm" onFill /></div>
            </motion.article>
          )}
          <motion.article variants={staggerItem} className="brut col-span-2 p-5">
            <p className="font-head text-xs uppercase tracking-wider">Who talked</p>
            <ul className="mt-3 space-y-2">
              {share.map(([who, n]) => (
                <li key={who} className="grid grid-cols-[5.5rem_1fr_3.5rem] items-center gap-2 text-sm">
                  <span className="truncate font-medium">{who}</span>
                  <span className="h-4 overflow-hidden rounded-full border-2 border-black bg-muted"><i className="pop-fill block h-full border-r-2 border-black" style={{ width: `${(100 * n) / top}%`, ...(colors.has(who) ? pop(colors.get(who)!) : { ['--pop' as string]: '#000' }) }} /></span>
                  <span className="text-right font-mono text-xs font-bold">{n.toLocaleString('en-US')}</span>
                </li>
              ))}
            </ul>
          </motion.article>
          {data.result.awards.filter((a) => a.key !== 'group_word' && a.key !== 'busiest_day').map((a) => {
            return (
              <motion.article key={a.key} variants={staggerItem} className="brut pop-fill p-4" style={awardPop(a.key)}>
                <p className="font-head text-[11px] uppercase tracking-wider">{a.title}</p>
                <p className="mt-2 truncate font-head text-2xl leading-none">{heroText(a)}</p>
                <p className="mt-2 text-xs font-medium leading-snug"><CountValue text={a.value_text} /></p>
              </motion.article>
            );
          })}
        </div>
      </motion.div>
    </section>
  );
}
