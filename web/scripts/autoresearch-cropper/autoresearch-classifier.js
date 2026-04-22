#!/usr/bin/env node
/**
 * Train a small classifier to predict which algo (V1, V2, V7) wins per page.
 * Uses 10+ cheap image features and a shallow decision tree with 5-fold CV.
 * Reports CV score (honest, no overfit), then applies to ALL non-locked pages.
 */
const fs = require('fs');
const path = require('path');
const sharp = require('sharp');
const { extractCrops: v1Extract } = require('./cropper-skill');
const { extractCrops: v2Extract } = require('./cropper-v2-blob');

const IMAGES = '/tmp/bhmk/jcqje5aut5wve5w5b8hv6fcq8/pages';
const CROPS_JSON = path.join(__dirname, '../../public/illustration-crops.json');
const BEST_V1 = path.join(__dirname, 'best-params.json');
const BEST_V2 = path.join(__dirname, 'best-params-autoresearch.json');

function iou(a, b) {
  const aL=a.leftPct,aR=aL+a.widthPct,aT=a.topPct,aB=aT+a.heightPct;
  const bL=b.leftPct,bR=bL+b.widthPct,bT=b.topPct,bB=bT+b.heightPct;
  const iL=Math.max(aL,bL),iR=Math.min(aR,bR);
  const iT=Math.max(aT,bT),iB=Math.min(aB,bB);
  if(iR<=iL||iB<=iT) return 0;
  const inter=(iR-iL)*(iB-iT), union=a.widthPct*a.heightPct+b.widthPct*b.heightPct-inter;
  return union>0?inter/union:0;
}
function scorePage(auto, gt) {
  if (!gt.length && !auto.length) return 1;
  if (!gt.length && auto.length) return Math.max(0, 1 - auto.length * 0.35);
  if (gt.length && !auto.length) return 0;
  const m=new Set(); let tI=0;
  for (const g of gt) {
    let best=0,bi=-1;
    for (let i=0;i<auto.length;i++) { if(m.has(i)) continue; const s=iou(g,auto[i]); if(s>best){best=s;bi=i;} }
    if (bi>=0&&best>0.1) { m.add(bi); tI+=best; }
  }
  const p=auto.length>0?m.size/auto.length:1;
  const r=gt.length>0?m.size/gt.length:1;
  const a=gt.length>0?tI/gt.length:0;
  return a*0.6+p*0.2+r*0.2;
}
function isColored(r,g,b) {
  const br=(r+g+b)/3;
  if(br>215||br<45) return false;
  const mx=Math.max(r,g,b),mn=Math.min(r,g,b),rng=mx-mn;
  if(rng<20&&br<180) return false;
  if(r>195&&g>180&&b>145&&rng<40) return false;
  return true;
}
async function getPixels(f) {
  const buf = fs.readFileSync(f);
  const meta = await sharp(buf).metadata();
  const W=meta.width, H=meta.height, ch=meta.channels||3;
  const raw = await sharp(buf).raw().toBuffer();
  return { raw, W, H, ch };
}

