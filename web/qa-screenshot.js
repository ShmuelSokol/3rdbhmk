const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });

  console.log('Navigating to compare page...');
  await page.goto('http://localhost:3000/book/5qje5lvpqtuu1th3cnnbd73gz/compare', { waitUntil: 'networkidle' });

  // Wait for images to load and canvas processing
  console.log('Waiting for canvas processing...');
  await page.waitForTimeout(10000);

  // Take full page screenshot
  await page.screenshot({ path: '/tmp/compare-full.png', fullPage: true });
  console.log('Full page screenshot saved.');

  // Get page height to estimate scroll positions
  const pageHeight = await page.evaluate(() => document.body.scrollHeight);
  console.log('Total page height:', pageHeight);

  // Take screenshots at various scroll positions to capture individual pages
  const scrollPositions = [
    { name: 'top', y: 0 },
    { name: 'page4', y: 0 },
    { name: 'page5', y: 1000 },
    { name: 'page6', y: 2000 },
    { name: 'page7', y: 3000 },
    { name: 'page8', y: 4000 },
    { name: 'page9', y: 5000 },
    { name: 'page10', y: 6000 },
    { name: 'page11', y: 7000 },
    { name: 'page12', y: 8000 },
  ];

  for (const pos of scrollPositions) {
    await page.evaluate((y) => window.scrollTo(0, y), pos.y);
    await page.waitForTimeout(2000);
    await page.screenshot({ path: `/tmp/compare-${pos.name}.png` });
    console.log(`Screenshot saved for ${pos.name} at y=${pos.y}`);
  }

  // Try to find page elements and scroll to them
  const pageElements = await page.$$('[data-page], .page-container, canvas, .compare-page');
  console.log(`Found ${pageElements.length} potential page elements`);

  // Get bounding boxes of all canvas elements
  const canvases = await page.$$('canvas');
  console.log(`Found ${canvases.length} canvas elements`);

  for (let i = 0; i < canvases.length; i++) {
    const canvas = canvases[i];
    const box = await canvas.boundingBox();
    if (box) {
      console.log(`Canvas ${i}: x=${box.x}, y=${box.y}, w=${box.width}, h=${box.height}`);
      await page.evaluate((y) => window.scrollTo(0, Math.max(0, y - 50)), box.y);
      await page.waitForTimeout(1500);
      await page.screenshot({ path: `/tmp/compare-canvas${i}.png` });
      console.log(`Canvas ${i} screenshot saved`);
    }
  }

  await browser.close();
  console.log('Done!');
})();
