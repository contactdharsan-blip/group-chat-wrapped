// Records the demo video in Playwright WebKit (never Chromium) and converts it to docs/demo.mp4.
//   npm --prefix web run build:static && node scripts/record_demo.mjs [out.mp4]
// Starts the Python server on a free port as a child process (stopped at the end), plays the invented
// demo chat (feed, story with receipts, a profile, the group page), then uploads demo/demo-chat.txt with
// Jordan and Theo left unticked to show the opt-in guarantee. Title cards are rendered in the same page.
// Needs ffmpeg on PATH (or FFMPEG) and PLAYWRIGHT_CORE pointing at a playwright-core install.
import { spawn, spawnSync } from 'node:child_process';
import { mkdtempSync, readdirSync, rmSync } from 'node:fs';
import { createRequire } from 'node:module';
import net from 'node:net';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const { webkit } = require(process.env.PLAYWRIGHT_CORE || '/Users/Dharsan/Downloads/free-food-demo/node_modules/playwright-core');

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const PY = process.env.PYTHON || path.join(ROOT, '.venv', 'bin', 'python');
const FFMPEG = process.env.FFMPEG || 'ffmpeg';
const OUT = path.resolve(process.argv[2] || path.join(ROOT, 'docs', 'demo.mp4'));
const SIZE = { width: 1280, height: 720 };
const REPO = 'https://github.com/contactdharsan-blip/group-chat-wrapped';

function freePort() {
  return new Promise((resolve, reject) => {
    const s = net.createServer();
    s.listen(0, '127.0.0.1', () => { const { port } = s.address(); s.close(() => resolve(port)); });
    s.on('error', reject);
  });
}

async function waitFor(url, ms = 20000) {
  const end = Date.now() + ms;
  while (Date.now() < end) {
    try { const r = await fetch(url); if (r.ok) return; } catch { /* not up yet */ }
    await new Promise((r) => setTimeout(r, 200));
  }
  throw new Error(`timed out waiting for ${url}`);
}

const card = (lines) => `<!doctype html><meta charset="utf-8">
<style>
  html,body{margin:0;height:100vh;background:#FFF6E5;font-family:-apple-system,"Helvetica Neue",sans-serif;color:#000}
  body{display:flex;align-items:center;justify-content:center;height:100vh}
  .box{border:4px solid #000;border-radius:14px;background:#fff;box-shadow:10px 10px 0 #000;padding:44px 56px;max-width:900px}
  h1{font-size:68px;line-height:1;margin:0 0 18px;font-weight:900}
  h1 span{background:#FF4FA3;border:3px solid #000;border-radius:10px;padding:0 14px;display:inline-block;transform:rotate(-2deg)}
  p{font-size:28px;line-height:1.35;margin:10px 0 0;font-weight:500}
  code{font-family:ui-monospace,Menlo,monospace;background:#D7FF5C;border:2px solid #000;border-radius:6px;padding:2px 10px;font-size:26px}
  small{display:block;margin-top:22px;font-size:20px;color:#444}
</style><div class="box">${lines}</div>`;

// A caption pill in the left gutter, outside React's root so re-renders leave it alone. 'top' sits
// beside the header, for the wide group page; it fits one short line.
async function caption(page, text, where = 'bottom') {
  await page.evaluate(([t, w]) => {
    let el = document.getElementById('rec-caption');
    if (!el) {
      el = document.createElement('div');
      el.id = 'rec-caption';
      el.style.cssText = 'position:fixed;left:20px;z-index:9999;background:#000;color:#fff;'
        + 'font:600 17px/1.35 -apple-system,"Helvetica Neue",sans-serif;padding:10px 16px;border-radius:10px';
      document.body.appendChild(el);
    }
    el.textContent = t;
    el.style.display = t ? 'block' : 'none';
    el.style.top = w === 'top' ? '8px' : '';
    el.style.bottom = w === 'top' ? '' : '20px';
    el.style.maxWidth = w === 'top' ? 'none' : '250px';
    el.style.whiteSpace = w === 'top' ? 'nowrap' : 'normal';
  }, [text, where]);
}

async function scrollBy(page, dy, steps = 12, ms = 60) {
  for (let i = 0; i < steps; i++) { await page.mouse.wheel(0, dy / steps); await page.waitForTimeout(ms); }
}

