import { CirclePlay, House, MessageCirclePlus, UsersRound } from 'lucide-react';
import { useLayoutEffect, useRef, useState } from 'react';

export type Tab = 'feed' | 'story' | 'group' | 'add';

const TABS: { id: Tab; label: string; Icon: typeof House }[] = [
  { id: 'feed', label: 'Feed', Icon: House },
  { id: 'story', label: 'Story', Icon: CirclePlay },
  { id: 'group', label: 'Group', Icon: UsersRound },
  { id: 'add', label: 'Add to chat', Icon: MessageCirclePlus },
];

/** BioPath's segmented control: a liquid glass pill that springs to the active tab and squishes on arrival. */
function Selector({ tab, onTab, vertical }: { tab: Tab; onTab: (t: Tab) => void; vertical: boolean }) {
  const track = useRef<HTMLDivElement>(null);
  const [box, setBox] = useState<{ left: number; top: number; width: number; height: number } | null>(null);
  const [moving, setMoving] = useState(false);

  useLayoutEffect(() => {
    const el = track.current;
    if (!el) return;
    const place = () => {
      const btn = el.querySelector<HTMLButtonElement>(`[data-tab="${tab}"]`);
      if (btn) setBox({ left: btn.offsetLeft, top: btn.offsetTop, width: btn.offsetWidth, height: btn.offsetHeight });
    };
    place();
    const ro = new ResizeObserver(place);
    ro.observe(el);
    return () => ro.disconnect();
  }, [tab, vertical]);

  useLayoutEffect(() => {
    setMoving(true);
    const t = setTimeout(() => setMoving(false), 400);
    return () => clearTimeout(t);
  }, [tab]);

  return (
    <div ref={track} className="mode-selector" role="tablist" aria-orientation={vertical ? 'vertical' : 'horizontal'}>
      {box && (
        <span
          className={`mode-glass-indicator ${moving ? 'moving' : ''}`}
          style={{ left: box.left, width: box.width, top: box.top, height: box.height, bottom: 'auto' }}
          aria-hidden="true"
        />
      )}
      {TABS.map(({ id, label, Icon }) => (
        <button
          key={id}
          type="button"
          role="tab"
          data-tab={id}
          data-testid={`tab-${id}`}
          aria-selected={tab === id}
          className={`mode-btn ${tab === id ? 'active' : ''}`}
          onClick={() => onTab(id)}
        >
          <Icon size={vertical ? 18 : 20} strokeWidth={2} aria-hidden="true" />
          <span>{label}</span>
        </button>
      ))}
    </div>
  );
}

export function BottomNav(props: { tab: Tab; onTab: (t: Tab) => void }) {
  return (
    <nav className="bottom-nav" aria-label="Main">
      <div className="mx-auto max-w-xl">
        <Selector {...props} vertical={false} />
      </div>
    </nav>
  );
}
