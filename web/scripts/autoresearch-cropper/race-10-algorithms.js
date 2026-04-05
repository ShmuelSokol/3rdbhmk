#!/usr/bin/env node
/**
 * Race 10 different cropping algorithms against ground truth.
 * Each algorithm takes a different approach to finding illustrations.
 */

const sharp = require('sharp');
const fs = require('fs');
const path = require('path');

const IMAGES = '/tmp/bhmk/jcqje5aut5wve5w5b8hv6fcq8/pages';
const GT_PATH = '/tmp/user_crops_v3.json';
const ORIG_PATH = path.join(__dirname, '../../public/illustration-crops.json');

// ─── Ground Truth ──────────────────────────────────────────────────────────

function loadGT() {
  const cur = JSON.parse(fs.readFileSync(GT_PATH, 'utf8'));
  const orig = JSON.parse(fs.readFileSync(ORIG_PATH, 'utf8'));
  const locked = cur._locked || [];
  const gt = {};
  for (const k of Object.keys(cur)) {
    if (k === '_locked') continue;
    if (JSON.stringify(cur[k]) !== JSON.stringify(orig[k]) || locked.includes(k)) gt[k] = cur[k];
  }
  return gt;
}

// ─── Scoring ───────────────────────────────────────────────────────────────

function iou(a, b) {
  const aL=a.leftPct,aR=aL+a.widthPct,aT=a.topPct,aB=aT+a.heightPct;
  const bL=b.leftPct,bR=bL+b.widthPct,bT=b.topPct,bB=bT+b.heightPct;
  const iL=Math.max(aL,bL),iR=Math.min(aR,bR),iT=Math.max(aT,bT),iB=Math.min(aB,bB);
  if(iR<=iL||iB<=iT) return 0;
  const inter=(iR-iL)*(iB-iT),union=a.widthPct*a.heightPct+b.widthPct*b.heightPct-inter;
  return union>0?inter/union:0;
}

function scorePage(auto, gt2) {
  if (!gt2.length && !auto.length) return 1;
  if (!gt2.length) return 0;
  const m = new Set(); let tI = 0;
  for (const g of gt2) {
    let best=0,bi=-1;
    for (let i=0;i<auto.length;i++) { if(m.has(i))continue; const s=iou(g,auto[i]); if(s>best){best=s;bi=i;} }
    if (bi>=0&&best>0.1) { m.add(bi); tI+=best; }
  }
  const p=auto.length>0?m.size/auto.length:1, r=gt2.length>0?m.size/gt2.length:1, a=gt2.length>0?tI/gt2.length:0;
  return a*0.6+p*0.2+r*0.2;
}

async function evaluate(extractFn, gt) {
  const pages = Object.keys(gt); let total = 0, count = 0;
  for (const pn of pages) {
    const f = path.join(IMAGES, `page-${pn}.png`);
    if (!fs.existsSync(f)) continue;
    try { const auto = await extractFn(f); total += scorePage(auto, gt[pn]); count++; } catch {}
  }
  return count > 0 ? total / count * 100 : 0;
}

// ─── Shared Helpers ────────────────────────────────────────────────────────

function isColored(r, g, b) {
  const br = (r+g+b)/3;
  if (br > 215 || br < 45) return false;
  const mx=Math.max(r,g,b),mn=Math.min(r,g,b),rng=mx-mn;
  if (rng < 20 && br < 180) return false;
  if (r > 195 && g > 180 && b > 145 && rng < 40) return false;
  return true;
}

async function getPixels(f) {
  const buf = fs.readFileSync(f);
  const meta = await sharp(buf).metadata();
  const W = meta.width, H = meta.height, ch = meta.channels || 3;
  const raw = await sharp(buf).raw().toBuffer();
  return { raw, W, H, ch };
}

// ─── Algorithm 1: Current V1 (row + column) ───────────────────────────────
async function algo1(f) {
  const { extractCrops } = require('./cropper-skill');
  const best = JSON.parse(fs.readFileSync(path.join(__dirname, 'best-params.json'), 'utf8'));
  return extractCrops(f, best);
}

