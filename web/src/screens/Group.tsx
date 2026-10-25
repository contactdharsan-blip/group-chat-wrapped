import { motion } from 'motion/react';
import type { Wrapped } from '../types';
import { Avatar, Bubble, CountValue, Stat } from '../components/bits';
import { staggerContainer, staggerItem } from '../motion';
import { heroText, shortDate, tint } from '../util';

export function Group({ data, onProfile }: { data: Wrapped; onProfile: (n: string) => void }) {
  const g = data.result.group;
  const { busiest_day: day, group_word: word, members, others } = data.group;
  const range = g.first && g.last ? `${shortDate(g.first)} – ${shortDate(g.last)}, ${new Date(g.last).getFullYear()}` : '';
  const share = Object.entries(g.share ?? {});
  const top = Math.max(1, ...share.map(([, n]) => n));
  return (
    <section data-testid="screen-group" className="mx-auto w-full max-w-5xl px-4 pb-32 pt-4">
      <motion.div variants={staggerContainer} initial="hidden" animate="visible">
        <motion.header variants={staggerItem} className="glass p-5">
          <div className="flex items-center gap-4">
            <span className="avatar h-20 w-20 flex-none text-2xl" style={{ background: 'linear-gradient(135deg,#7c3aed,#e879f9 60%,#38bdf8)' }} aria-hidden="true">
              {data.group.name.slice(0, 1).toUpperCase()}
            </span>
            <div className="min-w-0">
              <h1 className="font-display text-3xl font-extrabold leading-tight">{data.group.name}</h1>
              <p className="font-mono text-xs text-slate-400">{range}</p>
            </div>
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-2" data-testid="group-members">
            {members.map((m) => (
              <button key={m.name} type="button" onClick={() => onProfile(m.name)} className="glass-subtle flex items-center gap-2 rounded-full py-1 pl-1 pr-3 text-sm" data-testid="group-member">
                <Avatar m={m} size={28} /> {m.name}
              </button>
            ))}
            {others > 0 && (
              <span className="glass-subtle rounded-full px-3 py-1.5 text-sm text-slate-300" data-testid="someone-chip">+{others} someone</span>
            )}
          </div>
          <div className="mt-5 grid grid-cols-3 gap-2 rounded-2xl border border-white/10 bg-white/[0.03] py-3 sm:grid-cols-6">
            <Stat n={g.messages} label="messages" />
            <Stat n={g.words ?? 0} label="words" />
            <Stat n={g.media ?? 0} label="photos & files" />
            <Stat n={g.days ?? 0} label="days" />
            <Stat n={g.busiest_hour ?? '–'} label="busiest hour" />
            <Stat n={(g.busiest_weekday ?? '–').slice(0, 3)} label="busiest day" />
          </div>
        </motion.header>

        <motion.h2 variants={staggerItem} className="mb-3 mt-8 font-display text-2xl font-bold">Recap</motion.h2>
        <div className="grid auto-rows-auto grid-cols-2 gap-3 lg:grid-cols-4" data-testid="recap">
          {word && (
            <motion.article variants={staggerItem} className="glass featured col-span-2 p-5" data-testid="recap-featured">
              <p className="text-xs font-semibold uppercase tracking-wider text-violet-200">Group word</p>
              <p className="mt-2 font-display text-5xl font-extrabold leading-none">{heroText(word)}</p>
              <p className="mt-3 text-sm text-slate-300"><CountValue text={word.value_text} /></p>
              <p className="mt-1 text-xs text-slate-400">{word.detail}</p>
            </motion.article>
          )}
          {day && (
            <motion.article variants={staggerItem} className="glass col-span-2 p-5">
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Busiest day</p>
              <p className="mt-2 font-display text-3xl font-extrabold leading-none">{heroText(day)}</p>
              <p className="mt-2 text-sm text-slate-300"><CountValue text={day.value_text} /></p>
              <div className="mt-3"><Bubble r={day.receipt} lines={2} size="text-sm" /></div>
            </motion.article>
          )}
          <motion.article variants={staggerItem} className="glass col-span-2 p-5">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Who talked</p>
            <ul className="mt-3 space-y-2">
              {share.map(([who, n]) => (
                <li key={who} className="grid grid-cols-[5.5rem_1fr_3.5rem] items-center gap-2 text-sm">
                  <span className="truncate">{who}</span>
                  <span className="h-2 overflow-hidden rounded-full bg-white/10"><i className="block h-full rounded-full" style={{ width: `${(100 * n) / top}%`, background: 'linear-gradient(90deg,#a78bfa,#e879f9)' }} /></span>
                  <span className="text-right font-mono text-xs text-slate-300">{n.toLocaleString('en-US')}</span>
                </li>
              ))}
            </ul>
          </motion.article>
          {data.result.awards.filter((a) => a.key !== 'group_word' && a.key !== 'busiest_day').map((a) => {
            const [rgb] = tint(a.key);
            return (
              <motion.article key={a.key} variants={staggerItem} className="glass glass-hover p-4" style={{ background: `radial-gradient(120% 100% at 0% 0%, rgba(${rgb},0.18), transparent 65%), var(--glass-bg)` }}>
                <p className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: `rgb(${rgb})` }}>{a.title}</p>
                <p className="mt-2 truncate font-display text-2xl font-extrabold leading-none">{heroText(a)}</p>
                <p className="mt-2 text-xs leading-snug text-slate-300"><CountValue text={a.value_text} /></p>
              </motion.article>
            );
          })}
        </div>
      </motion.div>
    </section>
  );
}
