import { motion } from 'motion/react';
import { FileUp, Lock, Sparkles } from 'lucide-react';
import { useRef, useState } from 'react';
import type { Format } from '../api';
import { slideUp, staggerContainer, staggerItem } from '../motion';
import { AddCards } from './AddToChat';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

const HOWTO: { id: Format; label: string; how: string }[] = [
  { id: 'whatsapp', label: 'WhatsApp', how: 'Open the chat, tap its name, Export chat, Without media. Upload the .txt.' },
  { id: 'instagram', label: 'Instagram', how: 'Accounts Center, Your information, Download your information, Messages, JSON. Upload message_1.json.' },
  { id: 'discord', label: 'Discord', how: 'Export the channel with DiscordChatExporter as JSON, or just add the bot.' },
  { id: 'csv', label: 'CSV', how: 'Any spreadsheet with timestamp, author and text columns.' },
];

export function Landing(props: {
  live: boolean;
  busy: boolean;
  error: string | null;
  onDemo: () => void;
  onFile: (f: File, fmt: Format) => void;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [drag, setDrag] = useState(false);
  const [help, setHelp] = useState<Format | null>(null);

  const pick = (f: File | undefined) => {
    if (f) props.onFile(f, help ?? 'auto');
  };

  return (
    <main data-testid="screen-landing" className="relative z-10 mx-auto w-full max-w-5xl px-4 pb-16 pt-10 sm:pt-16">
      <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="flex flex-col items-center text-center">
        <motion.div variants={staggerItem} className="mb-6">
          <Badge className="h-auto bg-lime px-3 py-1 text-xs text-black">
            <Sparkles aria-hidden="true" /> Group chat assistant · end of semester
          </Badge>
        </motion.div>
        <motion.h1 variants={staggerItem} className="font-head text-[44px] leading-[0.95] sm:text-7xl">
          Your group chat,
          <br />
          <span className="mt-3 inline-block -rotate-2 rounded-lg border-[3px] border-black bg-pink px-4 pb-2 pt-1 shadow-lg sm:mt-4">Wrapped.</span>
        </motion.h1>
        <motion.p variants={staggerItem} className="mt-7 max-w-xl text-base font-medium leading-relaxed sm:text-lg">
          Who said “omw” the most while very much not on the way? Who sends paragraphs at 3 AM? Eleven awards, each one backed by the receipt.
        </motion.p>
        <motion.div variants={staggerItem} className="mt-7 flex w-full flex-col items-center gap-3 sm:w-auto sm:flex-row">
          <Button size="lg" className="min-h-12 w-full text-base duration-100 sm:w-auto" onClick={props.onDemo} disabled={props.busy} data-testid="demo-button">
            {props.busy ? 'Wrapping…' : 'Try the demo chat'}
          </Button>
          <Button asChild variant="outline" size="lg" className="min-h-12 w-full bg-white text-base duration-100 sm:w-auto">
            <a href="#add">Add it to your group chat</a>
          </Button>
        </motion.div>
        <motion.p variants={staggerItem} className="mt-5 inline-flex items-center gap-1.5 text-sm font-medium" data-testid="privacy-line">
          <Lock size={14} aria-hidden="true" /> Nothing is stored. Only people who opt in get named.
        </motion.p>
      </motion.div>

      <motion.section id="add" variants={slideUp} initial="hidden" animate="visible" className="mt-16 scroll-mt-6">
        <h2 className="text-2xl sm:text-3xl">Add it to your group chat</h2>
        <p className="mt-1 text-muted-foreground">Run it right where your friends already are.</p>
        <div className="mt-5">
          <AddCards only={['discord', 'imessage']} />
        </div>
      </motion.section>

      <motion.section variants={slideUp} initial="hidden" animate="visible" className="mt-12">
        <h2 className="text-2xl sm:text-3xl">Or upload an export</h2>
        <p className="mt-1 text-muted-foreground">The way in for Instagram and WhatsApp, which no bot can join.</p>

        {props.live ? (
          <div
            data-testid="dropzone"
            className={`mt-5 flex cursor-pointer flex-col items-center gap-3 rounded-lg border-[3px] border-dashed border-black px-5 py-10 text-center shadow-md transition-colors duration-100 ${drag ? 'bg-yellow' : 'bg-white hover:bg-accent'}`}
            onClick={() => input.current?.click()}
            onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
            onDragLeave={() => setDrag(false)}
            onDrop={(e) => { e.preventDefault(); setDrag(false); pick(e.dataTransfer.files[0]); }}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') input.current?.click(); }}
          >
            <span className="flex h-14 w-14 items-center justify-center rounded-lg border-2 border-black bg-blue text-white shadow-sm"><FileUp size={26} aria-hidden="true" /></span>
            <div>
              <p className="font-head text-xl">Drop your chat export here</p>
              <p className="mt-1 text-sm text-muted-foreground">.txt, .json or .csv, up to 20 MB. Read in memory, then forgotten.</p>
            </div>
            <input
              ref={input}
              type="file"
              accept=".txt,.json,.csv,text/plain,application/json,text/csv"
              className="hidden"
              data-testid="file-input"
              onChange={(e) => { pick(e.target.files?.[0]); e.target.value = ''; }}
            />
          </div>
        ) : (
          <Card className="mt-5 px-5 py-6 text-sm" data-testid="static-note">
            <p>This is the static demo, so uploads are off here. Run the app locally (<code className="rounded border-2 border-black bg-accent px-1 font-mono">python -m wrapped.server</code>) to wrap your own chat.</p>
          </Card>
        )}
        {props.error && <p role="alert" className="mt-3 rounded-lg border-2 border-black bg-destructive px-4 py-3 text-sm font-medium text-white shadow-sm">{props.error}</p>}

        <div className="no-scrollbar -mx-4 mt-5 flex gap-2 overflow-x-auto px-4 pb-2" role="group" aria-label="How to export">
          {HOWTO.map((h) => (
            <button
              key={h.id}
              type="button"
              className={`press flex-none rounded-full border-2 border-black px-3.5 py-2 text-sm font-medium shadow-sm ${help === h.id ? 'bg-yellow' : 'bg-white'}`}
              onClick={() => setHelp(help === h.id ? null : h.id)}
              aria-pressed={help === h.id}
            >
              How to export: {h.label}
            </button>
          ))}
        </div>
        {help && <p className="mt-3 text-sm leading-relaxed">{HOWTO.find((h) => h.id === help)?.how}</p>}
      </motion.section>
    </main>
  );
}
