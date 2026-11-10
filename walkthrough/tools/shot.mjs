// Screenshot helper: node tools/shot.mjs out.png [w h] [--stop=key | --pose=x,y,z,yaw,pitch] [--time=..] [--q=..] [--fly]
import { createRequire } from 'node:module';
const { chromium } = createRequire(import.meta.url)('playwright');
const args = process.argv.slice(2);
const opt = Object.fromEntries(args.filter((a) => a.startsWith('--')).map((a) => { const [k, v] = a.slice(2).split('='); return [k, v ?? true]; }));
const pos = args.filter((a) => !a.startsWith('--'));
const out = pos[0] || 'shot.png';
const w = +(pos[1] || 1280), h = +(pos[2] || 720);
const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--enable-webgl'] });
const page = await browser.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: +(opt.dpr || 1), hasTouch: !!opt.touch, isMobile: !!opt.touch });
page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') console.log('[console]', m.type(), m.text().slice(0, 600)); });
page.on('pageerror', (e) => console.log('[pageerror]', e.message));
const q = new URLSearchParams({ fixed: '1', manual: '1', q: opt.q || 'medium' });
if (opt.time) q.set('time', opt.time);
await page.goto(`http://localhost:${opt.port || 4173}/?${q}`);
await page.waitForFunction(() => window.__mk && window.__mk.ready, null, { timeout: 180000 });
if (!opt.nocity) await page.waitForFunction(() => window.__mk.city, null, { timeout: 180000 });
if (!opt.welcome) {
  await page.evaluate(() => { window.__mk.start(location.search.includes('free') ? 'free' : 'tour'); });
  await page.waitForTimeout(1200);
  if (opt.stop) { await page.evaluate((k) => { const mk = window.__mk; const i = mk.stops.findIndex((s) => s.key === k); mk.selectStop(i); return mk.goStop(i); }, opt.stop); await page.waitForTimeout(900); for (let k = 0; k < 400 && await page.evaluate(() => window.__mk.traveling); k++) { await page.evaluate(() => window.__mk.step(0.1, 3)); await page.waitForTimeout(30); } }
  if (opt.pose) {
    const p = opt.pose.split(',').map(Number);
    await page.evaluate((p) => { const mk = window.__mk; if (p[5]) mk.player.setMode('fly'); mk.player.setPose({ x: p[0], y: p[1], z: p[2] }, p[3], p[4]); }, p);
  }
  if (opt.hide) await page.addStyleTag({ content: '#hud{display:none!important}' });
  if (opt.eval) await page.evaluate(opt.eval);
}
await page.evaluate(([t, n]) => { window.__mk.step(t, 1); window.__mk.step(0.1, n); }, [+(opt.t || 3), +(opt.n || 24)]);
await page.waitForTimeout(300);
await page.screenshot({ path: out, timeout: 120000 });
console.log('saved', out, await page.evaluate(() => ({ ms: Math.round(window.__mk.emaMs), q: window.__mk.quality })));
await browser.close();