// ─── Algorithm 2: Blob detection ──────────────────────────────────────────
async function algo2(f) {
  const { extractCrops } = require('./cropper-v2-blob');
  const best = JSON.parse(fs.readFileSync(path.join(__dirname, 'best-params-v2.json'), 'utf8'));
  return extractCrops(f, best);
}

// ─── Algorithm 3: Sliding window variance ─────────────────────────────────
// Scans with a tall window, measures color variance per window position
async function algo3(f) {
  const { raw, W, H, ch } = await getPixels(f);
  const winH = Math.round(H * 0.15); // 15% height window
  const step = Math.round(H * 0.02);
  const bands = [];
  
  for (let y = 0; y < H - winH; y += step) {
    let colored = 0, total = 0;
    for (let dy = 0; dy < winH; dy += 3) {
      for (let x = Math.round(W*0.05); x < Math.round(W*0.95); x += 4) {
        const i = ((y+dy)*W+x)*ch; total++;
        if (isColored(raw[i],raw[i+1],raw[i+2])) colored++;
      }
    }
    if (total > 0 && colored/total > 0.08) bands.push({ y, density: colored/total });
  }
  
  // Merge consecutive windows into regions
  const regions = []; let start = -1, end = -1;
  for (const b of bands) {
    if (start < 0) { start = b.y; end = b.y + winH; }
    else if (b.y <= end + step * 2) { end = b.y + winH; }
    else { if ((end-start)/H > 0.06) regions.push({top:start,bottom:end}); start = b.y; end = b.y + winH; }
  }
  if (start >= 0 && (end-start)/H > 0.06) regions.push({top:start,bottom:end});
  
  // Filter headers + find column extent
  return regions.filter(r => !(r.top/H < 0.12 && (r.bottom-r.top)/H < 0.10)).map(r => {
    let minX=W, maxX=0;
    for (let y=r.top; y<r.bottom; y+=4) {
      for (let x=0; x<W; x+=3) {
        const i=(y*W+x)*ch;
        if (isColored(raw[i],raw[i+1],raw[i+2])) { if(x<minX)minX=x; if(x>maxX)maxX=x; }
      }
    }
    const pad = W*0.01;
    return { topPct: Math.round(Math.max(0,r.top-pad)/H*1000)/1000, leftPct: Math.round(Math.max(0,minX-pad)/W*1000)/1000,
      widthPct: Math.round(Math.min(W,maxX-minX+pad*2)/W*1000)/1000, heightPct: Math.round(Math.min(H,r.bottom-r.top+pad*2)/H*1000)/1000 };
  }).filter(c => c.widthPct > 0.08 && c.heightPct > 0.04);
}

// ─── Algorithm 4: Edge detection (gradient magnitude) ─────────────────────
async function algo4(f) {
  const { raw, W, H, ch } = await getPixels(f);
  // Compute horizontal gradient magnitude per row
  const rowEdge = new Float32Array(H);
  for (let y = 0; y < H; y++) {
    let edges = 0, total = 0;
    for (let x = 1; x < W-1; x += 2) {
      const i1 = (y*W+x-1)*ch, i2 = (y*W+x+1)*ch;
      const dr = Math.abs(raw[i2]-raw[i1]), dg = Math.abs(raw[i2+1]-raw[i1+1]), db = Math.abs(raw[i2+2]-raw[i1+2]);
      total++;
      if (dr+dg+db > 60) edges++;
    }
    rowEdge[y] = total > 0 ? edges/total : 0;
  }
  
  // Find bands with high edge density (illustrations have many edges)
  const bands = []; let inB=false, st=0;
  for (let y=0; y<H; y++) {
    if (rowEdge[y] > 0.15) { if(!inB){inB=true;st=y;} }
    else { if(inB){ if((y-st)/H>0.04) bands.push({top:st,bottom:y}); inB=false; } }
  }
  if (inB && (H-st)/H>0.04) bands.push({top:st,bottom:H});
  
  // Merge close
  const mg = [];
  for (const b of bands) { if(mg.length>0&&(b.top-mg[mg.length-1].bottom)/H<0.03) mg[mg.length-1].bottom=b.bottom; else mg.push({...b}); }
  
  return mg.filter(b => !(b.top/H<0.12&&(b.bottom-b.top)/H<0.10)).map(b => {
    let minX=W,maxX=0;
    for(let y=b.top;y<b.bottom;y+=4){for(let x=0;x<W;x+=3){const i=(y*W+x)*ch;if(isColored(raw[i],raw[i+1],raw[i+2])){if(x<minX)minX=x;if(x>maxX)maxX=x;}}}
    const pad=W*0.01;
    return{topPct:Math.round(Math.max(0,b.top-pad)/H*1000)/1000,leftPct:Math.round(Math.max(0,minX-pad)/W*1000)/1000,
      widthPct:Math.round(Math.min(W,maxX-minX+pad*2)/W*1000)/1000,heightPct:Math.round(Math.min(H,b.bottom-b.top+pad*2)/H*1000)/1000};
  }).filter(c=>c.widthPct>0.08&&c.heightPct>0.04);
}

