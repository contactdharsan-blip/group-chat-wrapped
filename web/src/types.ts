export interface Receipt {
  author: string;
  ts: string;
  text: string;
}

export interface Award {
  key: string;
  title: string;
  winner: string;
  value_text: string;
  detail: string;
  receipt: Receipt;
  context?: Receipt;
  emoji?: string;
  word?: string;
  date?: string;
}

export interface GroupTotals {
  messages: number;
  words?: number;
  media?: number;
  people?: number;
  first?: string;
  last?: string;
  days?: number;
  busiest_hour?: string;
  busiest_hour_messages?: number;
  busiest_weekday?: string;
  busiest_weekday_messages?: number;
  share?: Record<string, number>;
}

export interface Post {
  award_key: string;
  award_title: string;
  text: string;
  ts: string;
  reactions: Record<string, number>;
}

export interface Profile {
  name: string;
  handle: string;
  initials: string;
  hue: number;
  messages: number;
  posts: number;
  awards: { key: string; title: string }[];
  peak_hour: string | null;
  top_emoji: { emoji: string; count: number }[];
  top_words: { word: string; count: number }[];
  receipts: Post[];
}

export type Member = Pick<Profile, 'name' | 'handle' | 'initials' | 'hue'>;

export interface Wrapped {
  chat_name: string;
  demo?: boolean;
  result: { group: GroupTotals; members: string[]; awards: Award[] };
  profiles: Profile[];
  group: {
    name: string;
    members: Member[];
    others: number;
    busiest_day: Award | null;
    group_word: Award | null;
  };
  captions: { source: 'template' | 'claude'; awards: Record<string, string>; bios: Record<string, string> };
}

export interface MembersResponse {
  format: string;
  messages: number;
  members: { name: string; messages: number }[];
}
