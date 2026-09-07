# Kotel access source study

Authored offline only. Original illustrative future access geometry, not surveyed current infrastructure or a prediction. Source OSM-derived coordinates retain existing alignment and attribution. Original wall/plaza/map assets are untouched.

Generate with Python 3.12 and Shapely 2.1.2: `python Scripts/create_mount_access.py`. The script reads the existing `FutureMountV1/.tools` dependency directory without modifying it. Run `python SourceAssets/mount-access/check_mount_access.py` for independent stdlib mesh/route checks.

Four editable OBJ meshes and the authoritative `mount-access.mesh.json` are provided. JSON is native east/south/up centimetres with identity actor transforms. OBJ is east/north/up metres with explicit normals and planar metre-scale UVs. Verify a native adapter's scale, handedness and bounds before placing; do not use an unchecked default OBJ import transform.

The straight staircase has 82 risers of 17.469512cm, 35cm treads, six250cm resting landings,300cm clear width,110cm side guards and a500cm top landing. It runs east from(-18400,19972.432518,-1432.5) to(-13230,19972.432518,0). Original Temple12x25cm outer-gateway stairs and courtyard300cm datum remain unchanged.

**Review hold:** `KotelPlaza_Infill_REVIEW_ONLY` and `KotelApproach_LowerApron_REVIEW_ONLY` intentionally occupy the protected plaza or its buffer as additive proposals. Their overlap is quantified separately in the spec; they must not be presented as zero-overlap geometry. The terrain-following infill is15cm thick with its top3cm above retained terrain. It leaves a201cm wall guard and preserves the source terrain slopes. The apron blends the existing plaza terrain to the lower stair landing; it has no accessibility certification.

The stair/parapet footprint is outside both200cm buffers (minimum distance609.5116cm to protected polygons). Its enclosure crossing is approximately(-13709.15355,19972.432518). A retained wall may block that crossing: main root must inspect and scope any future-scenario opening, with no Kotel or whole-wall-batch removal. Scene obstacles are not cleared by these offline checks. Solid stair footings reachZ-2100cm; check external terrain/building intersections and native walking before integration. The assembly has no roof; actual scene headroom remains unverified.

Read `mount-access-spec.json`, `mount-access-checks.json` and `independent-validation.json` for exact placement, per-tread editable parameters, source hashes, explicit overlapping-area treatment and native acceptance gates. No Unreal script, Content asset, map mutation or git operation was performed here.