// ─── Feature extraction (11 features) ───────────────────────────────────
async function extractFeatures(f) {
  const { raw, W, H, ch } = await getPixels(f);
  // Pass 1: sample grid for color + saturation + edges
  let coloredPx=0, total=0, satSum=0, edgeSum=0, edgeTotal=0;
  const rowColored = new Float32Array(H), colColored = new Float32Array(W);
  for (let y=0; y<H; y+=2) {
    for (let x=0; x<W; x+=2) {
      const i=(y*W+x)*ch; total++;
      const r=raw[i], g=raw[i+1], b=raw[i+2];
      const c = isColored(r,g,b);
      if (c) { coloredPx++; rowColored[y]++; colColored[x]++; }
      const mx=Math.max(r,g,b), mn=Math.min(r,g,b);
      satSum += mx>0 ? (mx-mn)/mx : 0;
      // Horizontal gradient
      if (x>1) {
        const j=(y*W+x-2)*ch;
        const dr=Math.abs(r-raw[j]), dg=Math.abs(g-raw[j+1]), db=Math.abs(b-raw[j+2]);
        edgeTotal++;
        if (dr+dg+db > 60) edgeSum++;
      }
    }
  }
  const colorDensity = coloredPx / total;
  const meanSat = satSum / total;
  const edgeDensity = edgeSum / edgeTotal;

  // Row density → bands
  const rowD = new Float32Array(H);
  const sampleCols = Math.ceil(W/2);
  for (let y=0; y<H; y++) rowD[y] = rowColored[y] / sampleCols;
  let bandCount=0, inB=false, st=0, maxBandH=0, totalBandH=0, firstBandTop=-1, lastBandBot=0;
  for (let y=0; y<H; y++) {
    if (rowD[y] > 0.05) { if (!inB) { inB=true; st=y; } }
    else { if (inB) {
      const bh=(y-st)/H; bandCount++; maxBandH=Math.max(maxBandH,bh); totalBandH+=bh;
      if (firstBandTop<0) firstBandTop=st/H; lastBandBot=y/H;
      inB=false;
    } }
  }
  if (inB) { const bh=(H-st)/H; bandCount++; maxBandH=Math.max(maxBandH,bh); totalBandH+=bh; if(firstBandTop<0) firstBandTop=st/H; lastBandBot=1; }

  // Column extent of colored pixels (rough blob width)
  let minColX=W, maxColX=0;
  const sampleRows = Math.ceil(H/2);
  for (let x=0; x<W; x+=2) {
    if (colColored[x]/sampleRows > 0.02) { if (x<minColX) minColX=x; if (x>maxColX) maxColX=x; }
  }
  const colorSpanX = (maxColX - minColX) / W;

  // Center of mass Y (weighted by colored density)
  let comY=0, comW=0;
  for (let y=0; y<H; y++) { comY += y * rowD[y]; comW += rowD[y]; }
  const centerMassY = comW > 0 ? comY / comW / H : 0.5;

  return {
    colorDensity,
    meanSat,
    edgeDensity,
    bandCount,
    maxBandH,
    totalBandH,
    firstBandTop: firstBandTop < 0 ? 1 : firstBandTop,
    lastBandBot,
    colorSpanX,
    centerMassY,
    aspectRatio: W / H,
  };
}

// ─── Shallow decision tree (CART-style, depth ≤ 3) ──────────────────────
function buildTree(rows, featNames, depth = 0, maxDepth = 3) {
  // rows: [{features, label, score_v1, score_v2, score_v7}]
  // Objective: at each node, pick (feature, threshold) that maximizes
  // total score across pages if we commit to the majority's algo in each branch.
  if (depth >= maxDepth || rows.length < 6) {
    // Leaf: pick algo that maximizes sum of scores
    const sums = { o1: 0, o2: 0, o7: 0 };
    for (const r of rows) { sums.o1 += r.score_v1; sums.o2 += r.score_v2; sums.o7 += r.score_v7; }
    const algo = Object.entries(sums).sort((a, b) => b[1] - a[1])[0][0];
    return { leaf: true, algo, n: rows.length };
  }
  let best = { gain: -Infinity };
  for (const feat of featNames) {
    const sorted = rows.map(r => r.features[feat]).sort((a, b) => a - b);
    const thresholds = [];
    for (let q = 0.15; q < 0.9; q += 0.08) thresholds.push(sorted[Math.floor(sorted.length * q)]);
    for (const t of thresholds) {
      const L = [], R = [];
      for (const r of rows) (r.features[feat] < t ? L : R).push(r);
      if (L.length < 3 || R.length < 3) continue;
      const pickL = bestAlgoFor(L);
      const pickR = bestAlgoFor(R);
      const total = L.reduce((s, r) => s + r[`score_${pickL.replace('o','v')}`], 0)
                  + R.reduce((s, r) => s + r[`score_${pickR.replace('o','v')}`], 0);
      if (total > best.gain) best = { gain: total, feat, t, L, R };
    }
  }
  if (best.gain === -Infinity) return buildTree(rows, featNames, maxDepth, maxDepth);
  return {
    leaf: false,
    feat: best.feat,
    threshold: best.t,
    left: buildTree(best.L, featNames, depth + 1, maxDepth),
    right: buildTree(best.R, featNames, depth + 1, maxDepth),
  };
}
function bestAlgoFor(rows) {
  const sums = { o1: 0, o2: 0, o7: 0 };
  for (const r of rows) { sums.o1 += r.score_v1; sums.o2 += r.score_v2; sums.o7 += r.score_v7; }
  return Object.entries(sums).sort((a, b) => b[1] - a[1])[0][0];
}
function predict(tree, feat) {
  if (tree.leaf) return tree.algo;
  return feat[tree.feat] < tree.threshold ? predict(tree.left, feat) : predict(tree.right, feat);
}
function stringifyTree(t, indent = 0) {
  const pad = '  '.repeat(indent);
  if (t.leaf) return `${pad}→ ${t.algo} (n=${t.n})`;
  return `${pad}if ${t.feat} < ${t.threshold.toFixed(4)}\n${stringifyTree(t.left, indent + 1)}\n${pad}else\n${stringifyTree(t.right, indent + 1)}`;
}

