import puppeteer from 'puppeteer';
import { readFileSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));

async function generatePDF(htmlFile, outputFile, options = {}) {
  const browser = await puppeteer.launch({ headless: true });
  const page = await browser.newPage();

  const htmlPath = resolve(__dirname, htmlFile);
  const html = readFileSync(htmlPath, 'utf-8');
  await page.setContent(html, { waitUntil: 'networkidle0' });

  await page.pdf({
    path: resolve(__dirname, outputFile),
    format: 'Letter',
    printBackground: true,
    margin: options.margin || { top: '0', right: '0', bottom: '0', left: '0' },
    ...options.pdfOptions
  });

  await browser.close();
  console.log(`Generated: ${outputFile}`);
}

const args = process.argv.slice(2);
const htmlFile = args[0] || 'outreach-letter.html';
const outputFile = args[1] || 'outreach-letter.pdf';

generatePDF(htmlFile, outputFile).catch(console.error);
