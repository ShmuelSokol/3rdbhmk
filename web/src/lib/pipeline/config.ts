/**
 * Pipeline configuration — all tunable parameters for steps 2, 4, and 5.
 * Used by autoresearch to optimize the final rendered output.
 *
 * Override defaults by placing a `pipeline-config.json` file in the project root,
 * or by passing config overrides via the pipeline API.
 */
import { readFileSync } from 'fs'
import { join } from 'path'

export interface Step2Config {
  /** Zone split: gap > multiplier × avg line height */
  zoneGapMultiplier: number
  /** Zone split: minimum gap (%) regardless of line height */
  zoneGapMin: number
  /** Body group split: gap > multiplier × avg line height */
  bodyGapMultiplier: number
  /** Body group split: minimum gap (%) */
  bodyGapMin: number
  /** Running header: lines above multiplier × avg line height from top */
  headerCutoffMultiplier: number
  /** Running header: minimum Y cutoff (%) */
  headerCutoffMin: number
  /** Multi-column detection: look ±window lines for y-overlapping neighbors */
  multiColWindow: number
  /** Multi-column detection: min x-center separation (%) */
  multiColXSep: number
  /** Annotation vs body split: min chars per line for body text */
  bodyCharThreshold: number
  /** Scattered layout: x-bucket width (%) */
  scatteredBucketWidth: number
  /** Scattered layout: if top 2 buckets hold > threshold of lines → columnar */
  scatteredTop2Threshold: number
  /** Scattered layout: need >= this many x-buckets to classify as scattered */
  scatteredMinBuckets: number
  /** Table zone merge: max gap (%) between adjacent table zones */
  tableMergeGap: number
  /** Centered line: max width (%) to consider centered */
  centeredMaxWidth: number
  /** Centered line: max width as fraction of body width */
  centeredBodyWidthRatio: number
  /** Centered line: max left-right gap asymmetry (%) */
  centeredSymmetryThreshold: number
  /** Annotation clustering: max Y gap (%) between annotation lines */
  annotationYGap: number
  /** Column detection: min X overlap fraction */
  columnXOverlap: number
  /** Width transition split: min left-edge shift (%) */
  widthTransitionThreshold: number
  /** Split body regions taller than this (% of page) at largest internal gap */
  tallRegionSplitThreshold: number
  /** Minimum gap (as fraction of avg line height) to allow splitting a tall region */
  tallRegionMinGapRatio: number
}

export interface Step4Config {
  /** Max pixel variance for safe expansion strip */
  varianceThreshold: number
  /** Max RGB color distance from reference background */
  colorDistThreshold: number
  /** Expansion step size (%) */
  expansionStep: number
  /** Page edge margin (%) */
  pageMargin: number
  /** Additional buffer inside page margin (%) */
  buffer: number
  /** Height of scan strip for gap color sampling (%) */
  gapScanHeight: number
  /** Max variance for gap color samples */
  gapScanVariance: number
  /** Whether to expand table regions horizontally */
  expandTableHorizontal: boolean
}

export interface Step5Config {
  /** Minimum font shrink ratio (0.5 = allow shrinking to 50% of Hebrew) */
  minFontRatio: number
  /** Line height as multiplier of font size */
  lineHeightMultiplier: number
  /** Initial English font size as fraction of Hebrew pixel size */
  fontSizeScale: number
  /** Lines wider than this fraction of region → left-align */
  wideLineThreshold: number
  /** Absolute minimum font size (px) */
  minAbsoluteFont: number
  /** Empty/blank line height as fraction of normal line height */
  emptyLineHeightRatio: number
}

export interface PipelineConfig {
  step2: Step2Config
  step4: Step4Config
  step5: Step5Config
}

export const DEFAULT_CONFIG: PipelineConfig = {
  step2: {
    zoneGapMultiplier: 3,
    zoneGapMin: 3,
    bodyGapMultiplier: 2,
    bodyGapMin: 1.5,
    headerCutoffMultiplier: 2,
    headerCutoffMin: 2,
    multiColWindow: 5,
    multiColXSep: 20,
    bodyCharThreshold: 30,
    scatteredBucketWidth: 15,
    scatteredTop2Threshold: 0.55,
    scatteredMinBuckets: 3,
    tableMergeGap: 5,
    centeredMaxWidth: 40,
    centeredBodyWidthRatio: 0.7,
    centeredSymmetryThreshold: 15,
    annotationYGap: 2,
    columnXOverlap: 0.3,
    widthTransitionThreshold: 10,
    tallRegionSplitThreshold: 25,
    tallRegionMinGapRatio: 0.5,
  },
  step4: {
    varianceThreshold: 150,
    colorDistThreshold: 20,
    expansionStep: 1,
    pageMargin: 2,
    buffer: 1,
    gapScanHeight: 0.3,
    gapScanVariance: 30,
    expandTableHorizontal: false,
  },
  step5: {
    minFontRatio: 0.5,
    lineHeightMultiplier: 1.15,
    fontSizeScale: 0.85,
    wideLineThreshold: 0.8,
    minAbsoluteFont: 14,
    emptyLineHeightRatio: 0.5,
  },
}

/**
 * Load pipeline config. Merges:
 * 1. Defaults
 * 2. pipeline-config.json overrides (if file exists)
 * 3. Runtime overrides (if provided)
 */
export function loadConfig(overrides?: Partial<PipelineConfig>): PipelineConfig {
  let fileOverrides: Partial<PipelineConfig> = {}
  try {
    const configPath = join(process.cwd(), 'pipeline-config.json')
    const raw = readFileSync(configPath, 'utf8')
    fileOverrides = JSON.parse(raw)
  } catch {
    // No config file — use defaults
  }

  return {
    step2: { ...DEFAULT_CONFIG.step2, ...fileOverrides.step2, ...overrides?.step2 },
    step4: { ...DEFAULT_CONFIG.step4, ...fileOverrides.step4, ...overrides?.step4 },
    step5: { ...DEFAULT_CONFIG.step5, ...fileOverrides.step5, ...overrides?.step5 },
  }
}
