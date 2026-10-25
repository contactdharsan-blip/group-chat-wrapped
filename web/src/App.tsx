import { AnimatePresence, motion } from 'motion/react';
import { useEffect, useState } from 'react';
import { apiAvailable, fetchMembers, fetchWrapped, loadDemo, type Format } from './api';
import type { MembersResponse, Wrapped } from './types';
import { BottomNav, type Tab } from './components/Nav';
import { fadeIn } from './motion';
import { AddToChat } from './screens/AddToChat';
import { Feed } from './screens/Feed';
import { Group } from './screens/Group';
import { Landing } from './screens/Landing';
import { OptIn } from './screens/OptIn';
import { ProfilePage } from './screens/ProfilePage';
import { Story } from './screens/Story';

// The upload and its member list live here only between upload and the /api/wrapped
// response. After that they are dropped, so no screen past opt-in can show a name
// that wasn't ticked.
interface Pending { file: File; format: Format; members: MembersResponse }

function Ambient() {
  return (
    <div className="app-bg" aria-hidden="true">
      <div className="glow-blob glow-a" />
      <div className="glow-blob glow-b" />
      <div className="glow-blob glow-c" />
    </div>
  );
}

export default function App() {
  const [live, setLive] = useState<boolean | null>(null);
  const [pending, setPending] = useState<Pending | null>(null);
  const [data, setData] = useState<Wrapped | null>(null);
  const [tab, setTab] = useState<Tab>('feed');
  const [profile, setProfile] = useState<string | null>(null);
  const [storyWho, setStoryWho] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { apiAvailable().then(setLive); }, []);
  useEffect(() => { window.scrollTo({ top: 0 }); }, [tab, profile, data]);

  const run = async (fn: () => Promise<void>) => {
    setBusy(true);
    setError(null);
    try { await fn(); } catch (e) { setError(e instanceof Error ? e.message : 'Something went wrong.'); } finally { setBusy(false); }
  };

  const open = (w: Wrapped) => { setData(w); setTab('feed'); setProfile(null); setStoryWho(null); };
  const home = () => { setData(null); setPending(null); setError(null); };

  const onDemo = () => run(async () => open(await loadDemo(live === true)));
  const onFile = (file: File, format: Format) => run(async () => setPending({ file, format, members: await fetchMembers(file, format) }));
  const onGo = (optin: string[], name: string) => run(async () => {
    if (!pending) return;
    const w = await fetchWrapped(pending.file, pending.format, optin, name);
    setPending(null);
    open(w);
  });

  const play = (who: string | null) => { setStoryWho(who); setProfile(null); setTab('story'); };
  const goTab = (t: Tab) => { setProfile(null); if (t === 'story' && tab !== 'story') setStoryWho(null); setTab(t); };

  if (!data) {
    return (
      <>
        <Ambient />
        <AnimatePresence mode="wait">
          <motion.div key={pending ? 'optin' : 'landing'} variants={fadeIn} initial="hidden" animate="visible" exit="exit">
            {pending ? (
              <OptIn members={pending.members} busy={busy} error={error} onBack={() => { setPending(null); setError(null); }} onGo={onGo} />
            ) : (
              <Landing live={live !== false} busy={busy || live === null} error={error} onDemo={onDemo} onFile={onFile} />
            )}
          </motion.div>
        </AnimatePresence>
      </>
    );
  }

  const person = profile ? data.profiles.find((p) => p.name === profile) : undefined;
  let screen;
  if (person) screen = <ProfilePage data={data} p={person} onBack={() => setProfile(null)} onPlay={play} />;
  else if (tab === 'feed') screen = <Feed data={data} onProfile={setProfile} onPlay={play} />;
  else if (tab === 'story') screen = <Story data={data} who={storyWho} onClose={() => goTab('feed')} />;
  else if (tab === 'group') screen = <Group data={data} onProfile={setProfile} />;
  else screen = <AddToChat />;

  return (
    <>
      <Ambient />
      <div className="relative z-10 flex min-h-screen">
        <div className="min-w-0 flex-1">
          <div className="mx-auto flex max-w-xl items-center justify-between px-4 pt-4">
            <button type="button" onClick={home} className="flex items-center gap-2" data-testid="home">
              <span className="h-7 w-7 rounded-lg" style={{ background: 'linear-gradient(135deg,#a78bfa,#e879f9)' }} aria-hidden="true" />
              <span className="font-display font-bold">Wrapped</span>
            </button>
            <span className="text-[11px] text-slate-400">Nothing is stored</span>
          </div>
          <AnimatePresence mode="wait">
            <motion.div key={person ? `p-${person.name}` : tab} variants={fadeIn} initial="hidden" animate="visible" exit="exit">
              {screen}
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
      <BottomNav tab={tab} onTab={goTab} />
    </>
  );
}
