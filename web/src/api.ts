import type { MembersResponse, Wrapped } from './types';

// Relative URLs, so the same build works behind the Python server and from a static host.
async function json<T>(res: Response): Promise<T> {
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new Error((body && body.error) || `Request failed (${res.status})`);
  return body as T;
}

/** true when the Python API answers; false on a static host (then the demo plays from demo.json). */
export async function apiAvailable(): Promise<boolean> {
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), 2000);
  try {
    const res = await fetch('./api/health', { signal: ctl.signal });
    if (!res.ok) return false;
    const body = await res.json();
    return body?.ok === true;
  } catch {
    return false;
  } finally {
    clearTimeout(timer);
  }
}

export async function loadDemo(live: boolean): Promise<Wrapped> {
  return json<Wrapped>(await fetch(live ? './api/demo' : './demo.json'));
}

export type Format = 'auto' | 'whatsapp' | 'discord' | 'csv' | 'instagram';

export async function fetchMembers(file: File, format: Format): Promise<MembersResponse> {
  const form = new FormData();
  form.append('file', file);
  form.append('format', format);
  return json<MembersResponse>(await fetch('./api/members', { method: 'POST', body: form }));
}

export async function fetchWrapped(file: File, format: Format, optin: string[], name: string): Promise<Wrapped> {
  const form = new FormData();
  form.append('file', file);
  form.append('format', format);
  form.append('name', name);
  for (const n of optin) form.append('optin', n);
  return json<Wrapped>(await fetch('./api/wrapped', { method: 'POST', body: form }));
}
