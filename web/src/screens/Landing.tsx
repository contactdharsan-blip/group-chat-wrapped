import { motion } from 'motion/react';
import { FileUp, Lock, Sparkles } from 'lucide-react';
import { useRef, useState } from 'react';
import type { Format } from '../api';
import { slideUp, staggerContainer, staggerItem } from '../motion';
import { AddCards } from './AddToChat';

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
        <motion.span variants={staggerItem} className="glass-subtle mb-5 inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-medium text-violet-200">
          <Sparkles size={14} aria-hidden="true" /> Group chat assistant · end of semester
        </motion.span>
        <motion.h1 variants={staggerItem} className="font-display text-[44px] font-extrabold leading-[0.95] sm:text-7xl">
          Your group chat,
          <br />
          <span className="bg-gradient-to-r from-violet-300 via-fuchsia-300 to-sky-300 bg-clip-text text-transparent">Wrapped.</span>
        </motion.h1>
        <motion.p variants={staggerItem} className="mt-5 max-w-xl text-base leading-relaxed text-slate-300 sm:text-lg">
          Who said “omw” the most while very much not on the way? Who sends paragraphs at 3 AM? Eleven awards, each one backed by the receipt.
        </motion.p>
        <motion.div variants={staggerItem} className="mt-7 flex w-full flex-col items-center gap-3 sm:w-auto sm:flex-row">
          <button type="button" className="btn-primary w-full px-7 text-base sm:w-auto" onClick={props.onDemo} disabled={props.busy} data-testid="demo-button">
            {props.busy ? 'Wrapping…' : 'Try the demo chat'}
          </button>
          <a href="#add" className="btn-glass w-full sm:w-auto">Add it to your group chat</a>
        </motion.div>
        <motion.p variants={staggerItem} className="mt-4 inline-flex items-center gap-1.5 text-sm text-slate-300" data-testid="privacy-line">
          <Lock size={14} aria-hidden="true" /> Nothing is stored. Only people who opt in get named.
        </motion.p>
      </motion.div>

      <motion.section id="add" variants={slideUp} initial="hidden" animate="visible" className="mt-16 scroll-mt-6">
        <h2 className="font-display text-2xl font-bold sm:text-3xl">Add it to your group chat</h2>
        <p className="mt-1 text-slate-300">Run it right where your friends already are.</p>
        <div className="mt-5">
          <AddCards only={['discord', 'imessage']} />
        </div>
      </motion.section>

      <motion.section variants={slideUp} initial="hidden" animate="visible" className="mt-12">
        <h2 className="font-display text-2xl font-bold sm:text-3xl">Or upload an export</h2>
        <p className="mt-1 text-slate-300">The way in for Instagram and WhatsApp, which no bot can join.</p>

        {props.live ? (
          <div
            data-testid="dropzone"
            className={`glass mt-5 flex cursor-pointer flex-col items-center gap-3 border-dashed px-5 py-10 text-center transition ${drag ? 'border-violet-300/70 bg-violet-400/10' : ''}`}
            onClick={() => input.current?.click()}
            onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
            onDragLeave={() => setDrag(false)}
            onDrop={(e) => { e.preventDefault(); setDrag(false); pick(e.dataTransfer.files[0]); }}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') input.current?.click(); }}
          >
            <span className="glass-strong flex h-14 w-14 items-center justify-center rounded-2xl"><FileUp size={26} aria-hidden="true" /></span>
            <div>
              <p className="font-display text-xl font-bold">Drop your chat export here</p>
              <p className="mt-1 text-sm text-slate-400">.txt, .json or .csv, up to 20 MB. Read in memory, then forgotten.</p>
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
          <div className="glass mt-5 px-5 py-6 text-sm text-slate-300" data-testid="static-note">
            This is the static demo, so uploads are off here. Run the app locally (<code className="font-mono text-violet-200">python -m wrapped.server</code>) to wrap your own chat.
          </div>
        )}
        {props.error && <p role="alert" className="mt-3 rounded-xl border border-rose-400/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">{props.error}</p>}

        <div className="no-scrollbar mt-4 flex gap-2 overflow-x-auto pb-1" role="group" aria-label="How to export">
          {HOWTO.map((h) => (
            <button
              key={h.id}
              type="button"
              className={`glass-subtle flex-none rounded-full px-3.5 py-2 text-sm transition ${help === h.id ? 'border-violet-300/60 text-white' : 'text-slate-300'}`}
              onClick={() => setHelp(help === h.id ? null : h.id)}
              aria-pressed={help === h.id}
            >
              How to export: {h.label}
            </button>
          ))}
        </div>
        {help && <p className="mt-3 text-sm leading-relaxed text-slate-300">{HOWTO.find((h) => h.id === help)?.how}</p>}
      </motion.section>
    </main>
  );
}