// ─── Algorithm 5: HSV saturation-based ────────────────────────────────────
async function algo5(f) {
  const { raw, W, H, ch } = await getPixels(f);
  const rowSat = new Float32Array(H);
  for (let y=0; y<H; y++) {
    let satSum=0, total=0;
    for (let x=Math.round(W*0.03); x<Math.round(W*0.97); x+=3) {
      const i=(y*W+x)*ch, r=raw[i],g=raw[i+1],b=raw[i+2];
      const mx=Math.max(r,g,b),mn=Math.min(r,g,b);
      const sat = mx>0?(mx-mn)/mx:0;
      const br=(r+g+b)/3;
      if (br>40 && br<220) { satSum+=sat; total++; }
    }
    rowSat[y] = total>0?satSum/total:0;
  }
  
  const bands=[]; let inB=false,st=0;
  for(let y=0;y<H;y++){
    if(rowSat[y]>0.06){if(!inB){inB=true;st=y;}}
    else{if(inB){if((y-st)/H>0.04)bands.push({top:st,bottom:y});inB=false;}}
  }
  if(inB&&(H-st)/H>0.04) bands.push({top:st,bottom:H});
  
  const mg=[];
  for(const b of bands){if(mg.length>0&&(b.top-mg[mg.length-1].bottom)/H<0.02)mg[mg.length-1].bottom=b.bottom;else mg.push({...b});}
  
  return mg.filter(b=>!(b.top/H<0.12&&(b.bottom-b.top)/H<0.08)).map(b=>{
    let minX=W,maxX=0;
    for(let y=b.top;y<b.bottom;y+=4){for(let x=0;x<W;x+=3){const i=(y*W+x)*ch;if(isColored(raw[i],raw[i+1],raw[i+2])){if(x<minX)minX=x;if(x>maxX)maxX=x;}}}
    const pad=W*0.008;
    return{topPct:Math.round(Math.max(0,b.top-pad)/H*1000)/1000,leftPct:Math.round(Math.max(0,minX-pad)/W*1000)/1000,
      widthPct:Math.round(Math.min(W,maxX-minX+pad*2)/W*1000)/1000,heightPct:Math.round(Math.min(H,b.bottom-b.top+pad*2)/H*1000)/1000};
  }).filter(c=>c.widthPct>0.08&&c.heightPct>0.04);
}

