// Everything drawn in HTML over the 3D view: welcome screen, tour card, panels, map.
const $ = (id) => document.getElementById(id);

function h(tag, attrs, ...kids) {
  const el = document.createElement(tag);
  if (attrs) {
    for (const [k, v] of Object.entries(attrs)) {
      if (v == null || v === false) continue;
      if (k === 'class') el.className = v;
      else if (k === 'text') el.textContent = v;
      else if (k.startsWith('on')) el.addEventListener(k.slice(2), v);
      else el.setAttribute(k, v === true ? '' : v);
    }
  }
  for (const kid of kids.flat(Infinity)) {
    if (kid == null || kid === false) continue;
    el.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
  }
  return el;
}

const PART_NAMES = {
  ulam: 'Ulam', heichal: 'Heikhal', kodesh: 'Kodesh HaKodashim', altar: 'The altar', gates: 'Gates',
  outer: 'Outer court', inner: 'Inner court', cells: 'Side cells of the House', galleries: 'Galleries',
  kitchens: 'Cooking courts', priest: 'Chambers of the kohanim', vessel: 'Kiyor', mixed: 'The House', mount: 'The Mount',
};

const fmtAmot = (a) => (Number.isInteger(a) ? String(a) : String(+a.toFixed(2)));
const fmtMetres = (cm) => {
  const m = cm / 100;
  return m >= 100 ? `${Math.round(m)} m` : m >= 10 ? `${+m.toFixed(1)} m` : m >= 1 ? `${+m.toFixed(2)} m` : `${+cm.toFixed(1)} cm`;
};

