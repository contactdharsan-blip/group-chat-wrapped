import { motion } from 'motion/react';
import { useState } from 'react';
import type { MembersResponse } from '../types';
import { staggerContainer, staggerItem } from '../motion';

/** Who gets named. Unticked people count toward totals as "someone" and never get an award, a quote or a profile. */
export function OptIn(props: {
  members: MembersResponse;
  busy: boolean;
  error: string | null;
  onBack: () => void;
  onGo: (optin: string[], name: string) => void;
}) {
  const [on, setOn] = useState<Set<string>>(() => new Set());
  const [name, setName] = useState('');
  const toggle = (n: string) => {
    const next = new Set(on);
    if (next.has(n)) next.delete(n); else next.add(n);
    setOn(next);
  };
  const total = props.members.messages;

  return (
    <main data-testid="screen-optin" className="relative z-10 mx-auto w-full max-w-xl px-4 pb-16 pt-10">
      <button type="button" className="text-sm text-slate-400 hover:text-white" onClick={props.onBack}>← Back</button>
      <h1 className="mt-4 font-display text-3xl font-bold sm:text-4xl">Who agreed to be named?</h1>
      <p className="mt-2 text-slate-300">
        Tick the people who said yes. Everyone else still counts in the group totals, as “someone”, and never gets an award, a quote or a profile.
      </p>
      <p className="mt-2 font-mono text-xs text-slate-400">
        {total.toLocaleString('en-US')} messages · {props.members.members.length} people · read as {props.members.format}
      </p>

      <label className="mt-6 block text-xs font-semibold uppercase tracking-wider text-slate-400" htmlFor="chat-name">Chat name</label>
      <input
        id="chat-name"
        className="glass mt-2 w-full rounded-2xl px-4 py-3 text-base text-white placeholder:text-slate-500 focus:border-violet-300/60 focus:outline-none"
        placeholder="Floor 4 Survivors"
        value={name}
        maxLength={80}
        onChange={(e) => setName(e.target.value)}
      />

      <motion.ul variants={staggerContainer} initial="hidden" animate="visible" className="mt-6 space-y-2.5">
        {props.members.members.map((m) => {
          const checked = on.has(m.name);
          return (
            <motion.li key={m.name} variants={staggerItem}>
              <label className={`glass flex min-h-[60px] cursor-pointer items-center gap-3 px-4 py-3 transition ${checked ? 'border-violet-300/50' : ''}`}>
                <span className="min-w-0 flex-1">
                  <span className="block truncate font-medium">{checked ? m.name : <span className="text-slate-300">{m.name}</span>}</span>
                  <span className="font-mono text-xs text-slate-400">{m.messages.toLocaleString('en-US')} messages · {checked ? 'named' : 'shows as “someone”'}</span>
                </span>
                <input type="checkbox" className="peer sr-only" checked={checked} onChange={() => toggle(m.name)} data-testid="optin-toggle" data-name={m.name} />
                <span className="relative h-7 w-12 flex-none rounded-full bg-white/10 transition peer-checked:bg-violet-500 peer-focus-visible:outline-2 peer-focus-visible:outline-violet-300" aria-hidden="true">
                  <span className={`absolute top-1 h-5 w-5 rounded-full bg-white shadow transition-all ${checked ? 'left-6' : 'left-1'}`} style={{ transitionTimingFunction: 'cubic-bezier(0.34,1.56,0.64,1)' }} />
                </span>
              </label>
            </motion.li>
          );
        })}
      </motion.ul>

      {props.error && <p role="alert" className="mt-4 rounded-xl border border-rose-400/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">{props.error}</p>}
      <div className="sticky bottom-4 mt-6">
        <button type="button" className="btn-primary w-full text-base" disabled={props.busy || on.size === 0} onClick={() => props.onGo([...on], name.trim())} data-testid="make-wrapped">
          {props.busy ? 'Wrapping…' : on.size === 0 ? 'Tick at least one person' : `Make our Wrapped (${on.size} named)`}
        </button>
      </div>
    </main>
  );
}
