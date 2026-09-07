// UE Custom-expression body. World coordinates in centimeters, Z up.
// Only basecolor/roughness/normal outputs: no geometry motion or depth changes.
float3 n = normalize(N);
float2 uv;
float pilotMask = 0.0;
#if __PAVING__
    uv = P.xy;
    pilotMask = n.z > 0.999 ? 1.0 : 0.0; // Thin slab edges stay canonical/plain.
#else
    // Cardinal courtyard walls: dominant side projection; vertical coordinate Z.
    // Corners/curved or diagonal surfaces need human review, not auto-assignment.
    uv = abs(n.z) > 0.5 ? P.xy : float2(abs(n.x) > abs(n.y) ? P.y : P.x, P.z);
    // Exact source AABBs of Ulam opening jambs 43/44 and lintel 45.
    // Restrict this review to the existing union faces inside those bounds.
    bool slabX = P.x >= -2750.01 && P.x <= -2499.99;
    bool jambY = abs(P.y) >= 349.99 && abs(P.y) <= 2500.01;
    bool jambZ = P.z >= 924.99 && P.z <= 5925.01;
    bool lintel = abs(P.y) <= 350.01 && P.z >= 3424.99 && P.z <= 5925.01;
    bool cardinalSide = abs(n.z) < 0.001 && max(abs(n.x),abs(n.y)) > 0.999;
    pilotMask = slabX && ((jambY && jambZ) || lintel) && cardinalSide ? 1.0 : 0.0;
#endif
uv += float2(GridOffsetUCm, GridOffsetVCm);
float2 dims = max(float2(BlockWidthCm, CourseHeightCm), float2(5,5));
float2 q = uv / dims;
// Derivatives before row offset avoid treating an offset jump as huge UV density.
float2 footprint = max(fwidth(q), float2(0.00001,0.00001));
float row = floor(q.y);
q.x += frac(row * 0.5) * 2.0 * saturate(RunningBond);
float2 cell = floor(q);
float2 gap = clamp(max(JointWidthCm,0.0) / dims, 0.0, 0.1);
// Integrated periodic box coverage: analytic pixel-width filtering of joints.
// Average coverage tends to 1-gap at distance, rather than flickering thin lines.
float2 lo = q - footprint * 0.5, hi = q + footprint * 0.5;
float2 ilo = floor(lo)*(1.0-gap) + clamp(frac(lo)-gap*0.5,0.0,1.0-gap);
float2 ihi = floor(hi)*(1.0-gap) + clamp(frac(hi)-gap*0.5,0.0,1.0-gap);
float2 coverage = saturate((ihi-ilo)/footprint);
float stone = coverage.x * coverage.y;
// One deterministic block hash, faded before blocks become subpixel.
float randomBlock = frac(sin(dot(cell,float2(127.1,311.7)))*43758.5453)*2.0-1.0;
float blockFade = 1.0-smoothstep(0.10,0.60,max(footprint.x,footprint.y));
float variation = randomBlock * clamp(BlockVariation,0.0,0.12) * blockFade;
float3 color = lerp(MortarTint,StoneTint*(1.0+variation),stone);
// Two quiet world-space waves: restrained mineral microfinish, not image noise.
// Pixel-footprint fade suppresses unresolved detail during camera movement.
float3 dirA = float3(0.73,0.41,0.55), dirB = float3(-0.31,0.84,0.44);
float invScale = 6.2831853 / max(MicroScaleCm,0.1);
float a = dot(P,dirA)*invScale, b = dot(P,dirB)*invScale*1.71;
float fadeA = 1.0-smoothstep(0.5,2.5,fwidth(a));
float fadeB = 1.0-smoothstep(0.5,2.5,fwidth(b));
float micro = (sin(a)*fadeA + sin(b)*fadeB)*0.5;
float3 grad = (dirA*cos(a)*fadeA + dirB*cos(b)*fadeB)*0.5;
grad -= n*dot(n,grad);
WorldNormal = normalize(n - grad*clamp(MicroNormalStrength,0.0,0.05)*stone*pilotMask);
SurfaceRoughness = clamp(RoughnessBase + micro*clamp(MicroRoughness,0.0,0.06)
    + variation*0.25 + (1.0-stone)*0.035,0.55,0.95);
SurfaceRoughness = lerp(RoughnessBase, SurfaceRoughness, pilotMask);
return saturate(lerp(StoneTint, color, pilotMask));
