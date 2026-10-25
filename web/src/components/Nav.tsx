import { CirclePlay, House, MessageCirclePlus, UsersRound } from 'lucide-react';

export type Tab = 'feed' | 'story' | 'group' | 'add';

const TABS: { id: Tab; label: string; Icon: typeof House }[] = [
  { id: 'feed', label: 'Feed', Icon: House },
  { id: 'story', label: 'Story', Icon: CirclePlay },
  { id: 'group', label: 'Group', Icon: UsersRound },
  { id: 'add', label: 'Add to chat', Icon: MessageCirclePlus },
];

/** A chunky bordered bar; the active tab is a filled yellow block that presses down. */
export function BottomNav({ tab, onTab }: { tab: Tab; onTab: (t: Tab) => void }) {
  return (
    <nav className="bottom-nav" aria-label="Main">
      <div className="mx-auto max-w-xl">
        <div className="mode-selector" role="tablist" aria-orientation="horizontal">
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
              <Icon size={20} strokeWidth={2.5} aria-hidden="true" />
              <span>{label}</span>
            </button>
          ))}
        </div>
      </div>
    </nav>
  );
}
