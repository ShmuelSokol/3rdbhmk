const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });

  console.log('Navigating to compare page (waitUntil: domcontentloaded)...');
  try {
    await page.goto('http://localhost:3000/book/5qje5lvpqtuu1th3cnnbd73gz/compare', {
      waitUntil: 'domcontentloaded',
      timeout: 60000
    });
  } catch(e) {
    console.log('Navigation warning:', e.message);
  }

  // Wait extra time for React hydration + canvas processing
  console.log('Waiting 15s for React hydration and canvas processing...');
  await page.waitForTimeout(15000);

  const title = await page.title();
  const url = page.url();
  console.log('Page title:', title);
  console.log('Page URL:', url);

  await page.screenshot({ path: '/tmp/compare-full.png', fullPage: true });
  console.log('Full page screenshot saved to /tmp/compare-full.png');

  // Get page height
  const pageHeight = await page.evaluate(() => document.body.scrollHeight);
  const pageWidth = await page.evaluate(() => document.body.scrollWidth);
  console.log(`Page dimensions: ${pageWidth}x${pageHeight}`);

  // Find the page containers
  const pageInfo = await page.evaluate(() => {
    const scrollContainers = document.querySelectorAll('.scroll-mt-20');
    return Array.from(scrollContainers).map((el, i) => {
      const rect = el.getBoundingClientRect();
      const scrollY = window.pageYOffset;
      return {
        index: i,
        top: rect.top + scrollY,
        height: rect.height,
        text: el.querySelector('span')?.textContent || ''
      };
    });
  });
  console.log('Found page containers:', JSON.stringify(pageInfo, null, 2));

  // Take screenshot of each page
  for (let i = 0; i < pageInfo.length; i++) {
    const info = pageInfo[i];
    console.log(`Scrolling to page ${i+1} at y=${info.top}...`);
    await page.evaluate((y) => window.scrollTo(0, Math.max(0, y - 70)), info.top);
    await page.waitForTimeout(2000);
    await page.screenshot({ path: `/tmp/compare-page${i+4}.png` });
    console.log(`Screenshot saved for page ${i+4}`);
  }

  // Take screenshots at different scroll positions as backup
  const positions = [0, 900, 1800, 2700, 3600, 4500, 5400, 6300, 7200];
  for (let i = 0; i < positions.length; i++) {
    await page.evaluate((y) => window.scrollTo(0, y), positions[i]);
    await page.waitForTimeout(1000);
    await page.screenshot({ path: `/tmp/compare-scroll${i}.png` });
  }

  console.log('All screenshots complete.');
  await browser.close();
})();
