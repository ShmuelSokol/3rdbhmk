#!/usr/bin/env node
const { PrismaClient } = require('@prisma/client');
const fs = require('fs');
const path = require('path');

// Load env
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
const BOOK_ID = 'jcqje5aut5wve5w5b8hv6fcq8';

async function proofread() {
  const regions = await prisma.contentRegion.findMany({
    where: { page: { bookId: BOOK_ID } },
    select: {
      id: true, translatedText: true, hebrewText: true,
      regionType: true, page: { select: { pageNumber: true } }
    },
    orderBy: [{ page: { pageNumber: 'asc' } }, { regionIndex: 'asc' }]
  });

  const issues = [];

  for (const r of regions) {
    const t = (r.translatedText || '').trim();
    if (!t || t.length < 5) continue;
    const pg = r.page.pageNumber;
    const id = r.id;
    const rtype = r.regionType;

    // 1. Standalone numbers (page number leaks)
    if (/^\d{1,3}$/.test(t)) {
      issues.push({ pg, id, itype: 'content', severity: 'high',
        current: t, suggested: '[remove]', reason: 'Standalone number — likely leaked page number' });
    }

    // 2. Meta-text artifacts
    if (/\[THIS IS (TABLE|DIAGRAM|CHART|IMAGE)/i.test(t)) {
      const m = t.match(/\[THIS IS \w+[^\]]*\]/i);
      issues.push({ pg, id, itype: 'content', severity: 'high',
        current: (m?.[0] || '').substring(0, 80), suggested: '[remove]', reason: 'Meta-text artifact' });
    }

    // 3. Stray single Hebrew char between English words
    const strayHeb = t.match(/[a-zA-Z]\s+[\u0590-\u05FF]\s+[a-zA-Z]/g);
    if (strayHeb) {
      for (const match of strayHeb) {
        issues.push({ pg, id, itype: 'hebrew_artifact', severity: 'high',
          current: match, suggested: match.replace(/[\u0590-\u05FF]/g, '').replace(/\s+/g, ' '),
          reason: 'Orphan Hebrew char between English words' });
      }
    }

    // 4. Text starts with stray punctuation
    if (/^[,;:!\?]\s/.test(t)) {
      issues.push({ pg, id, itype: 'punctuation', severity: 'medium',
        current: t.substring(0, 60), suggested: t.substring(1).trim().substring(0, 60),
        reason: 'Text starts with stray punctuation' });
    }

    // 5. Empty parens or brackets
    if (/\(\s*\)/.test(t)) {
      const m = t.match(/.{0,30}\(\s*\).{0,30}/);
      issues.push({ pg, id, itype: 'punctuation', severity: 'medium',
        current: (m?.[0] || '').substring(0, 80),
        suggested: (m?.[0] || '').replace(/\(\s*\)/g, '').substring(0, 80),
        reason: 'Empty parentheses' });
    }
    if (/\[\s*\]/.test(t)) {
      const m = t.match(/.{0,30}\[\s*\].{0,30}/);
      issues.push({ pg, id, itype: 'punctuation', severity: 'medium',
        current: (m?.[0] || '').substring(0, 80),
        suggested: (m?.[0] || '').replace(/\[\s*\]/g, '').substring(0, 80),
        reason: 'Empty brackets' });
    }

    // 6. Lowercase header start
    if (rtype === 'header' && /^[a-z]/.test(t)) {
      issues.push({ pg, id, itype: 'grammar', severity: 'low',
        current: t.substring(0, 60),
        suggested: t[0].toUpperCase() + t.substring(1, 60),
        reason: 'Header starts with lowercase' });
    }

    // 7. Repeated 5+ word phrases within same region
    const words = t.split(/\s+/);
    if (words.length > 30) {
      outer: for (let len = 6; len <= 10; len++) {
        for (let i = 0; i <= words.length - len * 2; i++) {
          const phrase = words.slice(i, i + len).join(' ').toLowerCase();
          const rest = words.slice(i + len).join(' ').toLowerCase();
          if (rest.includes(phrase) && phrase.length > 25) {
            issues.push({ pg, id, itype: 'content', severity: 'medium',
              current: words.slice(i, i + len).join(' ').substring(0, 80),
              suggested: '[remove duplicate phrase]',
              reason: 'Repeated phrase in same region' });
            break outer;
          }
        }
      }
    }

    // 8. Very short body noise
    if (rtype === 'body' && t.length < 15 && !/\d/.test(t) && !/[\u0590-\u05FF]/.test(t)) {
      const alpha = t.replace(/[^a-zA-Z]/g, '');
      if (alpha.length < 8) {
        issues.push({ pg, id, itype: 'content', severity: 'low',
          current: t, suggested: '[review]', reason: 'Very short body text — may be noise' });
      }
    }

    // 9. Double period (not ellipsis)
    const dblP = t.match(/[^.]\.\.[^.]/g);
    if (dblP) {
      const idx = t.indexOf(dblP[0]);
      const ctx = t.substring(Math.max(0, idx - 15), Math.min(t.length, idx + dblP[0].length + 15));
      issues.push({ pg, id, itype: 'punctuation', severity: 'low',
        current: ctx.substring(0, 60),
        suggested: ctx.replace(/([^.])\.\./g, '$1.').substring(0, 60),
        reason: 'Double period' });
    }
  }

  // Deduplicate
  const seen = new Set();
  const deduped = issues.filter(i => {
    const key = `${i.pg}:${i.itype}:${i.current.substring(0, 25)}`;
    if (seen.has(key)) return false;
    seen.add(key); return true;
  });

  // Sort: high first, then page
  const sev = { high: 0, medium: 1, low: 2 };
  deduped.sort((a, b) => (sev[a.severity] - sev[b.severity]) || (a.pg - b.pg));

  // Summary
  const byType = {}, bySev = {};
  for (const i of deduped) {
    byType[i.itype] = (byType[i.itype] || 0) + 1;
    bySev[i.severity] = (bySev[i.severity] || 0) + 1;
  }

  console.log('=== PROOFREADING RESULTS ===\n');
  console.log('Total issues:', deduped.length);
  console.log('By type:', JSON.stringify(byType));
  console.log('By severity:', JSON.stringify(bySev));

  for (const severity of ['high', 'medium', 'low']) {
    const items = deduped.filter(x => x.severity === severity);
    if (items.length === 0) continue;
    console.log(`\n=== ${severity.toUpperCase()} SEVERITY (${items.length}) ===`);
    const show = severity === 'low' ? items.slice(0, 20) : items;
    for (const i of show) {
      console.log('---');
      console.log(`PAGE: ${i.pg} | TYPE: ${i.itype} | SEVERITY: ${i.severity}`);
      console.log(`CURRENT: ${JSON.stringify(i.current)}`);
      console.log(`SUGGESTED: ${JSON.stringify(i.suggested)}`);
      console.log(`REASON: ${i.reason}`);
    }
    if (severity === 'low' && items.length > 20)
      console.log(`... and ${items.length - 20} more low-severity issues`);
  }

  await prisma.$disconnect();
}

proofread().catch(console.error);
