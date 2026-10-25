import { motion } from 'motion/react';
import { staggerContainer, staggerItem } from '../motion';

function Cmd({ children }: { children: React.ReactNode }) {
  return <code className="rounded-md bg-white/10 px-1.5 py-0.5 font-mono text-[13px] text-violet-200">{children}</code>;
}

const CARDS = [
  {
    id: 'discord',
    name: 'Discord',
    tag: 'Bot',
    dot: '#818cf8',
    steps: [
      <>Invite the Wrapped bot to your server.</>,
      <>Everyone who wants to be in it runs <Cmd>/wrapped optin</Cmd>.</>,
      <>Anyone runs <Cmd>/wrapped run</Cmd>: the slides post in the channel, then one card per award with its receipt.</>,
      <><Cmd>/wrapped-me</Cmd> posts your own profile card.</>,
    ],
  },
  {
    id: 'imessage',
    name: 'iMessage',
    tag: 'Mac bridge',
    dot: '#38bdf8',
    steps: [
      <>One person in the group runs the bridge on their Mac.</>,
      <>Members type <Cmd>wrapped optin</Cmd> in the group.</>,
      <>Anyone types <Cmd>wrapped</Cmd> and the slides arrive in the chat.</>,
      <>Only people who opted in are named; everyone else is “someone”.</>,
    ],
  },
  {
    id: 'instagram',
    name: 'Instagram and WhatsApp',
    tag: 'Export',
    dot: '#e879f9',
    steps: [
      <>No bot can join these group chats, so export the chat and upload it here.</>,
      <>Instagram: Accounts Center, Download your information, Messages, format JSON.</>,
      <>WhatsApp: open the chat, Export chat, Without media.</>,
      <>The slides are 1080 by 1920, the Stories size, ready to post.</>,
    ],
  },
];

export function AddCards({ only }: { only?: string[] }) {
  return (
    <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {CARDS.filter((c) => !only || only.includes(c.id)).map((c) => (
        <motion.article key={c.id} variants={staggerItem} className="glass glass-hover p-5" data-testid={`add-${c.id}`}>
          <header className="mb-3 flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full" style={{ background: c.dot, boxShadow: `0 0 12px ${c.dot}` }} aria-hidden="true" />
            <h3 className="font-display text-lg font-bold">{c.name}</h3>
            <span className="ml-auto rounded-full border border-white/15 px-2 py-0.5 text-[11px] font-medium uppercase tracking-wider text-slate-300">{c.tag}</span>
          </header>
          <ol className="space-y-2 text-sm leading-relaxed text-slate-300">
            {c.steps.map((s, i) => (
              <li key={i} className="flex gap-2.5">
                <span className="mt-0.5 font-mono text-xs text-violet-300">{i + 1}</span>
                <span>{s}</span>
              </li>
            ))}
          </ol>
        </motion.article>
      ))}
    </motion.div>
  );
}

export function AddToChat() {
  return (
    <section data-testid="screen-add" className="mx-auto w-full max-w-5xl px-4 pb-32 pt-6">
      <h1 className="font-display text-3xl font-bold sm:text-4xl">Add it to your chat</h1>
      <p className="mt-2 max-w-xl text-slate-300">
        Wrapped lives where your group already talks. Same rules everywhere: only people who opt in are named, and every award quotes a real message.
      </p>
      <div className="mt-6">
        <AddCards />
      </div>
    </section>
  );
}
