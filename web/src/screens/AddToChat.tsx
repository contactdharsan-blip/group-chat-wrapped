import { motion } from 'motion/react';
import { staggerContainer, staggerItem } from '../motion';
import { pop } from '../util';
import { Badge } from '@/components/ui/badge';

function Cmd({ children }: { children: React.ReactNode }) {
  return <code className="rounded border-2 border-black bg-accent px-1 py-px font-mono text-[13px] font-bold">{children}</code>;
}

const CARDS = [
  {
    id: 'discord',
    name: 'Discord',
    tag: 'Bot',
    pop: 1,
    steps: [
      <>Invite the Wrapped bot to your server.</>,
      <>Everyone who wants to be in it runs <Cmd>/wrapped optin</Cmd>.</>,
      <>Anyone runs <Cmd>/wrapped run</Cmd>: the slides post in the channel, then one card per award with its receipt.</>,
      <><Cmd>/wrapped me</Cmd> posts your own profile card.</>,
    ],
  },
  {
    id: 'imessage',
    name: 'iMessage',
    tag: 'Mac bridge',
    pop: 2,
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
    pop: 0,
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
        <motion.article key={c.id} variants={staggerItem} className="brut overflow-hidden" data-testid={`add-${c.id}`}>
          <header className="pop-fill flex items-center gap-2 border-b-2 border-black px-5 py-3" style={pop(c.pop)}>
            <h3 className="text-lg">{c.name}</h3>
            <Badge variant="outline" className="ml-auto bg-white uppercase tracking-wider text-black">{c.tag}</Badge>
          </header>
          <ol className="space-y-2.5 p-5 text-sm leading-relaxed">
            {c.steps.map((s, i) => (
              <li key={i} className="flex gap-2.5">
                <span className="flex h-5 w-5 flex-none items-center justify-center rounded-full border-2 border-black bg-yellow font-head text-[10px]">{i + 1}</span>
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
      <h1 className="text-3xl sm:text-4xl">Add it to your chat</h1>
      <p className="mt-2 max-w-xl font-medium">
        Wrapped lives where your group already talks. Same rules everywhere: only people who opt in are named, and every award quotes a real message.
      </p>
      <div className="mt-6">
        <AddCards />
      </div>
    </section>
  );
}