export function createUI({ tour, codex, actions, settings, times }) {
  const stops = tour.stops;
  const codexById = new Map(codex.entries.map((e) => [e.id, e]));
  const sheet = $('sheet');
  const body = $('sheet-body');
  const scrim = $('scrim');
  let current = 0;
  let seen = new Set();
  let sheetKind = null;
  let backFn = null;
  let lastFocus = null;
  let mapTimer = 0;

  // ------------------------------------------------------------ welcome
  function setProgress(p, note) {
    const pct = Math.round(p * 100);
    $('loadbar').firstElementChild.style.width = `${pct}%`;
    $('loadbar').setAttribute('aria-valuenow', pct);
    if (note) $('loadnote').textContent = note;
  }
  function ready() {
    $('welcome').classList.remove('loading');
    $('loadbar').hidden = true;
    $('loadnote').hidden = true;
    $('w-actions').hidden = false;
    $('w-tour').focus({ preventScroll: true });
  }
  function fail(message) {
    $('loadbar').hidden = true;
    $('loadnote').textContent = message;
    $('loadnote').style.color = '#f0b9a0';
  }
  $('w-tour').addEventListener('click', () => actions.start('tour'));
  $('w-free').addEventListener('click', () => actions.start('free'));
  function enter(showTour) {
    $('welcome').classList.add('gone');
    $('hud').hidden = false;
    $('tourcard').classList.toggle('min', !showTour);
    $('view').focus({ preventScroll: true });
  }

  // ------------------------------------------------------------ sheet framework
  function openSheet(kind, title, content, { wide = false, back = null } = {}) {
    if (!sheetKind) lastFocus = document.activeElement;
    clearInterval(mapTimer);
    sheetKind = kind;
    backFn = back;
    $('sheet-title').textContent = title;
    $('sheet-back').hidden = !back;
    sheet.classList.toggle('wide', wide);
    body.replaceChildren(...[content].flat(Infinity).filter((k) => k != null && k !== false));
    body.scrollTop = 0;
    sheet.hidden = false;
    scrim.hidden = false;
    actions.panel(true);
    $('sheet-close').focus({ preventScroll: true });
  }
  function closeSheet() {
    if (!sheetKind) return false;
    clearInterval(mapTimer);
    sheetKind = null;
    sheet.hidden = true;
    scrim.hidden = true;
    actions.panel(false);
    (lastFocus && lastFocus.isConnected ? lastFocus : $('view')).focus({ preventScroll: true });
    return true;
  }
  $('sheet-close').addEventListener('click', closeSheet);
  $('sheet-back').addEventListener('click', () => backFn && backFn());
  scrim.addEventListener('click', closeSheet);
  sheet.addEventListener('keydown', (e) => {
    if (e.key !== 'Tab') return;
    const f = [...sheet.querySelectorAll('button, a[href], input, [tabindex]:not([tabindex="-1"])')].filter((el) => !el.hidden && el.offsetParent !== null);
    if (!f.length) return;
    const first = f[0], last = f[f.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  });

  const badge = (c) => h('span', { class: `badge ${c}`, title: tour.confidenceLabels[c] || '' }, c === 'certain' ? 'Sources agree' : c === 'disputed' ? 'Disputed' : 'Project’s choice');

  // ------------------------------------------------------------ tour card
  function setStop(i, seenSet) {
    current = i;
    if (seenSet) seen = seenSet;
    const s = stops[i];
    $('t-count').textContent = `Stop ${i + 1} of ${stops.length}`;
    $('t-name').textContent = s.name;
    $('t-he').textContent = s.he || '';
    $('t-sub').textContent = s.subtitle || '';
    $('t-prev').disabled = i === 0;
    $('t-next').disabled = i === stops.length - 1;
  }
  function setArrived(arrived) {
    $('t-go').textContent = arrived ? 'You are here' : 'Take me there';
    $('t-go').disabled = arrived;
    $('t-go').style.opacity = arrived ? 0.6 : 1;
  }
  $('t-prev').addEventListener('click', () => actions.selectStop(current - 1, true));
  $('t-next').addEventListener('click', () => actions.selectStop(current + 1, true));
  $('t-go').addEventListener('click', () => actions.goStop(current));
  $('t-read').addEventListener('click', () => openStop(current));

  // ------------------------------------------------------------ stop details
  function measureTable(list) {
    return h('table', { class: 'measures' }, h('tbody', null, list.map((m) =>
      h('tr', null,
        h('td', null, m.label, m.source ? h('small', null, m.source) : null),
        h('td', { class: 'num' },
          m.amot != null ? h('span', { class: 'amot' }, `${fmtAmot(m.amot)} amot`) : m.log != null ? h('span', { class: 'amot' }, `${m.log === 0.5 ? 'half a' : m.log} log`) : m.value || '',
          m.cm != null ? h('small', null, fmtMetres(m.cm)) : null)))));
  }
  function openStop(i, from) {
    const s = stops[i];
    const related = s.codex.map((id) => codexById.get(id)).filter(Boolean);
    const content = [
      s.he ? h('p', { class: 'stop-he', lang: 'he', dir: 'rtl' }, s.he) : null,
      h('p', { class: 'stop-sub' }, s.subtitle, ' ', badge(s.confidence)),
      h('h3', null, 'What happens here'),
      h('p', { class: 'big' }, s.what),
      s.measurements.length ? [h('h3', null, 'Measurements'), measureTable(s.measurements)] : null,
      h('h3', null, 'How it was built'),
      h('p', null, s.explanation),
      related.length ? [h('h3', null, 'Read further'), h('ul', { class: 'rows' }, related.map((e) =>
        h('li', null, h('button', { class: 'row', onclick: () => openCodexEntry(e.id, () => openStop(i, from)) },
          h('span', { class: 't' }, h('b', null, e.name)), h('span', { class: 'chev' }, '›')))))] : null,
      h('h3', null, 'Sources'),
      h('ul', { class: 'sources' }, s.sources.map((t) => h('li', null, t))),
      h('div', { class: 'stack' },
        h('button', { class: 'btn primary small', onclick: () => { closeSheet(); actions.goStop(i); } }, 'Take me there'),
        i < stops.length - 1 ? h('button', { class: 'btn small', onclick: () => { actions.selectStop(i + 1, false); openStop(i + 1, from); } }, 'Next stop ›') : null),
    ];
    openSheet('stop', `${i + 1}. ${s.name}`, content, { back: from === 'list' ? openStops : null });
  }

  function openStops() {
    const content = [
      h('p', null, tour.description),
      h('ul', { class: 'rows' }, stops.map((s, i) =>
        h('li', null, h('button', {
          class: `row${i === current ? ' current' : ''}${seen.has(i) ? ' seen' : ''}`,
          onclick: () => { actions.selectStop(i, false); openStop(i, 'list'); },
        },
          h('span', { class: 'n' }, seen.has(i) ? '✓' : i + 1),
          h('span', { class: 't' }, h('b', null, s.name), h('span', null, s.subtitle)),
          s.he ? h('span', { class: 'h', lang: 'he', dir: 'rtl' }, s.he) : null)))),
      h('h3', null, 'Good to know'),
      tour.limitations.slice(1).map((t) => h('p', null, t)),
    ];
    openSheet('stops', tour.name, content);
  }

  // ------------------------------------------------------------ codex
  function openCodex() {
    const list = h('div');
    const render = (q) => {
      const needle = q.trim().toLowerCase();
      const out = [];
      for (const cat of codex.categories) {
        const items = codex.entries.filter((e) => e.category === cat.id &&
          (!needle || e.name.toLowerCase().includes(needle) || e.summary.toLowerCase().includes(needle) || (e.he && e.he.includes(q.trim()))));
        if (!items.length) continue;
        out.push(h('h3', null, cat.name.en));
        out.push(h('ul', { class: 'rows' }, items.map((e) =>
          h('li', null, h('button', { class: 'row', onclick: () => openCodexEntry(e.id, openCodex) },
            h('span', { class: 't' }, h('b', null, e.name)),
            e.he ? h('span', { class: 'h', lang: 'he', dir: 'rtl' }, e.he) : null,
            h('span', { class: 'chev' }, '›'))))));
      }
      if (!out.length) out.push(h('p', null, 'Nothing matches that search.'));
      list.replaceChildren(...out);
    };
    const search = h('input', { class: 'search', type: 'search', placeholder: 'Search the notes…', 'aria-label': 'Search the notes', oninput: (e) => render(e.target.value) });
    render('');
    openSheet('codex', 'Sources and notes', [
      h('p', null, `${codex.entries.length} notes on what the sources say, where they disagree, and what this model chose.`),
      search, list,
    ]);
  }
  function openCodexEntry(id, back) {
    const e = codexById.get(id);
    if (!e) return;
    openSheet('codex-entry', e.name, [
      e.he ? h('p', { class: 'stop-he', lang: 'he', dir: 'rtl' }, e.he) : null,
      h('p', { class: 'stop-sub' }, badge(e.confidence)),
      h('p', { class: 'big' }, e.summary),
      e.measurements.length ? [h('h3', null, 'Measurements'), measureTable(e.measurements)] : null,
      e.dispute.length ? [h('h3', null, 'Who holds what'), h('table', { class: 'measures' }, h('tbody', null,
        e.dispute.map((d) => h('tr', null, h('td', null, d.who), h('td', { class: 'num', style: 'white-space:normal;max-width:60%' }, d.holds)))))] : null,
      e.sources.length ? [h('h3', null, 'Sources'), h('ul', { class: 'sources' }, e.sources.map((t) => h('li', null, t)))] : null,
    ], { back });
  }

  // ------------------------------------------------------------ plan
  const PLAN_EXTENT = 100;
  const toPlan = (x, z) => ({ left: `${((x + PLAN_EXTENT) / (2 * PLAN_EXTENT)) * 100}%`, top: `${((z + PLAN_EXTENT) / (2 * PLAN_EXTENT)) * 100}%` });
  function openMap() {
    const you = h('div', { class: 'you' });
    const wrap = h('div', { class: 'plan-wrap' },
      h('img', { src: 'assets/plan.png', alt: 'Plan of the Beis HaMikdash seen from above, north at the top', draggable: 'false' }),
      h('span', { class: 'plan-north' }, 'N ↑'));
    const outside = [];
    stops.forEach((s, i) => {
      const [x, , z] = s.stand;
      const cls = `pin${seen.has(i) ? ' seen' : ''}${i === current ? ' current' : ''}`;
      const go = () => { closeSheet(); actions.selectStop(i, false); actions.goStop(i); };
      if (Math.abs(x) > PLAN_EXTENT - 3 || Math.abs(z) > PLAN_EXTENT - 3) {
        outside.push(h('button', { class: 'btn small', onclick: go }, `${i + 1}. ${s.name}`));
        return;
      }
      const pin = h('button', { class: cls, 'aria-label': `Stop ${i + 1}: ${s.name}`, title: s.name, onclick: go }, i + 1);
      Object.assign(pin.style, toPlan(x, z));
      wrap.append(pin);
    });
    wrap.append(you);
    const place = () => {
      const p = actions.playerPose();
      const cx = Math.max(-PLAN_EXTENT + 2, Math.min(PLAN_EXTENT - 2, p.x));
      const cz = Math.max(-PLAN_EXTENT + 2, Math.min(PLAN_EXTENT - 2, p.z));
      Object.assign(you.style, toPlan(cx, cz));
      // yaw 0 faces north (up the page); positive yaw turns toward the west
      you.style.transform = `rotate(${-p.yaw}rad)`;
    };
    place();
    openSheet('map', 'Plan of the Mikdash', [
      h('p', null, 'Tap a numbered stop to go there. The red arrow is you.'),
      wrap,
      outside.length ? [h('h3', null, 'Stops outside the walls'), h('div', { class: 'plan-edge' }, outside)] : null,
    ], { wide: true });
    mapTimer = setInterval(place, 250);
  }

  // ------------------------------------------------------------ settings
  function seg(options, value, onPick) {
    const el = h('div', { class: 'seg', role: 'group' });
    const draw = (v) => el.replaceChildren(...options.map(([key, label]) =>
      h('button', { 'aria-pressed': String(key === v), onclick: () => { draw(key); onPick(key); } }, label)));
    draw(value);
    return el;
  }
  function openSettings() {
    const s = settings.get();
    openSheet('settings', 'Settings', [
      h('div', { class: 'field' }, h('span', { class: 'label' }, 'Time of day'),
        seg(Object.entries(times).map(([k, t]) => [k, t.label]), s.time, (v) => settings.set('time', v))),
      h('div', { class: 'field' }, h('span', { class: 'label' }, 'Picture quality'),
        seg([['auto', 'Auto'], ['low', 'Low'], ['medium', 'Medium'], ['high', 'High']], s.quality, (v) => settings.set('quality', v)),
        h('p', { class: 'note' }, 'Auto picks for this device and lowers the resolution if the picture stutters. Changing this reloads the page.')),
      h('div', { class: 'field' }, h('label', { for: 'set-sens' }, 'Look speed'),
        h('input', { id: 'set-sens', type: 'range', min: '0.4', max: '2.2', step: '0.1', value: String(s.sensitivity), oninput: (e) => settings.set('sensitivity', +e.target.value) })),
      h('div', { class: 'field' },
        h('label', { class: 'check' }, h('input', { type: 'checkbox', checked: s.invertY, onchange: (e) => settings.set('invertY', e.target.checked) }), 'Invert up and down'),
        h('label', { class: 'check' }, h('input', { type: 'checkbox', checked: s.reduceMotion, onchange: (e) => settings.set('reduceMotion', e.target.checked) }), 'Reduce motion (no head bob, no gliding between stops)'),
        h('label', { class: 'check' }, h('input', { type: 'checkbox', checked: s.sound, onchange: (e) => settings.set('sound', e.target.checked) }), 'Sound (wind, footsteps, the altar fire)'),
        h('label', { class: 'check' }, h('input', { type: 'checkbox', checked: s.showTour, onchange: (e) => settings.set('showTour', e.target.checked) }), 'Show the tour card')),
      h('div', { class: 'stack' },
        h('button', { class: 'btn small', onclick: () => { closeSheet(); actions.restart(); } }, 'Return to the east gate'),
        h('button', { class: 'btn small', onclick: () => { closeSheet(); actions.share(); } }, 'Copy a link to this spot')),
    ]);
  }

  // ------------------------------------------------------------ help
  function openHelp() {
    const k = (...keys) => keys.map((t) => h('kbd', null, t));
    openSheet('help', 'How to move', [
      h('h3', null, 'On a phone or tablet'),
      h('table', { class: 'keys' }, h('tbody', null,
        h('tr', null, h('td', null, 'Walk'), h('td', null, 'Press the left side of the screen and slide your thumb. Push all the way to hurry.')),
        h('tr', null, h('td', null, 'Look'), h('td', null, 'Drag anywhere else.')),
        h('tr', null, h('td', null, 'Name it'), h('td', null, 'Tap any part of the building to see what it is.')))),
      h('h3', null, 'With a keyboard and mouse'),
      h('table', { class: 'keys' }, h('tbody', null,
        h('tr', null, h('td', null, k('W', 'A', 'S', 'D')), h('td', null, 'Walk. Arrow keys also work.')),
        h('tr', null, h('td', null, 'Drag'), h('td', null, 'Look around. Double-click to capture the mouse, Esc to release it.')),
        h('tr', null, h('td', null, k('Shift')), h('td', null, 'Hurry')),
        h('tr', null, h('td', null, k('Space')), h('td', null, 'Jump, or rise when flying')),
        h('tr', null, h('td', null, k('F')), h('td', null, 'Fly as a dove, and land again')),
        h('tr', null, h('td', null, k('Q', 'E')), h('td', null, 'Descend and rise when flying')),
        h('tr', null, h('td', null, k('[', ']')), h('td', null, 'Previous and next tour stop')),
        h('tr', null, h('td', null, k('G')), h('td', null, 'Go to the selected stop')),
        h('tr', null, h('td', null, k('M'), ' ', k('T')), h('td', null, 'Plan, and the list of stops')))),
      h('h3', null, 'About this model'),
      h('p', null, 'The building is the measured reconstruction from this project: ', h('b', null, '2,633 parts'), ' placed from Yechezkel 40–48 with Rashi, Mishnah Middos, Rambam and the sefer Lishchno Tidreshu. One amah is drawn as 50 cm.'),
      h('p', null, 'Nothing here is a ruling. Where the sources disagree the notes say who holds what, and where nobody says, the notes say the project chose. The paroches is closed, and the model does not show what is behind it.'),
      h('p', null, 'This is the light version that runs in a browser. The full Windows walkthrough has the city, people and sound.'),
    ]);
  }

  // ------------------------------------------------------------ small pieces
  let toastTimer = 0;
  function toast(msg, ms = 2600) {
    const el = $('toast');
    el.textContent = msg;
    el.classList.add('on');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.classList.remove('on'), ms);
  }
  let hintTimer = 0;
  function hint(parts, ms = 9000) {
    const el = $('hint');
    el.replaceChildren(...parts.map((p) => (Array.isArray(p) ? h('kbd', null, p[0]) : p)));
    el.hidden = false;
    clearTimeout(hintTimer);
    hintTimer = setTimeout(() => { el.hidden = true; }, ms);
  }
  function hideHint() { clearTimeout(hintTimer); $('hint').hidden = true; }
  let tagTimer = 0;
  function tag(x, y, name, part) {
    const el = $('tag');
    el.replaceChildren(h('small', null, PART_NAMES[part] || part), name);
    el.style.left = `${Math.max(90, Math.min(window.innerWidth - 90, x))}px`;
    el.style.top = `${Math.max(70, y)}px`;
    el.hidden = true;
    void el.offsetWidth; // restart the pop animation
    el.hidden = false;
    clearTimeout(tagTimer);
    tagTimer = setTimeout(() => { el.hidden = true; }, 3200);
  }
  let placeKey = '';
  function setPlace(en, he) {
    if (en === placeKey) return;
    placeKey = en;
    $('place-en').textContent = en;
    $('place-he').textContent = he || '';
  }
  function setCompass(yaw) { $('compass-dial').style.transform = `rotate(${yaw}rad)`; }
  function setFly(on, touch) {
    $('b-fly').setAttribute('aria-pressed', String(on));
    $('fly-keys').hidden = !(on && touch);
  }
  function setTourVisible(v) { $('tourcard').classList.toggle('min', !v); }

  $('b-map').addEventListener('click', () => (sheetKind === 'map' ? closeSheet() : openMap()));
  $('b-stops').addEventListener('click', () => (sheetKind === 'stops' ? closeSheet() : openStops()));
  $('b-codex').addEventListener('click', openCodex);
  $('b-settings').addEventListener('click', openSettings);
  $('b-help').addEventListener('click', openHelp);
  $('b-fly').addEventListener('click', () => actions.toggleFly());

  return {
    setProgress, ready, fail, enter, setStop, setArrived, openStop, openStops, openMap, openCodex, openSettings, openHelp,
    closeSheet, toast, hint, hideHint, tag, setPlace, setCompass, setFly, setTourVisible,
    get panelOpen() { return !!sheetKind; },
    toggle(kind) {
      if (sheetKind === kind) return closeSheet();
      if (kind === 'map') openMap(); else if (kind === 'stops') openStops(); else if (kind === 'help') openHelp();
      return true;
    },
    upButton: $('b-up'), downButton: $('b-down'),
  };
}
