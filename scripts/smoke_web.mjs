// Smoke test for the web app in WebKit (never Chromium).
//   node scripts/smoke_web.mjs            (after `npm --prefix web run build:static`)
// Starts the Python server and a plain static server as child processes, drives
// landing -> demo -> feed -> profile -> story rings -> story -> group -> add to chat,
// then uploads demo/demo-chat.txt with Jordan and Theo left unticked and checks their
// names appear nowhere in the DOM on any later screen. Screenshots go to out/screens/.
// Also checks the static build plays the demo from demo.json with upload hidden.
import { spawn } from 'node:child_process';
import { mkdirSync } from 'node:fs';
import { createRequire } from 'node:module';
import net from 'node:net';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const { webkit } = require(process.env.PLAYWRIGHT_CORE || '/Users/Dharsan/Downloads/free-food-demo/node_modules/playwright-core');

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const SHOTS = path.join(ROOT, 'out', 'screens');
const PY = process.env.PYTHON || path.join(ROOT, '.venv', 'bin', 'python');
const HIDDEN = [/\bjordan\b/i, /\btheo\b/i];
const SIZES = [{ name: 'mobile', width: 390, height: 844 }, { name: 'desktop', width: 1440, height: 900 }];

let failures = 0;
const check = (ok, msg) => { console.log(`${ok ? 'ok  ' : 'FAIL'} ${msg}`); if (!ok) failures++; };

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

function start(cmd, args) {
  const child = spawn(cmd, args, { cwd: ROOT, stdio: ['ignore', 'ignore', 'pipe'] });
  child.stderr.on('data', (d) => { const t = String(d); if (/Error|Traceback/.test(t)) process.stderr.write(t); });
  return child;
}

async function shot(page, size, name) {
  await page.waitForTimeout(700); // let entry springs settle
  await page.screenshot({ path: path.join(SHOTS, `${size}-${name}.png`), fullPage: false });
}

async function noHorizontalScroll(page, label) {
  const { sw, iw } = await page.evaluate(() => ({ sw: document.documentElement.scrollWidth, iw: window.innerWidth }));
  check(sw <= iw, `${label}: no horizontal scroll (${sw} <= ${iw})`);
}

async function hiddenAbsent(page, label) {
  const html = await page.evaluate(() => document.title + document.documentElement.outerHTML);
  check(HIDDEN.every((re) => !re.test(html)), `${label}: Jordan and Theo appear nowhere in the DOM`);
}

async function playThrough(page, label, after) {
  await page.getByTestId('phone').waitFor();
  const total = Number(await page.getByTestId('phone').getAttribute('data-slides'));
  for (let i = 0; i < total - 1; i++) {
    await page.getByTestId('story-next').click();
    await page.waitForFunction((n) => document.querySelector('[data-testid=phone]')?.getAttribute('data-slide') === String(n), i + 1);
    if (after) await after(i + 1);
  }
  const last = Number(await page.getByTestId('phone').getAttribute('data-slide'));
  check(last === total - 1, `${label}: advanced through all ${total} slides`);
  await page.getByTestId('story-prev').click();
  const back = Number(await page.getByTestId('phone').getAttribute('data-slide'));
  check(back === total - 2, `${label}: tap left goes back`);
  await page.keyboard.press('ArrowRight');
  check(Number(await page.getByTestId('phone').getAttribute('data-slide')) === total - 1, `${label}: arrow key advances`);
}

async function demoTour(browser, base, size) {
  const page = await browser.newPage({ viewport: { width: size.width, height: size.height } });
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  await page.goto(base);
  await page.getByTestId('screen-landing').waitFor();
  await page.waitForFunction(() => !document.querySelector('[data-testid=demo-button]')?.disabled);
  check(await page.getByTestId('privacy-line').isVisible(), `${size.name}: privacy line visible`);
  check(await page.getByTestId('dropzone').count() === 1, `${size.name}: upload shown when the API is up`);
  await shot(page, size.name, '01-landing');
  await noHorizontalScroll(page, `${size.name} landing`);
  await page.getByTestId('add-discord').scrollIntoViewIfNeeded();
  await shot(page, size.name, '02-landing-add');

  await page.getByTestId('demo-button').click();
  await page.getByTestId('screen-feed').waitFor();
  const blur = await page.evaluate(() => {
    const el = document.querySelector('.glass');
    const cs = getComputedStyle(el);
    return cs.backdropFilter || cs.webkitBackdropFilter;
  });
  check(blur && blur !== 'none', `${size.name}: glass has a backdrop blur (${blur})`);
  check(await page.getByTestId('feed-post').count() === 11, `${size.name}: feed has 11 award posts`);
  check(await page.getByTestId('story-ring').count() === 4, `${size.name}: 4 person story rings + group`);
  await shot(page, size.name, '03-feed');
  await noHorizontalScroll(page, `${size.name} feed`);
  await page.getByTestId('like').first().click();
  check((await page.getByTestId('like').first().getAttribute('aria-pressed')) === 'true', `${size.name}: like toggles locally`);

  await page.getByTestId('post-avatar').first().click();
  await page.getByTestId('screen-profile').waitFor();
  const who = await page.getByTestId('screen-profile').getAttribute('data-profile');
  check(await page.getByTestId('profile-post').count() > 0, `${size.name}: ${who}'s profile shows posts`);
  await shot(page, size.name, '04-profile');
  await noHorizontalScroll(page, `${size.name} profile`);
  await page.mouse.wheel(0, 900);
  await shot(page, size.name, '05-profile-posts');
  await page.getByTestId('profile-back').click();
  await page.getByTestId('screen-feed').waitFor();

  await page.getByTestId('story-ring').nth(1).click();
  await page.getByTestId('screen-story').waitFor();
  await shot(page, size.name, '06-story-person');
  await playThrough(page, `${size.name} person story`);
  await page.getByTestId('story-close').click();
  await page.getByTestId('screen-feed').waitFor();

  await page.getByTestId('story-ring-group').click();
  await page.getByTestId('screen-story').waitFor();
  await shot(page, size.name, '07-story-cover');
  await playThrough(page, `${size.name} group story`, async (i) => {
    if (i === 1) await shot(page, size.name, '08-story-totals');
    if (i === 3) await shot(page, size.name, '09-story-award');
    if (i === 4) await shot(page, size.name, '10-story-award-long');
  });
  await shot(page, size.name, '11-story-closing');
  await page.getByTestId('story-pause').click();

  await page.getByTestId('tab-group').click();
  await page.getByTestId('screen-group').waitFor();
  check(await page.getByTestId('recap-featured').count() === 1, `${size.name}: recap has the featured tile`);
  await shot(page, size.name, '12-group');
  await noHorizontalScroll(page, `${size.name} group`);
  await page.getByTestId('recap').scrollIntoViewIfNeeded();
  await shot(page, size.name, '13-group-recap');

  await page.getByTestId('tab-add').click();
  await page.getByTestId('screen-add').waitFor();
  check(await page.getByTestId('add-instagram').count() === 1, `${size.name}: add-to-chat lists Discord, iMessage, Instagram`);
  await shot(page, size.name, '14-add');
  await noHorizontalScroll(page, `${size.name} add`);
  check(errors.length === 0, `${size.name}: no page errors ${errors.join(' | ')}`);
  await page.close();
}

