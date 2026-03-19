const puppeteer = require('puppeteer');
const path = require('path');
const fs = require('fs');

const TEST_PAGES = [
  { pageId: 'cmmkpf55h00bqggb6gxy0tzaw', pageNum: 4, bookId: '5qje5lvpqtuu1th3cnnbd73gz' },
  { pageId: 'cmmkpf55h00bwggb6mhneh9tz', pageNum: 10, bookId: '5qje5lvpqtuu1th3cnnbd73gz' },
  { pageId: 'cmmkpf55h00byggb68runpbmp', pageNum: 12, bookId: '5qje5lvpqtuu1th3cnnbd73gz' },
  { pageId: 'cmmno2m5c000li9xoiyjxf7p0', pageNum: 22, bookId: 'jcqje5aut5wve5w5b8hv6fcq8' },
  { pageId: 'cmmno2m5c000wi9xoojv2br4y', pageNum: 33, bookId: 'jcqje5aut5wve5w5b8hv6fcq8' },
];

const BASE_URL = process.env.BASE_URL || 'http://localhost:3001';
const OUT_DIR = path.join(__dirname, 'screenshots');

// Create a minimal HTML page that renders one page's overlay
function makeOverlayHTML(pageId, baseUrl) {
  return `<!DOCTYPE html>
<html><head><style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: #f0f0f0; display: flex; justify-content: center; }
  .page-container { position: relative; width: 828px; }
  .page-container img { width: 100%; display: block; }
  .overlay { position: absolute; top: 0; left: 0; width: 100%; height: 100%; }
  .text-block {
    position: absolute;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
    padding: 2px;
    font-family: Arial, sans-serif;
    color: #000;
    line-height: 1.2;
  }
  .text-block.centered { text-align: center; justify-content: center; }
  .text-block.table-region { display: flex; flex-direction: row; }
  .table-col { flex: 1; padding: 0 2px; overflow: hidden; border-right: 1px solid rgba(0,0,0,0.1); }
  .table-col:last-child { border-right: none; }
</style></head>
<body>
<div class="page-container" id="container">
  <img id="erased-img" src="${baseUrl}/api/pages/${pageId}/image-erased" />
  <div class="overlay" id="overlay"></div>
</div>
<script>
async function render() {
  const img = document.getElementById('erased-img');
  await new Promise(r => { if (img.complete) r(); else img.onload = r; });

  const res = await fetch('${baseUrl}/api/pages/${pageId}/text-blocks');
  const data = await res.json();
  const overlay = document.getElementById('overlay');

  // Get translation text
  const bookRes = await fetch('${baseUrl}/api/books/${pageId.includes('cmmno') ? 'jcqje5aut5wve5w5b8hv6fcq8' : '5qje5lvpqtuu1th3cnnbd73gz'}/compare');
  let translationText = '';
  try {
    const bookData = await bookRes.json();
    const page = bookData.pages?.find(p => p.id === '${pageId}');
    if (page?.translation?.englishOutput) {
      translationText = page.translation.englishOutput;
    }
  } catch(e) { console.log('No translation data:', e); }

  // Simple text distribution
  const paragraphs = translationText.split(/\\n\\s*\\n/).filter(Boolean);
  const bodyBlocks = data.blocks.filter(b => !b.isTableRegion && !b.centered);
  const centeredBlocks = data.blocks.filter(b => b.centered);
  const tableBlocks = data.blocks.filter(b => b.isTableRegion);

  let paraIdx = 0;

  for (const block of data.blocks) {
    const div = document.createElement('div');
    div.className = 'text-block' + (block.centered ? ' centered' : '') + (block.isTableRegion ? ' table-region' : '');
    div.style.left = block.x + '%';
    div.style.top = block.y + '%';
    div.style.width = block.width + '%';
    div.style.height = block.height + '%';

    // Calculate font size based on avgLineHeightPct
    const containerH = img.naturalHeight || 2340;
    const lineHeightPx = (block.avgLineHeightPct / 100) * containerH;
    const fontSize = Math.max(8, Math.min(24, lineHeightPx * 0.65));
    div.style.fontSize = fontSize + 'px';

    if (block.isTableRegion && block.columnDividers?.length > 0) {
      // Table rendering
      const dividers = block.columnDividers;
      const edges = [block.x, ...dividers, block.x + block.width];
      for (let i = 0; i < edges.length - 1; i++) {
        const col = document.createElement('div');
        col.className = 'table-col';
        col.style.flex = ((edges[i+1] - edges[i]) / block.width).toFixed(3);
        if (paraIdx < paragraphs.length) {
          col.textContent = paragraphs[paraIdx]?.replace(/\\*\\*/g, '').substring(0, 200) || '';
        }
        div.appendChild(col);
      }
      paraIdx++;
    } else if (block.centered) {
      // Centered header
      if (paraIdx < paragraphs.length) {
        const text = paragraphs[paraIdx]?.replace(/\\*\\*/g, '') || '';
        if (text.length < 80) {
          div.textContent = text;
          paraIdx++;
        }
      }
    } else {
      // Body text
      const charRatio = block.hebrewCharCount / Math.max(1, bodyBlocks.reduce((s,b) => s + b.hebrewCharCount, 0));
      const numParas = Math.max(1, Math.round(paragraphs.length * charRatio));
      const assigned = paragraphs.slice(paraIdx, paraIdx + numParas);
      div.textContent = assigned.map(p => p.replace(/\\*\\*/g, '')).join(' ');
      paraIdx += numParas;
    }

    overlay.appendChild(div);
  }

  document.title = 'READY';
}
render().catch(console.error);
</script>
</body></html>`;
}