// ─── Algorithm 6: Two-pass (coarse + fine) ────────────────────────────────
// First pass at low res finds rough regions, second pass refines at full res
async function algo6(f) {
  const buf = fs.readFileSync(f);
  const meta = await sharp(buf).metadata();
  const W = meta.width, H = meta.height, ch = meta.channels || 3;
  
  // Coarse pass: downsample to 200px wide
  const smallW = 200, smallH = Math.round(H/W*200);
  const smallBuf = await sharp(buf).resize(smallW, smallH).raw().toBuffer();
  const sCh = 3;
  
  // Build coarse color map
  const rowD = new Float32Array(smallH);
  for (let y=0; y<smallH; y++) {
    let c=0,t=0;
    for (let x=5; x<smallW-5; x++) {
      const i=(y*smallW+x)*sCh; t++;
      if(isColored(smallBuf[i],smallBuf[i+1],smallBuf[i+2])) c++;
    }
    rowD[y] = t>0?c/t:0;
  }
  
  // Find coarse bands
  const bands=[]; let inB=false,st=0;
  for(let y=0;y<smallH;y++){
    if(rowD[y]>0.05){if(!inB){inB=true;st=y;}}
    else{if(inB){if((y-st)/smallH>0.03)bands.push({top:st/smallH,bottom:y/smallH});inB=false;}}
  }
  if(inB&&(smallH-st)/smallH>0.03) bands.push({top:st/smallH,bottom:1});
  
  // Merge
  const mg=[];
  for(const b of bands){if(mg.length>0&&b.top-mg[mg.length-1].bottom<0.02)mg[mg.length-1].bottom=b.bottom;else mg.push({...b});}
  
  // Fine pass: refine column extent at full res
  const raw = await sharp(buf).raw().toBuffer();
  return mg.filter(b=>!(b.top<0.12&&(b.bottom-b.top)<0.08)&&(b.bottom-b.top)>0.035).map(b=>{
    const yStart=Math.round(b.top*H), yEnd=Math.round(b.bottom*H);
    let minX=W,maxX=0;
    for(let y=yStart;y<yEnd;y+=3){for(let x=0;x<W;x+=3){const i=(y*W+x)*ch;if(isColored(raw[i],raw[i+1],raw[i+2])){if(x<minX)minX=x;if(x>maxX)maxX=x;}}}
    const pad=W*0.01;
    return{topPct:Math.round(Math.max(0,yStart-pad)/H*1000)/1000,leftPct:Math.round(Math.max(0,minX-pad)/W*1000)/1000,
      widthPct:Math.round(Math.min(W,maxX-minX+pad*2)/W*1000)/1000,heightPct:Math.round(Math.min(H,yEnd-yStart+pad*2)/H*1000)/1000};
  }).filter(c=>c.widthPct>0.08&&c.heightPct>0.035);
}

// ─── Algorithm 7: Column-first (vertical scan then horizontal) ────────────
async function algo7(f) {
  const { raw, W, H, ch } = await getPixels(f);
  // Column density first
  const colD = new Float32Array(W);
  for (let x=0; x<W; x+=2) {
    let c=0,t=0;
    for(let y=Math.round(H*0.1);y<Math.round(H*0.95);y+=3){const i=(y*W+x)*ch;t++;if(isColored(raw[i],raw[i+1],raw[i+2]))c++;}
    colD[x]=t>0?c/t:0;
  }
  
  // Find column clusters
  const clusters=[]; let inC=false,cSt=0;
  for(let x=0;x<W;x+=2){
    if(colD[x]>0.04){if(!inC){inC=true;cSt=x;}}
    else{if(inC){if((x-cSt)/W>0.06)clusters.push({left:cSt,right:x});inC=false;}}
  }
  if(inC&&(W-cSt)/W>0.06) clusters.push({left:cSt,right:W});
  
  // For each column cluster, find row extent
  const results=[];
  for(const cl of clusters){
    const rowD2=new Float32Array(H);
    for(let y=0;y<H;y++){let c=0,t=0;for(let x=cl.left;x<cl.right;x+=3){const i=(y*W+x)*ch;t++;if(isColored(raw[i],raw[i+1],raw[i+2]))c++;}rowD2[y]=t>0?c/t:0;}
    
    const bands=[]; let inB2=false,st2=0;
    for(let y=0;y<H;y++){if(rowD2[y]>0.06){if(!inB2){inB2=true;st2=y;}}else{if(inB2){if((y-st2)/H>0.04)bands.push({top:st2,bottom:y});inB2=false;}}}
    if(inB2&&(H-st2)/H>0.04) bands.push({top:st2,bottom:H});
    
    for(const b of bands){
      if(b.top/H<0.12&&(b.bottom-b.top)/H<0.08) continue;
      const pad=W*0.008;
      results.push({topPct:Math.round(Math.max(0,b.top-pad)/H*1000)/1000,leftPct:Math.round(Math.max(0,cl.left-pad)/W*1000)/1000,
        widthPct:Math.round(Math.min(W,cl.right-cl.left+pad*2)/W*1000)/1000,heightPct:Math.round(Math.min(H,b.bottom-b.top+pad*2)/H*1000)/1000});
    }
  }
  return results.filter(c=>c.widthPct>0.06&&c.heightPct>0.035);
}