async function uploadTour(browser, base, size) {
  const page = await browser.newPage({ viewport: { width: size.width, height: size.height } });
  await page.goto(base);
  await page.getByTestId('file-input').setInputFiles(path.join(ROOT, 'demo', 'demo-chat.txt'));
  await page.getByTestId('screen-optin').waitFor();
  check(await page.getByTestId('optin-toggle').count() === 4, `${size.name} upload: 4 members to opt in`);
  await shot(page, size.name, '15-optin');
  for (const name of ['Maya', 'Priya']) await page.locator(`[data-testid=optin-toggle][data-name="${name}"]`).check({ force: true });
  await page.locator('#chat-name').fill('Floor 4 Survivors');
  await shot(page, size.name, '16-optin-ticked');
  await page.getByTestId('make-wrapped').click();
  await page.getByTestId('screen-feed').waitFor();
  check(await page.getByTestId('story-ring').count() === 2, `${size.name} upload: only the 2 opted-in people get story rings`);
  await hiddenAbsent(page, `${size.name} upload feed`);
  await shot(page, size.name, '17-upload-feed');

  const people = await page.getByTestId('post-avatar').count();
  for (let i = 0; i < Math.min(people, 4); i++) {
    await page.getByTestId('post-avatar').nth(i).click();
    await page.getByTestId('screen-profile').waitFor();
    await hiddenAbsent(page, `${size.name} upload profile ${await page.getByTestId('screen-profile').getAttribute('data-profile')}`);
    await page.getByTestId('profile-back').click();
    await page.getByTestId('screen-feed').waitFor();
  }
  await page.getByTestId('story-ring-group').click();
  await playThrough(page, `${size.name} upload story`, async (i) => hiddenAbsent(page, `${size.name} upload story slide ${i}`));
  await page.getByTestId('tab-group').click();
  await page.getByTestId('screen-group').waitFor();
  check((await page.getByTestId('someone-chip').textContent())?.includes('+2 someone'), `${size.name} upload: group shows "+2 someone"`);
  await hiddenAbsent(page, `${size.name} upload group`);
  await shot(page, size.name, '18-upload-group');
  await page.getByTestId('tab-add').click();
  await hiddenAbsent(page, `${size.name} upload add`);
  await page.close();
}

async function staticTour(browser, base) {
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  await page.goto(base);
  await page.getByTestId('static-note').waitFor({ timeout: 8000 });
  check(await page.getByTestId('dropzone').count() === 0, 'static: upload hidden, note shown');
  await shot(page, 'mobile', '19-static-landing');
  await page.getByTestId('demo-button').click();
  await page.getByTestId('screen-feed').waitFor();
  check(await page.getByTestId('feed-post').count() === 11, 'static: demo plays from demo.json');
  await page.close();
}

const procs = [];
let browser;
try {
  mkdirSync(SHOTS, { recursive: true });
  const apiPort = await freePort();
  const staticPort = await freePort();
  procs.push(start(PY, ['-m', 'wrapped.server', '--port', String(apiPort)]));
  procs.push(start(PY, ['-m', 'http.server', String(staticPort), '--bind', '127.0.0.1', '--directory', path.join(ROOT, 'web', 'dist')]));
  const api = `http://127.0.0.1:${apiPort}/`;
  const stat = `http://127.0.0.1:${staticPort}/`;
  await waitFor(api + 'api/health');
  await waitFor(stat + 'demo.json');
  console.log(`server ${api}  static ${stat}`);
  browser = await webkit.launch();
  for (const size of SIZES) {
    await demoTour(browser, api, size);
    await uploadTour(browser, api, size);
  }
  await staticTour(browser, stat);
} catch (e) {
  console.error(e);
  failures++;
} finally {
  if (browser) await browser.close();
  for (const p of procs) p.kill('SIGTERM');
}
console.log(failures ? `\n${failures} check(s) failed` : `\nall checks passed; screenshots in ${SHOTS}`);
process.exit(failures ? 1 : 0);
