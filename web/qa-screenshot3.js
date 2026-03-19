const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1400, height: 900 } });
  const page = await context.newPage();

  // Intercept console messages
  page.on('console', msg => console.log('BROWSER:', msg.type(), msg.text()));
  page.on('pageerror', err => console.log('PAGE ERROR:', err.message));

  console.log('Navigating to compare page...');
  try {
    const response = await page.goto('http://localhost:3000/book/5qje5lvpqtuu1th3cnnbd73gz/compare', {
      waitUntil: 'domcontentloaded',
      timeout: 90000
    });
    console.log('Response status:', response?.status());
  } catch(e) {
    console.log('Navigation error:', e.message);
  }

  const title = await page.title();
  console.log('Page title:', title);

  // Take immediate screenshot
  await page.screenshot({ path: '/tmp/compare-immediate.png' });
  console.log('Immediate screenshot saved');

  // Wait more
  await page.waitForTimeout(20000);
  await page.screenshot({ path: '/tmp/compare-after20s.png', fullPage: true });
  console.log('After 20s screenshot saved');

  // Check for loading indicators
  const hasSpinner = await page.$('.animate-spin') !== null;
  const hasCanvas = await page.$('canvas') !== null;
  const bodyText = await page.evaluate(() => document.body.innerText.substring(0, 500));
  console.log('Has spinner:', hasSpinner);
  console.log('Has canvas:', hasCanvas);
  console.log('Body text preview:', bodyText);

  // Wait for images to fully load
  await page.waitForTimeout(5000);
  await page.screenshot({ path: '/tmp/compare-final.png', fullPage: true });
  console.log('Final screenshot saved');

  await browser.close();
})();