// ─── Algorithm 8: Quadtree subdivision ────────────────────────────────────
async function algo8(f) {
  const { raw, W, H, ch } = await getPixels(f);
  
  function regionDensity(x0,y0,w,h) {
    let c=0,t=0;
    for(let y=y0;y<y0+h;y+=4){for(let x=x0;x<x0+w;x+=4){const i=(y*W+x)*ch;t++;if(isColored(raw[i],raw[i+1],raw[i+2]))c++;}}
    return t>0?c/t:0;
  }
  
  // Divide page into grid of 10x14 blocks
  const BW=10, BH=14;
  const blockW=Math.round(W/BW), blockH=Math.round(H/BH);
  const grid=[];
  for(let r=0;r<BH;r++){grid[r]=[];for(let c=0;c<BW;c++){grid[r][c]=regionDensity(c*blockW,r*blockH,blockW,blockH)>0.08?1:0;}}
  
  // Find rectangular regions of filled blocks
  const results=[];
  const visited=Array.from({length:BH},()=>new Uint8Array(BW));
  
  for(let r=0;r<BH;r++){
    for(let c=0;c<BW;c++){
      if(!grid[r][c]||visited[r][c]) continue;
      // Expand right and down
      let maxC=c, maxR=r;
      while(maxC+1<BW&&grid[r][maxC+1]&&!visited[r][maxC+1]) maxC++;
      outer: while(maxR+1<BH){
        for(let cc=c;cc<=maxC;cc++){if(!grid[maxR+1][cc]||visited[maxR+1][cc]) break outer;}
        maxR++;
      }
      // Mark visited
      for(let rr=r;rr<=maxR;rr++) for(let cc=c;cc<=maxC;cc++) visited[rr][cc]=1;
      
      const top=r*blockH/H, left=c*blockW/W, w=(maxC-c+1)*blockW/W, h=(maxR-r+1)*blockH/H;
      if(w>0.06&&h>0.035&&!(top<0.12&&h<0.08)){
        results.push({topPct:Math.round(top*1000)/1000,leftPct:Math.round(left*1000)/1000,widthPct:Math.round(w*1000)/1000,heightPct:Math.round(h*1000)/1000});
      }
    }
  }
  return results;
}

