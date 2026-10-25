import { motion } from 'motion/react';
import { useState } from 'react';
import type { MembersResponse } from '../types';
import { staggerContainer, staggerItem } from '../motion';
import { Button } from '@/components/ui/button';

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
      <Button variant="outline" size="sm" className="bg-white duration-100" onClick={props.onBack}>← Back</Button>
      <h1 className="mt-5 text-3xl sm:text-4xl">Who agreed to be named?</h1>
      <p className="mt-2 font-medium">
        Tick the people who said yes. Everyone else still counts in the group totals, as “someone”, and never gets an award, a quote or a profile.
      </p>
      <p className="mt-2 font-mono text-xs text-muted-foreground">
        {total.toLocaleString('en-US')} messages · {props.members.members.length} people · read as {props.members.format}
      </p>

      <label className="mt-6 block font-head text-xs uppercase tracking-wider" htmlFor="chat-name">Chat name</label>
      <input
        id="chat-name"
        className="mt-2 w-full rounded-lg border-2 border-black bg-white px-4 py-3 text-base shadow-md placeholder:text-muted-foreground focus:shadow-sm focus:outline-none"
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
              <label className={`press flex min-h-[60px] cursor-pointer items-center gap-3 rounded-lg border-2 border-black px-4 py-3 shadow-md ${checked ? 'bg-lime' : 'bg-white'}`}>
                <span className="min-w-0 flex-1">
                  <span className="block truncate font-bold">{m.name}</span>
                  <span className={`font-mono text-xs ${checked ? '' : 'text-muted-foreground'}`}>{m.messages.toLocaleString('en-US')} messages · {checked ? 'named' : 'shows as “someone”'}</span>
                </span>
                <input type="checkbox" className="peer sr-only" checked={checked} onChange={() => toggle(m.name)} data-testid="optin-toggle" data-name={m.name} />
                <span className="relative h-8 w-14 flex-none rounded-full border-2 border-black bg-muted transition-colors duration-100 peer-checked:bg-black peer-focus-visible:outline-3 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-blue" aria-hidden="true">
                  <span className={`absolute top-[2px] h-6 w-6 rounded-full border-2 border-black bg-white transition-[left] duration-100 ease-out ${checked ? 'left-[26px] bg-yellow' : 'left-[2px]'}`} />
                </span>
              </label>
            </motion.li>
          );
        })}
      </motion.ul>

      {props.error && <p role="alert" className="mt-4 rounded-lg border-2 border-black bg-destructive px-4 py-3 text-sm font-medium text-white shadow-sm">{props.error}</p>}
      <div className="sticky bottom-4 mt-6">
        <Button size="lg" className="min-h-12 w-full text-base duration-100" disabled={props.busy || on.size === 0} onClick={() => props.onGo([...on], name.trim())} data-testid="make-wrapped">
          {props.busy ? 'Wrapping…' : on.size === 0 ? 'Tick at least one person' : `Make our Wrapped (${on.size} named)`}
        </Button>
      </div>
    </main>
  );
}
