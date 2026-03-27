import puppeteer from 'puppeteer';
import { readFileSync, writeFileSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));

// Parse CSV
const csv = readFileSync(resolve(__dirname, 'judaica-stores.csv'), 'utf-8');
const lines = csv.trim().split('\n');
const headers = lines[0].split(',');

function parseCSVLine(line) {
  const result = [];
  let current = '';
  let inQuotes = false;
  for (const char of line) {
    if (char === '"') { inQuotes = !inQuotes; }
    else if (char === ',' && !inQuotes) { result.push(current.trim()); current = ''; }
    else { current += char; }
  }
  result.push(current.trim());
  return result;
}

const stores = lines.slice(1).filter(l => l.trim()).map(line => {
  const vals = parseCSVLine(line);
  return {
    name: vals[0] || '',
    address: vals[1] || '',
    city: vals[2] || '',
    state: vals[3] || '',
    zip: vals[4] || '',
    phone: vals[5] || '',
    email: vals[6] || '',
    region: vals[7] || '',
    priority: parseInt(vals[8]) || 9
  };
});

// Group by region
const regionOrder = [
  'Brooklyn - Borough Park', 'Brooklyn - Flatbush', 'Brooklyn - Crown Heights', 'Brooklyn - Williamsburg',
  'Lakewood NJ', 'Monsey NY', 'Five Towns NY',
  'Manhattan NY', 'Queens NY', 'Bronx NY',
  'Teaneck NJ', 'Passaic NJ', 'Highland Park NJ', 'Long Branch NJ', 'Howell NJ',
  'Baltimore MD', 'Philadelphia PA', 'Boston MA', 'Washington DC',
  'South Florida', 'Pittsburgh PA', 'Cleveland OH', 'Detroit MI',
  'Chicago IL', 'Los Angeles CA', 'San Francisco CA',
  'Las Vegas NV', 'Denver CO', 'Phoenix AZ', 'Seattle WA',
  'Houston TX', 'Dallas TX', 'San Diego CA', 'Minneapolis MN', 'Milwaukee WI'
];

const regionGroups = {};
for (const store of stores) {
  if (!regionGroups[store.region]) regionGroups[store.region] = [];
  regionGroups[store.region].push(store);
}

// Region display names with tier labels
const tierLabels = {
  1: 'Tier 1 — Highest Density Jewish Communities',
  2: 'Tier 2 — Major Tri-State Communities',
  3: 'Tier 3 — Major US Jewish Communities',
  4: 'Tier 4 — Regional Jewish Communities',
  5: 'Tier 5 — Additional Communities'
};

let currentTier = 0;

function storeRow(s) {
  const fullAddr = `${s.address}, ${s.city}, ${s.state} ${s.zip}`.replace(/, ,/g, ',').replace(/,\s*$/,'');
  const emailCell = s.email ? `<a href="mailto:${s.email}">${s.email}</a>` : '—';
  return `<tr>
    <td class="store-name">${s.name}</td>
    <td>${fullAddr}</td>
    <td class="phone">${s.phone || '—'}</td>
    <td class="email">${emailCell}</td>
  </tr>`;
}

let tableHtml = '';
let storeCount = 0;

for (const region of regionOrder) {
  const group = regionGroups[region];
  if (!group || group.length === 0) continue;

  const tier = group[0].priority;
  if (tier !== currentTier) {
    currentTier = tier;
    tableHtml += `<tr class="tier-header"><td colspan="4">${tierLabels[tier] || `Tier ${tier}`}</td></tr>`;
  }

  tableHtml += `<tr class="region-header"><td colspan="4">${region} <span class="count">(${group.length} stores)</span></td></tr>`;

  for (const store of group) {
    tableHtml += storeRow(store);
    storeCount++;
  }
}