// ─── Algorithm 9: Downsampled binary mask + morphological ops ─────────────
async function algo9(f) {
  const buf = fs.readFileSync(f);
  const meta = await sharp(buf).metadata();
  const W=meta.width, H=meta.height;
  // Downsample to 80px wide
  const sW=80, sH=Math.round(H/W*80);
  const small = await sharp(buf).resize(sW,sH).raw().toBuffer();
  
  // Binary mask
  const mask=new Uint8Array(sW*sH);
  for(let i=0;i<sW*sH;i++){const r=small[i*3],g=small[i*3+1],b=small[i*3+2];mask[i]=isColored(r,g,b)?1:0;}
  
  // Dilate (3x3)
  const dilated=new Uint8Array(sW*sH);
  for(let y=1;y<sH-1;y++){for(let x=1;x<sW-1;x++){
    let any=0;
    for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++)if(mask[(y+dy)*sW+x+dx])any=1;
    dilated[y*sW+x]=any;
  }}
  
  // Find connected components via flood fill
  const labels=new Int32Array(sW*sH);
  let label=0;
  function flood(y,x,l){
    const stack=[[y,x]];
    while(stack.length){
      const[cy,cx]=stack.pop();
      if(cy<0||cy>=sH||cx<0||cx>=sW||labels[cy*sW+cx]||!dilated[cy*sW+cx])continue;
      labels[cy*sW+cx]=l;
      stack.push([cy-1,cx],[cy+1,cx],[cy,cx-1],[cy,cx+1]);
    }
  }
  for(let y=0;y<sH;y++)for(let x=0;x<sW;x++){if(dilated[y*sW+x]&&!labels[y*sW+x]){label++;flood(y,x,label);}}
  
  // Bounding boxes
  const boxes={};
  for(let y=0;y<sH;y++)for(let x=0;x<sW;x++){
    const l=labels[y*sW+x]; if(!l)continue;
    if(!boxes[l])boxes[l]={minR:y,maxR:y,minC:x,maxC:x,count:0};
    const b=boxes[l]; b.minR=Math.min(b.minR,y);b.maxR=Math.max(b.maxR,y);b.minC=Math.min(b.minC,x);b.maxC=Math.max(b.maxC,x);b.count++;
  }
  
  return Object.values(boxes).filter(b=>b.count>15).map(b=>{
    const top=b.minR/sH,left=b.minC/sW,w=(b.maxC-b.minC+1)/sW,h=(b.maxR-b.minR+1)/sH;
    return{topPct:Math.round(Math.max(0,top-0.008)*1000)/1000,leftPct:Math.round(Math.max(0,left-0.008)*1000)/1000,
      widthPct:Math.round(Math.min(1,w+0.016)*1000)/1000,heightPct:Math.round(Math.min(1,h+0.016)*1000)/1000};
  }).filter(c=>c.widthPct>0.06&&c.heightPct>0.035&&!(c.topPct<0.12&&c.heightPct<0.08));
}

// ─── Algorithm 10: Hybrid V1+V7 (row-first + column-first, union) ────────
async function algo10(f) {
  const r1 = await algo1(f);
  const r7 = await algo7(f);
  // Union: keep crops from both, dedup by IoU > 0.5
  const all = [...r1];
  for (const c of r7) {
    const overlap = all.some(a => iou(a, c) > 0.5);
    if (!overlap) all.push(c);
  }
  return all;
}

// ─── RACE ──────────────────────────────────────────────────────────────────

const algorithms = [
  { name: 'V1: Row+Column (current best)', fn: algo1 },
  { name: 'V2: Blob detection', fn: algo2 },
  { name: 'V3: Sliding window variance', fn: algo3 },
  { name: 'V4: Edge detection (gradient)', fn: algo4 },
  { name: 'V5: HSV saturation', fn: algo5 },
  { name: 'V6: Two-pass (coarse+fine)', fn: algo6 },
  { name: 'V7: Column-first', fn: algo7 },
  { name: 'V8: Quadtree subdivision', fn: algo8 },
  { name: 'V9: Morphological (dilate+flood)', fn: algo9 },
  { name: 'V10: Hybrid V1+V7 union', fn: algo10 },
];

(async () => {
  const gt = loadGT();
  console.log(`Racing 10 algorithms against ${Object.keys(gt).length} ground truth pages...\n`);
  
  const results = [];
  for (const algo of algorithms) {
    process.stdout.write(`  ${algo.name}... `);
    const t0 = Date.now();
    const score = await evaluate(algo.fn, gt);
    const elapsed = ((Date.now() - t0) / 1000).toFixed(1);
    console.log(`${score.toFixed(1)}/100  (${elapsed}s)`);
    results.push({ name: algo.name, score, elapsed });
  }
  
  results.sort((a, b) => b.score - a.score);
  console.log('\n=== LEADERBOARD ===');
  results.forEach((r, i) => {
    const bar = '█'.repeat(Math.round(r.score / 2));
    console.log(`${i + 1}. ${r.score.toFixed(1)} ${bar} ${r.name} (${r.elapsed}s)`);
  });
  
  console.log(`\nWinner: ${results[0].name} (${results[0].score.toFixed(1)})`);
  fs.writeFileSync(path.join(__dirname, 'race-results.json'), JSON.stringify(results, null, 2));
})();