async function capturePages(suffix = '') {
  if (!fs.existsSync(OUT_DIR)) fs.mkdirSync(OUT_DIR, { recursive: true });

  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });

  for (const tp of TEST_PAGES) {
    console.log(`Capturing page ${tp.pageNum}...`);

    const page = await browser.newPage();
    await page.setViewport({ width: 900, height: 1300 });

    // Create inline HTML
    const html = makeOverlayHTML(tp.pageId, BASE_URL);

    // Navigate using data URL doesn't work for fetching, so save temp file and serve
    const tmpFile = path.join(OUT_DIR, `_tmp_${tp.pageNum}.html`);
    fs.writeFileSync(tmpFile, html);

    // We need to serve this through the same origin for CORS, so use a different approach:
    // Just navigate to the compare page for a single page
    // Actually, let's use the erased image directly and overlay text-blocks

    // Simpler: just capture the erased image and annotate programmatically
    // For now, download erased image + text-blocks

    const erasedUrl = `${BASE_URL}/api/pages/${tp.pageId}/image-erased`;
    const tbUrl = `${BASE_URL}/api/pages/${tp.pageId}/text-blocks`;

    // Download erased image
    const erasedPath = path.join(OUT_DIR, `erased-${tp.pageNum}${suffix}.png`);
    const tbPath = path.join(OUT_DIR, `textblocks-${tp.pageNum}${suffix}.json`);

    // Use page to download (avoids CORS)
    await page.goto(erasedUrl, { waitUntil: 'networkidle2', timeout: 60000 }).catch(() => {});

    // Get the image
    const imageBuffer = await page.evaluate(async (url) => {
      try {
        const res = await fetch(url);
        const blob = await res.blob();
        const reader = new FileReader();
        return new Promise(resolve => {
          reader.onloadend = () => resolve(reader.result);
          reader.readAsDataURL(blob);
        });
      } catch(e) { return null; }
    }, erasedUrl);

    if (imageBuffer) {
      const base64 = imageBuffer.replace(/^data:image\/\w+;base64,/, '');
      fs.writeFileSync(erasedPath, Buffer.from(base64, 'base64'));
      console.log(`  Saved erased image`);
    }

    // Get text-blocks
    const tbData = await page.evaluate(async (url) => {
      try {
        const res = await fetch(url);
        return await res.json();
      } catch(e) { return null; }
    }, tbUrl);

    if (tbData) {
      fs.writeFileSync(tbPath, JSON.stringify(tbData, null, 2));
      console.log(`  Saved text-blocks`);
    }

    // Clean up temp file
    try { fs.unlinkSync(tmpFile); } catch(e) {}

    await page.close();
  }

  await browser.close();
  console.log('Done!');
}

capturePages(process.argv[2] || '').catch(console.error);
