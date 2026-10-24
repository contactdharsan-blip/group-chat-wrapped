// Screenshot every <section class="slide"> of an HTML page to slide-NN.png
// with Playwright WebKit (never Chromium).
//   node render_slides.cjs <slides.html> <out dir>
// PLAYWRIGHT_CORE may point at a playwright-core install; it is only required, never modified.
const path = require('path');
const { pathToFileURL } = require('url');
const { webkit } = require(process.env.PLAYWRIGHT_CORE || 'playwright-core');

(async () => {
  const [html, outDir] = process.argv.slice(2);
  const browser = await webkit.launch();
  try {
    const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
    await page.goto(pathToFileURL(path.resolve(html)).href);
    await page.evaluate(() => document.fonts.ready);
    const ids = await page.$$eval('section.slide', (els) => els.map((e) => e.id));
    // Safe-zone check: nothing inside a slide may reach the bottom 350 px or the right 120 px.
    const overflow = await page.$$eval('section.slide', (els) => els.flatMap((s) => {
      const box = s.getBoundingClientRect();
      let bottom = 0, right = 0;
      for (const el of s.querySelectorAll('.safe *')) {
        const r = el.getBoundingClientRect();
        if (r.width === 0 || r.height === 0) continue;
        bottom = Math.max(bottom, r.bottom - box.top);
        right = Math.max(right, r.right - box.left);
      }
      return bottom > 1920 - 350 || right > 1080 - 120 ? [`${s.id} bottom=${Math.round(bottom)} right=${Math.round(right)}`] : [];
    }));
    for (const line of overflow) console.error('SAFE-ZONE ' + line);
    for (const id of ids) {
      const file = path.join(outDir, id + '.png');
      await page.locator('#' + id).screenshot({ path: file });
      console.log(file);
    }
  } finally {
    await browser.close();
  }
})().catch((e) => { console.error(e); process.exit(1); });
