const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1400, height: 900 } });
  const page = await context.newPage();

  page.on('console', msg => {
    if (msg.type() !== 'warning') console.log('BROWSER:', msg.type(), msg.text());
  });
  page.on('pageerror', err => console.log('PAGE ERROR:', err.message));

  console.log('First - hitting homepage to ensure server is warm...');
  try {
    await page.goto('http://localhost:3000/', { waitUntil: 'networkidle', timeout: 30000 });
  } catch(e) {
    console.log('Homepage load:', e.message);
  }
  console.log('Homepage loaded, title:', await page.title());
  await page.screenshot({ path: '/tmp/homepage.png' });

  // Now navigate to compare page
  console.log('\nNavigating to compare page...');
  try {
    const response = await page.goto('http://localhost:3000/book/5qje5lvpqtuu1th3cnnbd73gz/compare', {
      waitUntil: 'networkidle',
      timeout: 90000
    });
    console.log('Response status:', response?.status());
    console.log('Response URL:', response?.url());
  } catch(e) {
    console.log('Navigation error:', e.message);
    // Take screenshot anyway
  }

  const title = await page.title();
  console.log('Page title:', title);
  await page.screenshot({ path: '/tmp/compare-v2-0s.png', fullPage: true });
  console.log('Screenshot at 0s saved');

  if (title.includes('404')) {
    console.log('\nStill 404. Waiting 30s more for lazy compilation...');
    await page.waitForTimeout(30000);

    // Try reloading
    console.log('Reloading...');
    try {
      await page.reload({ waitUntil: 'networkidle', timeout: 60000 });
    } catch(e) {
      console.log('Reload error:', e.message);
    }
    await page.screenshot({ path: '/tmp/compare-v2-after-reload.png', fullPage: true });
    console.log('After reload screenshot saved');
    console.log('Page title after reload:', await page.title());
  }

  await browser.close();
  console.log('Done.');
})();
