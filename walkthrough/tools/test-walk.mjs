// End-to-end check in a real (headless) browser:
//   1. the page loads without console errors and the welcome screen becomes usable;
//   2. a simulated visitor WALKS the whole pilgrim's way, stop to stop, with the same
//      collision and floor-following code a person uses, and reaches all 18 stops;
//   3. nobody can walk through the paroches, the Menorah or an outer wall;
//   4. "Take me there", the panels and the phone layout work.
// Run: npm run build && npm test          (needs the preview server: npm run serve)
import { createRequire } from 'node:module';
import { spawn } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const { chromium } = createRequire(import.meta.url)('playwright');
const here = path.dirname(fileURLToPath(import.meta.url));
const PORT = 4188;
const server = spawn(process.execPath, [path.join(here, 'serve.mjs'), String(PORT)], { stdio: 'ignore' });
await new Promise((r) => setTimeout(r, 700));

let failures = 0;
const check = (ok, name, detail = '') => {
  if (!ok) failures++;
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? `  (${detail})` : ''}`);
};

const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
try {
  // ------------------------------------------------------------ desktop
  const page = await browser.newPage({ viewport: { width: 740, height: 360 } });
  const errors = [];
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto(`http://localhost:${PORT}/?manual=1&fixed=1&q=low`);
  await page.waitForFunction(() => window.__mk && window.__mk.ready, null, { timeout: 180000 });
  check(await page.isVisible('#w-tour'), 'welcome screen offers the tour once loaded');
  await page.click('#w-tour');
  await page.waitForFunction(() => window.__mk.started && !window.__mk.traveling, null, { timeout: 30000 });
  await page.waitForTimeout(600);
  check(await page.isVisible('#tourcard'), 'tour card is shown after starting');
  check((await page.textContent('#t-count')).includes('1 of 18'), 'tour starts at stop 1 of 18');

  // Walk the route with the real movement code.
  const legs = await page.evaluate(() => {
    const mk = window.__mk;
    const P = mk.player;
    const wrap = (a) => ((a + Math.PI) % (2 * Math.PI) + 2 * Math.PI) % (2 * Math.PI) - Math.PI;
    function walkTo(target, limitSeconds) {
      const dt = 1 / 30;
      let t = 0, lastD = Infinity, stall = 0;
      while (t < limitSeconds) {
        const dx = target[0] - P.position.x, dz = target[2] - P.position.z;
        const d = Math.hypot(dx, dz);
        if (d < 0.7) return { ok: true, t };
        const want = Math.atan2(-dx, -dz);
        P.update(dt, { moveX: 0, moveZ: 1, lookX: wrap(want - P.yaw), lookY: -P.pitch, run: true, jump: false, up: false, down: false });
        t += dt;
        if (d > lastD - 0.002) { if (++stall > 90) return { ok: false, t, at: P.position.toArray().map((v) => +v.toFixed(2)), left: +d.toFixed(2) }; } else stall = 0;
        lastD = d;
      }
      return { ok: false, t, at: P.position.toArray().map((v) => +v.toFixed(2)), timeout: true };
    }
    const out = [];
    const first = mk.stops[0];
    P.setPose({ x: first.stand[0], y: 0, z: first.stand[2] }, Math.PI / 2, 0);
    for (let i = 1; i < mk.stops.length; i++) {
      const s = mk.stops[i];
      const points = [...s.approach, s.stand];
      let res = { ok: true, t: 0 };
      for (const pt of points) {
        const r = walkTo(pt, 120);
        res = { ...r, t: res.t + r.t };
        if (!r.ok) break;
      }
      const floorErr = Math.abs(P.position.y - mk.world.groundBelow(s.stand[0], s.stand[1] + 2.5, s.stand[2]));
      out.push({ key: s.key, ...res, floorErr: +floorErr.toFixed(2), y: +P.position.y.toFixed(2) });
      if (!res.ok) P.setPose({ x: s.stand[0], y: s.stand[1] + 0.2, z: s.stand[2] }, P.yaw, 0);
    }
    return out;
  });
  for (const leg of legs) {
    // 0.6 m: a stop that stands on a stair is reached within 0.7 m, which can be two steps off.
    check(leg.ok && leg.floorErr < 0.6, `walk to ${leg.key}`, leg.ok ? `${leg.t.toFixed(0)} s, floor ${leg.y} m` : `stuck at ${leg.at} ${leg.left ?? ''} m short`);
  }

  // Things a visitor must not be able to walk through.
  const blocked = await page.evaluate(() => {
    const P = window.__mk.player;
    const push = (from, yaw, seconds) => {
      P.setPose({ x: from[0], y: from[1], z: from[2] }, yaw, 0);
      for (let i = 0; i < seconds * 30; i++) P.update(1 / 30, { moveX: 0, moveZ: 1, lookX: 0, lookY: 0, run: true, jump: false, up: false, down: false });
      return P.position.toArray();
    };
    return {
      paroches: push([-52, 9.25, 0], Math.PI / 2, 4),       // west, at the curtain
      menorah: push([-50, 9.25, 3.15], Math.PI / 2, 3),     // west, at the Menorah
      outerWall: push([70, 3, 40], -Math.PI / 2, 4),        // east, at the outer wall from inside
      heikhalWall: push([-45, 9.25, 0], 0, 4),              // north, at the Heikhal wall
    };
  });
  check(blocked.paroches[0] > -55.6, 'the paroches cannot be walked through', `x ${blocked.paroches[0].toFixed(2)}`);
  check(blocked.menorah[0] > -53.0, 'the Menorah cannot be walked through', `x ${blocked.menorah[0].toFixed(2)}`);
  check(blocked.outerWall[0] < 79, 'the outer wall cannot be walked through', `x ${blocked.outerWall[0].toFixed(2)}`);
  check(blocked.heikhalWall[2] > -5.0, 'the Heikhal wall cannot be walked through', `z ${blocked.heikhalWall[2].toFixed(2)}`);

  // Dove flight cannot enter the Kodesh HaKodashim either.
  const dove = await page.evaluate(() => {
    const P = window.__mk.player;
    P.setMode('fly');
    P.setPose({ x: -52, y: 9.6, z: 0 }, Math.PI / 2, 0);
    for (let i = 0; i < 150; i++) P.update(1 / 30, { moveX: 0, moveZ: 1, lookX: 0, lookY: 0, run: true, jump: false, up: false, down: false });
    const x = P.position.x;
    P.setMode('walk');
    return x;
  });
  check(dove > -55.6, 'dove flight is stopped by the paroches', `x ${dove.toFixed(2)}`);

  // "Take me there" for every stop lands on that stop.
  for (const i of [0, 4, 9, 13, 17]) {
    await page.evaluate((k) => { window.__mk.selectStop(k); window.__mk.goStop(k); }, i);
    for (let k = 0; k < 600 && await page.evaluate(() => window.__mk.traveling); k++) {
      await page.evaluate(() => window.__mk.step(0.2, 2));
      await page.waitForTimeout(25);
    }
    await page.waitForTimeout(500);
    const d = await page.evaluate((k) => { const mk = window.__mk; const s = mk.stops[k]; return Math.hypot(mk.player.position.x - s.stand[0], mk.player.position.z - s.stand[2]); }, i);
    check(d < 0.5, `"Take me there" reaches stop ${i + 1}`, `${d.toFixed(2)} m off`);
  }
  check((await page.evaluate(() => window.__mk.seen.length)) >= 5, 'visited stops are remembered');

  // Panels open and close.
  await page.evaluate(() => window.__mk.step(0.1, 1));
  for (const [button, title] of [['#b-map', 'Plan of the Mikdash'], ['#b-stops', 'The pilgrim'], ['#b-codex', 'Sources and notes'], ['#b-settings', 'Settings'], ['#b-help', 'How to move']]) {
    await page.click(button);
    const t = await page.textContent('#sheet-title');
    check(t.includes(title) && await page.isVisible('#sheet'), `${title} panel opens`);
    await page.keyboard.press('Escape');
    check(!(await page.isVisible('#sheet')), `${title} panel closes with Escape`);
  }
  await page.click('#t-read');
  check((await page.textContent('#sheet-body')).includes('What happens here'), 'stop details show the authored text');
  await page.click('#sheet-close');
  check(errors.length === 0, 'no console errors on desktop', errors.slice(0, 3).join(' | '));
  await page.close();

  // ------------------------------------------------------------ phone
  const phone = await browser.newPage({ viewport: { width: 390, height: 780 }, hasTouch: true, isMobile: true, deviceScaleFactor: 1 });
  const perr = [];
  phone.on('console', (m) => { if (m.type() === 'error') perr.push(m.text()); });
  phone.on('pageerror', (e) => perr.push(e.message));
  await phone.goto(`http://localhost:${PORT}/?manual=1&fixed=1&q=low`);
  await phone.waitForFunction(() => window.__mk && window.__mk.ready, null, { timeout: 180000 });
  await phone.tap('#w-free');
  await phone.waitForFunction(() => window.__mk.started && !window.__mk.traveling, null, { timeout: 30000 });
  await phone.waitForTimeout(600);
  const overflow = await phone.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
  check(!overflow, 'phone layout has no sideways scroll');
  // a thumb on the left side walks the visitor forward
  const before = await phone.evaluate(() => window.__mk.player.position.x);
  const cdp = await phone.context().newCDPSession(phone);
  const touch = (type, x, y) => cdp.send('Input.dispatchTouchEvent', { type, touchPoints: type === 'touchEnd' ? [] : [{ x, y, id: 1 }] });
  await touch('touchStart', 90, 600);
  await touch('touchMove', 90, 570);
  await touch('touchMove', 90, 540);
  await phone.evaluate(() => window.__mk.step(1 / 30, 45));
  check(await phone.evaluate(() => document.getElementById('stick').classList.contains('on')), 'the joystick appears under the thumb');
  await touch('touchEnd', 90, 540);
  const after = await phone.evaluate(() => window.__mk.player.position.x);
  check(before - after > 1.5, 'sliding the left thumb walks forward', `${(before - after).toFixed(1)} m`);
  await phone.evaluate(() => window.__mk.step(1 / 30, 2));
  check(!(await phone.evaluate(() => document.getElementById('stick').classList.contains('on'))), 'the joystick disappears on release');
  const tools = await phone.$$eval('.tool', (els) => els.filter((e) => e.offsetParent).map((e) => { const r = e.getBoundingClientRect(); return Math.min(r.width, r.height); }));
  check(tools.every((s) => s >= 40), 'every toolbar button is at least 40 px for a thumb', tools.join(','));
  check(perr.length === 0, 'no console errors on phone', perr.slice(0, 3).join(' | '));
  await phone.close();
} finally {
  await browser.close();
  server.kill();
}
console.log(failures ? `\n${failures} check(s) failed` : '\nall checks passed');
process.exit(failures ? 1 : 0);