async function tour(page, base) {
  const wait = (ms) => page.waitForTimeout(ms);

  await page.setContent(card(`<h1>Group Chat <span>Wrapped</span></h1>
    <p>Spotify Wrapped for your group chat. Eleven awards, each backed by a real quoted message.</p>
    <p>Only people who opt in are named or quoted.</p>
    <small>Team hercules · Cubbie Hackathon, Track 3 · invented demo chat, no real people</small>`));
  await wait(4500);

  await page.goto(base);
  await page.getByTestId('screen-landing').waitFor();
  await page.waitForFunction(() => !document.querySelector('[data-testid=demo-button]')?.disabled);
  await wait(2500);
  await page.getByTestId('demo-button').click();
  await page.getByTestId('screen-feed').waitFor();
  await caption(page, 'The feed: one post per award, each with its receipt.');
  await wait(2500);
  await scrollBy(page, 520);
  await wait(2200);
  await scrollBy(page, 560);
  await wait(2200);
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'smooth' }));
  await wait(900);

  await caption(page, 'The story player. Every award slide quotes the message that earned it.');
  await page.getByTestId('story-ring-group').click();
  await page.getByTestId('screen-story').waitFor();
  await page.getByTestId('story-pause').click();
  await wait(2200);
  for (const hold of [2400, 2400, 3600, 3600, 3000]) {
    await page.getByTestId('story-next').click();
    await wait(hold);
  }
  await page.getByTestId('story-close').click();
  await page.getByTestId('screen-feed').waitFor();

  await caption(page, 'A profile per opted-in member: messages, awards, badges.');
  await page.getByTestId('post-avatar').first().click();
  await page.getByTestId('screen-profile').waitFor();
  await wait(2500);
  await scrollBy(page, 500);
  await wait(2200);
  await page.getByTestId('profile-back').click();
  await page.getByTestId('screen-feed').waitFor();

  await caption(page, 'The group page and recap.', 'top');
  await page.getByTestId('tab-group').click();
  await page.getByTestId('screen-group').waitFor();
  await wait(2800);
  await caption(page, '');

  await page.setContent(card(`<h1>Opt-in <span>only</span></h1>
    <p>Upload a chat export, then tick who agreed to be named.</p>
    <p>Everyone else still counts, as “someone”: no award, no quote, no profile.</p>`));
  await wait(4000);

  await page.goto(base);
  await page.getByTestId('screen-landing').waitFor();
  await page.waitForFunction(() => !document.querySelector('[data-testid=demo-button]')?.disabled);
  await page.getByTestId('file-input').setInputFiles(path.join(ROOT, 'demo', 'demo-chat.txt'));
  await page.getByTestId('screen-optin').waitFor();
  await caption(page, 'Uploaded the invented demo export. Nobody is named yet.');
  await wait(2500);
  await caption(page, 'Maya and Priya said yes. Jordan and Theo stay unticked.');
  for (const name of ['Maya', 'Priya']) {
    await page.locator(`[data-testid=optin-toggle][data-name="${name}"]`).check({ force: true });
    await wait(900);
  }
  await page.locator('#chat-name').fill('Floor 4 Survivors');
  await wait(1800);
  await page.getByTestId('make-wrapped').click();
  await page.getByTestId('screen-feed').waitFor();
  await caption(page, 'Only the two who opted in get story rings, posts and quotes.');
  await wait(3200);
  await page.getByTestId('tab-group').click();
  await page.getByTestId('screen-group').waitFor();
  await page.getByTestId('someone-chip').scrollIntoViewIfNeeded();
  await caption(page, 'Jordan, Theo: just “+2 someone”', 'top');
  await wait(3500);
  await caption(page, '');

  await page.setContent(card(`<h1>In <span>Discord</span></h1>
    <p><code>/wrapped optin</code> → <code>/wrapped run</code></p>
    <p>The bot posts the slides and one embed per award into the channel.</p>
    <small>Tested against fakes so far, not yet on a live server.</small>`));
  await wait(4000);

  await page.setContent(card(`<h1>Group Chat <span>Wrapped</span></h1>
    <p style="font-family:ui-monospace,Menlo,monospace;font-size:24px">${REPO.replace('https://', '')}</p>
    <small>Team hercules · Cubbie Hackathon, Track 3</small>`));
  await wait(4000);
}

const tmp = mkdtempSync(path.join(os.tmpdir(), 'wrapped-rec-'));
let server;
let browser;
let failed = false;
try {
  const port = await freePort();
  server = spawn(PY, ['-m', 'wrapped.server', '--port', String(port)], { cwd: ROOT, stdio: ['ignore', 'ignore', 'pipe'] });
  server.stderr.on('data', (d) => { const t = String(d); if (/Error|Traceback/.test(t)) process.stderr.write(t); });
  const base = `http://127.0.0.1:${port}/`;
  await waitFor(base + 'api/health');
  browser = await webkit.launch();
  const ctx = await browser.newContext({ viewport: SIZE, recordVideo: { dir: tmp, size: SIZE } });
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  await tour(page, base);
  await ctx.close();
  if (errors.length) throw new Error(`page errors: ${errors.join(' | ')}`);
  const webm = readdirSync(tmp).find((f) => f.endsWith('.webm'));
  const ff = spawnSync(FFMPEG, ['-y', '-loglevel', 'error', '-i', path.join(tmp, webm),
    '-vf', 'fps=30,format=yuv420p', '-c:v', 'libx264', '-crf', '20', '-preset', 'slow', '-an', '-movflags', '+faststart', OUT],
  { stdio: 'inherit' });
  if (ff.status !== 0) throw new Error('ffmpeg failed');
  console.log(`video -> ${OUT}`);
} catch (e) {
  console.error(e);
  failed = true;
} finally {
  if (browser) await browser.close();
  if (server) server.kill('SIGTERM');
  rmSync(tmp, { recursive: true, force: true });
}
process.exit(failed ? 1 : 0);
