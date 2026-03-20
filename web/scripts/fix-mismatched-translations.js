#!/usr/bin/env node
const { PrismaClient } = require('@prisma/client');
const fs = require('fs');
const path = require('path');

const envPath = path.join(__dirname, '..', '.env.local');
if (fs.existsSync(envPath)) {
  for (const line of fs.readFileSync(envPath, 'utf8').split('\n')) {
    if (line.trim() && !line.startsWith('#') && line.includes('=')) {
      const [key, ...vals] = line.split('=');
      process.env[key.trim()] = vals.join('=').trim();
    }
  }
}

const prisma = new PrismaClient();

async function fix() {
  const pages = [21, 36, 108, 110, 177, 197];

  for (const pg of pages) {
    const regions = await prisma.contentRegion.findMany({
      where: { page: { bookId: 'jcqje5aut5wve5w5b8hv6fcq8', pageNumber: pg } },
      select: { id: true, translatedText: true }
    });

    for (const r of regions) {
      let t = r.translatedText || '';
      const orig = t;

      // p21: Remove "ומשכן נקרא מקדש — "My head is filled with dew" -"
      if (pg === 21 && t.includes('\u05D5\u05DE\u05E9\u05DB\u05DF \u05E0\u05E7\u05E8\u05D0 \u05DE\u05E7\u05D3\u05E9')) {
        // Find and remove the Hebrew + separator + wrong English
        const idx = t.indexOf('\u05D5\u05DE\u05E9\u05DB\u05DF \u05E0\u05E7\u05E8\u05D0');
        if (idx >= 0) {
          // Find the end of the wrong pairing (after "dew" and the dash)
          const dewIdx = t.indexOf('My head is filled with dew', idx);
          if (dewIdx >= 0) {
            const endIdx = t.indexOf(' - ', dewIdx + 25);
            if (endIdx >= 0) {
              t = t.substring(0, idx) + t.substring(endIdx + 3);
            }
          }
        }
      }

      // p108: Same "My head is filled with dew" issue
      if (pg === 108 && t.includes('\u05D7\u05D5\u05E8\u05D1\u05DF \u05D4\u05D1\u05D9\u05EA')) {
        const idx = t.indexOf('\u05D7\u05D5\u05E8\u05D1\u05DF \u05D4\u05D1\u05D9\u05EA');
        if (idx >= 0) {
          const dewIdx = t.indexOf('My head is filled with dew', idx);
          if (dewIdx >= 0) {
            // Find next sentence start after the wrong quote
            const afterDew = t.substring(dewIdx);
            const nextSentence = afterDew.match(/[,."]\s*[A-Z]/);
            if (nextSentence) {
              const cutEnd = dewIdx + nextSentence.index + 2;
              t = t.substring(0, idx) + t.substring(cutEnd);
            }
          }
        }
      }

      // p110: Remove "רוחני בית א׳... — "And their cry went up to Hashem,""
      if (pg === 110 && t.includes('\u05E8\u05D5\u05D7\u05E0\u05D9 \u05D1\u05D9\u05EA')) {
        const idx = t.indexOf('\u05E8\u05D5\u05D7\u05E0\u05D9 \u05D1\u05D9\u05EA');
        if (idx >= 0) {
          const cryIdx = t.indexOf('And their cry went up', idx);
          if (cryIdx >= 0) {
            const afterCry = t.substring(cryIdx);
            const nextPart = afterCry.match(/[,"]\s*and afterwards/i);
            if (nextPart) {
              t = t.substring(0, idx) + t.substring(cryIdx + nextPart.index + 2);
            } else {
              // Just remove the Hebrew block
              const sepIdx = t.indexOf('\u2014', idx) || t.indexOf(' - ', idx);
              if (sepIdx > idx) {
                t = t.substring(0, idx) + t.substring(sepIdx + 2);
              }
            }
          }
        }
      }

      // p36: Remove Hebrew gate text paired with wrong English
      if (pg === 36 && t.includes('\u05D4\u05E9\u05E2\u05E8 \u05E9\u05DC \u05D4\u05D7\u05E6\u05E8')) {
        const idx = t.indexOf('\u05D4\u05E9\u05E2\u05E8 \u05E9\u05DC \u05D4\u05D7\u05E6\u05E8');
        if (idx >= 0) {
          // Find the separator (- ) after the Hebrew
          const rest = t.substring(idx);
          const sepMatch = rest.match(/[\u0590-\u05FF\s\u05F3\u05F4\d\[\]\(\)'".,:;]+\s*-\s*/);
          if (sepMatch) {
            t = t.substring(0, idx) + t.substring(idx + sepMatch.index + sepMatch[0].length);
          }
        }
      }

      // p177: Remove Hebrew ulam measurement paired with wrong English
      if (pg === 177 && t.includes('\u05D0\u05D5\u05E8\u05DA \u05D4\u05D0\u05D5\u05DC\u05DD')) {
        const idx = t.indexOf('\u05D0\u05D5\u05E8\u05DA \u05D4\u05D0\u05D5\u05DC\u05DD');
        if (idx >= 0) {
          const rest = t.substring(idx);
          const sepMatch = rest.match(/[\u0590-\u05FF\s\u05F3\u05F4\d\[\]\(\)'".,:;\u05E7]+\s*[,\-]\s*/);
          if (sepMatch) {
            t = t.substring(0, idx) + t.substring(idx + sepMatch.index + sepMatch[0].length);
          }
        }
      }

      // p197: Remove Hebrew house measurement paired with wrong English
      if (pg === 197 && t.includes('\u05E9\u05D6\u05D4 \u05DB\u05E9\u05DC\u05D9\u05E9 \u05D4\u05D1\u05D9\u05EA')) {
        const idx = t.indexOf('\u05E9\u05D6\u05D4 \u05DB\u05E9\u05DC\u05D9\u05E9 \u05D4\u05D1\u05D9\u05EA');
        if (idx >= 0) {
          const rest = t.substring(idx);
          const sepMatch = rest.match(/[\u0590-\u05FF\s\u05F3\u05F4\d\[\]\(\)'".,:;]+\s*-\s*/);
          if (sepMatch) {
            t = t.substring(0, idx) + t.substring(idx + sepMatch.index + sepMatch[0].length);
          }
        }
      }

      if (t !== orig) {
        await prisma.contentRegion.update({ where: { id: r.id }, data: { translatedText: t } });
        console.log('Fixed p' + pg + ':');
        const changeStart = Math.max(0, orig.indexOf(orig.substring(0, 20)));
        console.log('  Removed mismatched Hebrew-English pairing');
      }
    }
  }

  // Verify
  console.log('\nVerifying...');
  const check = await prisma.contentRegion.findMany({
    where: { page: { bookId: 'jcqje5aut5wve5w5b8hv6fcq8', pageNumber: { in: pages } } },
    select: { translatedText: true, page: { select: { pageNumber: true } } }
  });
  for (const r of check) {
    if ((r.translatedText || '').includes('My head is filled with dew')) {
      console.log('  WARNING: p' + r.page.pageNumber + ' still has "My head is filled with dew"');
    }
    if ((r.translatedText || '').includes('their cry went up')) {
      console.log('  WARNING: p' + r.page.pageNumber + ' still has "their cry went up"');
    }
  }

  await prisma.$disconnect();
}

fix().catch(console.error);
