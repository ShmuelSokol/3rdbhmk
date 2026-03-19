#!/usr/bin/env node
/**
 * Autoresearch Catalog — Persistent experiment tracking
 * Saves every experiment's config, scores, PDFs, and git state.
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const RESULTS_DIR = path.join(__dirname, '..', 'autoresearch-results');
const CATALOG_PATH = path.join(RESULTS_DIR, 'catalog.jsonl');
const INDEX_PATH = path.join(RESULTS_DIR, 'index.json');
const PDFS_DIR = path.join(RESULTS_DIR, 'pdfs');

function ensureDirs() {
  for (const d of [RESULTS_DIR, PDFS_DIR]) {
    if (!fs.existsSync(d)) fs.mkdirSync(d, { recursive: true });
  }
}

function generateExperimentId() {
  const now = new Date();
  const ts = now.toISOString().replace(/[-:T]/g, '').substring(0, 14);
  const rand = Math.random().toString(16).substring(2, 6);
  return `exp-${ts}-${rand}`;
}

function getGitInfo() {
  try {
    const hash = execSync('git rev-parse --short HEAD', { encoding: 'utf8', cwd: path.join(__dirname, '..') }).trim();
    const branch = execSync('git branch --show-current', { encoding: 'utf8', cwd: path.join(__dirname, '..') }).trim();
    const dirty = execSync('git status --porcelain', { encoding: 'utf8', cwd: path.join(__dirname, '..') }).trim().length > 0;
    const diffStat = dirty ? execSync('git diff --stat', { encoding: 'utf8', cwd: path.join(__dirname, '..') }).trim() : '';
    return { hash, branch, dirty, diffStat };
  } catch {
    return { hash: 'unknown', branch: 'unknown', dirty: true, diffStat: '' };
  }
}

function appendExperiment(record) {
  ensureDirs();
  fs.appendFileSync(CATALOG_PATH, JSON.stringify(record) + '\n');
}

function savePdf(experimentId, label, pdfPath) {
  const expDir = path.join(PDFS_DIR, experimentId);
  if (!fs.existsSync(expDir)) fs.mkdirSync(expDir, { recursive: true });
  const dest = path.join(expDir, `${label}.pdf`);
  if (fs.existsSync(pdfPath)) {
    fs.copyFileSync(pdfPath, dest);
    return dest;
  }
  return null;
}

function loadCatalog() {
  if (!fs.existsSync(CATALOG_PATH)) return [];
  const lines = fs.readFileSync(CATALOG_PATH, 'utf8').split('\n').filter(Boolean);
  const records = [];
  for (const line of lines) {
    try { records.push(JSON.parse(line)); } catch { /* skip malformed */ }
  }
  return records;
}

function rebuildIndex() {
  const records = loadCatalog();
  const kept = records.filter(r => r.decision === 'keep' || r.decision === 'baseline');
  const best = kept.reduce((a, b) => (a && a.scores?.combined?.pct >= (b.scores?.combined?.pct || 0)) ? a : b, null);
  const baseline = records.find(r => r.decision === 'baseline');

  const index = {
    lastUpdated: new Date().toISOString(),
    experimentCount: records.length,
    bestExperiment: best?.id || null,
    bestScore: best?.scores?.combined?.total || 0,
    bestPct: best?.scores?.combined?.pct || 0,
    baselineScore: baseline?.scores?.combined?.total || 0,
    experiments: records.map(r => ({
      id: r.id,
      timestamp: r.timestamp,
      config: r.config,
      combinedScore: r.scores?.combined?.total || 0,
      combinedMax: r.scores?.combined?.max || 200,
      combinedPct: r.scores?.combined?.pct || 0,
      layoutScore: r.scores?.layout?.total || 0,
      artscrollScore: r.scores?.artscroll?.total || 0,
      decision: r.decision,
      description: r.description,
    })),
  };

  fs.writeFileSync(INDEX_PATH, JSON.stringify(index, null, 2));
  return index;
}

module.exports = {
  RESULTS_DIR, CATALOG_PATH, INDEX_PATH, PDFS_DIR,
  ensureDirs, generateExperimentId, getGitInfo,
  appendExperiment, savePdf, loadCatalog, rebuildIndex,
};
