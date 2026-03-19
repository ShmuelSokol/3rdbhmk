const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1400, height: 900 } });
  const page = await context.newPage();

  page.on('console', msg => {
    if (msg.type() === 'error') console.log('BROWSER ERROR:', msg.text());
  });

  console.log('Navigating to compare page...');
  try {
    await page.goto('http://localhost:3000/book/5qje5lvpqtuu1th3cnnbd73gz/compare', {
      waitUntil: 'networkidle',
      timeout: 60000
    });
  } catch(e) {
    console.log('Navigation note:', e.message);
  }

  const title = await page.title();
  console.log('Page title:', title);

  // Wait for canvas processing and images
  console.log('Waiting 15s for canvas processing and images to load...');
  await page.waitForTimeout(15000);

  // Take full page screenshot
  await page.screenshot({ path: '/tmp/compare-full.png', fullPage: true });
  console.log('Full page screenshot saved');

  const pageHeight = await page.evaluate(() => document.body.scrollHeight);
  const viewportHeight = 900;
  console.log(`Page total height: ${pageHeight}px`);

  // Get all page containers
  const pageContainers = await page.evaluate(() => {
    const scrollContainers = document.querySelectorAll('.scroll-mt-20');
    return Array.from(scrollContainers).map((el, i) => {
      const rect = el.getBoundingClientRect();
      const scrollY = window.pageYOffset;
      const label = el.querySelector('span')?.textContent || `section-${i}`;
      return {
        index: i,
        top: Math.round(rect.top + scrollY),
        height: Math.round(rect.height),
        label
      };
    });
  });

  console.log('Found page containers:', JSON.stringify(pageContainers, null, 2));

  // Take a viewport-sized screenshot of each page
  for (const container of pageContainers) {
    const scrollY = Math.max(0, container.top - 80);
    await page.evaluate((y) => window.scrollTo(0, y), scrollY);
    await page.waitForTimeout(3000); // Wait for lazy-loaded images and canvas processing
    const filename = `/tmp/compare-${container.label.replace(/\s+/g, '').toLowerCase()}.png`;
    await page.screenshot({ path: filename });
    console.log(`Screenshot saved: ${filename} (scrollY=${scrollY})`);
  }

  // Additional: screenshot each page section with full height
  for (const container of pageContainers) {
    const scrollY = Math.max(0, container.top - 80);
    await page.evaluate((y) => window.scrollTo(0, y), scrollY);
    await page.waitForTimeout(2000);
    // Clip to just show the page content area
    const clip = {
      x: 0,
      y: 0,
      width: 1400,
      height: Math.min(900, container.height + 100)
    };
    const filename = `/tmp/compare-clip-${container.label.replace(/\s+/g, '').toLowerCase()}.png`;
    await page.screenshot({ path: filename, clip });
    console.log(`Clipped screenshot: ${filename}`);
  }

  // Take a series of scroll positions to cover all pages
  const steps = Math.ceil(pageHeight / viewportHeight);
  for (let i = 0; i < steps; i++) {
    const y = i * (viewportHeight - 100);
    await page.evaluate((scrollY) => window.scrollTo(0, scrollY), y);
    await page.waitForTimeout(2500);
    await page.screenshot({ path: `/tmp/compare-step${i}.png` });
    console.log(`Step ${i} screenshot at y=${y} saved`);
  }

  console.log('All screenshots complete!');
  await browser.close();
})();