const html = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Judaica Stores — Master Distribution List</title>
<style>
  @page { size: letter landscape; margin: 0.6in 0.5in; }
  * { box-sizing: border-box; }
  body {
    font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
    font-size: 8.5pt;
    line-height: 1.35;
    color: #1a1a1a;
    margin: 0;
    padding: 0.6in 0.5in;
  }
  .cover {
    text-align: center;
    padding: 2.5in 1in 0;
    page-break-after: always;
  }
  .cover h1 {
    font-size: 28pt;
    color: #2c3e50;
    margin: 0 0 0.3em;
    letter-spacing: 1px;
  }
  .cover .hebrew { font-size: 32pt; direction: rtl; margin-bottom: 0.2em; color: #2c3e50; }
  .cover .subtitle { font-size: 14pt; color: #555; margin: 0.5em 0 1.5em; }
  .cover .meta { font-size: 11pt; color: #777; }
  .cover .meta p { margin: 0.3em 0; }
  .cover .line { width: 200px; height: 2px; background: #2c3e50; margin: 1.5em auto; }

  h2 { font-size: 11pt; color: #2c3e50; margin: 1em 0 0.3em; page-break-after: avoid; }

  table { width: 100%; border-collapse: collapse; font-size: 8.5pt; }
  th {
    background: #2c3e50;
    color: white;
    padding: 5px 8px;
    text-align: left;
    font-weight: 600;
    font-size: 8pt;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    position: sticky;
    top: 0;
  }
  td { padding: 4px 8px; border-bottom: 1px solid #e8e8e8; vertical-align: top; }
  tr:nth-child(even) td { background: #fafafa; }

  .tier-header td {
    background: #2c3e50 !important;
    color: white;
    font-weight: 700;
    font-size: 10pt;
    padding: 8px;
    text-transform: uppercase;
    letter-spacing: 1px;
    page-break-after: avoid;
  }
  .region-header td {
    background: #ecf0f1 !important;
    font-weight: 700;
    font-size: 9pt;
    color: #2c3e50;
    padding: 5px 8px;
    border-bottom: 2px solid #bdc3c7;
    page-break-after: avoid;
  }
  .region-header .count { font-weight: 400; color: #777; font-size: 8pt; }

  .store-name { font-weight: 600; white-space: nowrap; }
  .phone { white-space: nowrap; }
  .email { font-size: 7.5pt; }
  .email a { color: #2980b9; text-decoration: none; }

  .footer {
    margin-top: 2em;
    padding-top: 0.5em;
    border-top: 1px solid #ccc;
    font-size: 7.5pt;
    color: #999;
    text-align: center;
  }
</style>
</head>
<body>

<div class="cover">
  <div class="hebrew">לשכנו תדרשו</div>
  <h1>Lishchno Tidreshu</h1>
  <p class="subtitle">Judaica Store Distribution List<br>United States</p>
  <div class="line"></div>
  <div class="meta">
    <p><strong>${storeCount} Stores</strong> across <strong>${Object.keys(regionGroups).length} Regions</strong></p>
    <p>Organized by Jewish Community Population Density</p>
    <p style="margin-top: 1em; color: #999;">Prepared March 2026</p>
  </div>
</div>

<table>
  <thead>
    <tr>
      <th style="width: 22%">Store Name</th>
      <th style="width: 38%">Address</th>
      <th style="width: 15%">Phone</th>
      <th style="width: 25%">Email</th>
    </tr>
  </thead>
  <tbody>
    ${tableHtml}
  </tbody>
</table>

<div class="footer">
  Lishchno Tidreshu — Judaica Store Distribution List &bull; ${storeCount} stores &bull; Prepared March 2026
  <br>Note: Verify store status before shipping. Some stores may have changed hours, relocated, or closed.
</div>

</body>
</html>`;

// Write HTML
writeFileSync(resolve(__dirname, 'store-list.html'), html);
console.log(`Generated store-list.html with ${storeCount} stores across ${Object.keys(regionGroups).length} regions`);

// Generate PDF
const browser = await puppeteer.launch({ headless: true });
const page = await browser.newPage();
await page.setContent(html, { waitUntil: 'networkidle0' });
await page.pdf({
  path: resolve(__dirname, 'judaica-store-list.pdf'),
  format: 'Letter',
  landscape: true,
  printBackground: true,
  margin: { top: '0.4in', right: '0.4in', bottom: '0.4in', left: '0.4in' }
});
await browser.close();
console.log('Generated: judaica-store-list.pdf');