async function main() {
  const d = JSON.parse(fs.readFileSync(CROPS_JSON, 'utf8'));
  const locked = d._locked || [];
  const paramsV1 = JSON.parse(fs.readFileSync(BEST_V1, 'utf8'));
  const paramsV2 = JSON.parse(fs.readFileSync(BEST_V2, 'utf8'));

  async function v7(f) {
    const { raw, W, H, ch } = await getPixels(f);
    const colD=new Float32Array(W);
    for (let x=0; x<W; x+=2) { let c=0,t=0; for (let y=Math.round(H*0.1); y<Math.round(H*0.95); y+=3) { const i=(y*W+x)*ch; t++; if(isColored(raw[i],raw[i+1],raw[i+2])) c++; } colD[x]=t>0?c/t:0; }
    const clusters=[]; let inC=false,cSt=0;
    for(let x=0;x<W;x+=2){ if(colD[x]>0.04){if(!inC){inC=true;cSt=x;}} else{ if(inC){if((x-cSt)/W>0.06) clusters.push({left:cSt,right:x}); inC=false;}} }
    if(inC&&(W-cSt)/W>0.06) clusters.push({left:cSt,right:W});
    const results=[];
    for (const cl of clusters) {
      const rowD=new Float32Array(H);
      for(let y=0;y<H;y++){ let c=0,t=0; for(let x=cl.left;x<cl.right;x+=3){ const i=(y*W+x)*ch; t++; if(isColored(raw[i],raw[i+1],raw[i+2])) c++; } rowD[y]=t>0?c/t:0; }
      const bands=[]; let inB=false,st=0;
      for(let y=0;y<H;y++){ if(rowD[y]>0.06){if(!inB){inB=true;st=y;}} else{ if(inB){if((y-st)/H>0.04) bands.push({top:st,bottom:y}); inB=false;}} }
      if(inB&&(H-st)/H>0.04) bands.push({top:st,bottom:H});
      for (const b of bands) {
        if(b.top/H<0.12&&(b.bottom-b.top)/H<0.08) continue;
        const pad=W*0.008;
        results.push({ topPct:Math.max(0,b.top-pad)/H, leftPct:Math.max(0,cl.left-pad)/W, widthPct:Math.min(W,cl.right-cl.left+pad*2)/W, heightPct:Math.min(H,b.bottom-b.top+pad*2)/H });
      }
    }
    return results.filter(c=>c.widthPct>0.06&&c.heightPct>0.035);
  }

  console.log('[1/4] Extracting algo outputs + features for 85 locked pages...');
  const rows = [];
  const t0 = Date.now();
  for (const pn of locked) {
    const f = path.join(IMAGES, `page-${pn}.jpg`);
    if (!fs.existsSync(f)) continue;
    try {
      const [o1, o2, o7, feat] = await Promise.all([
        v1Extract(f, paramsV1), v2Extract(f, paramsV2), v7(f), extractFeatures(f)
      ]);
      const gt = d[pn] || [];
      rows.push({
        pn, features: feat,
        score_v1: scorePage(o1, gt), score_v2: scorePage(o2, gt), score_v7: scorePage(o7, gt),
        o1, o2, o7, gt,
      });
    } catch (e) { console.log('err', pn, e.message.slice(0, 80)); }
  }
  console.log(`  done in ${((Date.now()-t0)/1000).toFixed(1)}s, ${rows.length} rows`);

  const featNames = ['colorDensity','meanSat','edgeDensity','bandCount','maxBandH','totalBandH','firstBandTop','lastBandBot','colorSpanX','centerMassY'];
  const mean = a => a.reduce((s,x)=>s+x,0)/a.length;
  const V1 = mean(rows.map(r=>r.score_v1))*100;
  const V2 = mean(rows.map(r=>r.score_v2))*100;
  const V7 = mean(rows.map(r=>r.score_v7))*100;
  const ORACLE = mean(rows.map(r=>Math.max(r.score_v1,r.score_v2,r.score_v7)))*100;
  console.log(`\n[2/4] Baselines:  V1=${V1.toFixed(2)}  V2=${V2.toFixed(2)}  V7=${V7.toFixed(2)}  ORACLE=${ORACLE.toFixed(2)}`);

  // ── 5-fold cross-validation ─────────────────────────────────────────
  const K = 5;
  const shuffled = [...rows].map(r => ({ ...r, fold: Math.floor(Math.random() * K) }));
  const cvScores = [];
  console.log(`\n[3/4] 5-fold CV on depth-3 tree (${featNames.length} features)...`);
  for (let k = 0; k < K; k++) {
    const train = shuffled.filter(r => r.fold !== k);
    const test = shuffled.filter(r => r.fold === k);
    const tree = buildTree(train, featNames);
    let total = 0;
    for (const r of test) {
      const algo = predict(tree, r.features);
      const out = r[algo];
      total += scorePage(out, r.gt);
    }
    const foldScore = test.length > 0 ? total / test.length * 100 : 0;
    cvScores.push(foldScore);
    console.log(`  fold ${k}: ${foldScore.toFixed(2)}% (n=${test.length})`);
  }
  const cvMean = mean(cvScores);
  const cvStd = Math.sqrt(mean(cvScores.map(s => (s - cvMean) ** 2)));
  console.log(`  CV mean: ${cvMean.toFixed(2)}% ± ${cvStd.toFixed(2)}`);

  // ── Train final model on all data ───────────────────────────────────
  console.log(`\n[4/4] Training final tree on all 85 pages...`);
  const finalTree = buildTree(rows, featNames);
  console.log(stringifyTree(finalTree));

  // Training score (overfit but useful to see)
  let trainTotal = 0;
  for (const r of rows) trainTotal += scorePage(r[predict(finalTree, r.features)], r.gt);
  const trainScore = trainTotal / rows.length * 100;
  console.log(`\nTraining score (overfit): ${trainScore.toFixed(2)}%`);

  // Save artifacts
  fs.writeFileSync(path.join(__dirname, 'classifier-tree.json'), JSON.stringify(finalTree, null, 2));
  fs.writeFileSync(path.join(__dirname, 'classifier-stats.json'), JSON.stringify({
    V1, V2, V7, ORACLE, cvScores, cvMean, cvStd, trainScore,
    featuresUsed: featNames,
  }, null, 2));

  console.log(`\n═══ SUMMARY ═══`);
  console.log(`V2 alone:          ${V2.toFixed(2)}%`);
  console.log(`CV-honest score:   ${cvMean.toFixed(2)}% ± ${cvStd.toFixed(2)}  ← REAL expected accuracy`);
  console.log(`Training score:    ${trainScore.toFixed(2)}% (overfit)`);
  console.log(`Oracle (ceiling):  ${ORACLE.toFixed(2)}%`);
}

main().catch(e => { console.error(e); process.exit(1); });
