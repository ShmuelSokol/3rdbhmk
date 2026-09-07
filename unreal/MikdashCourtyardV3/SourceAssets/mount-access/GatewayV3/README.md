# GatewayV3: measured exterior approach audit

No new geometry is needed. This package deliberately contains an empty mesh list to prevent duplicated measured stairs.

- East: existing SM0261–0272 provide twelve25cm risers,50cm runs and500cm width from platformZ0 to gatewayZ300. Existing access landing, threshold and vestibule are contiguous.
- North: existing SM0364–0373 provide ten approach terrace risers fromZ0 to250; existing SM0357–0363 provide seven more to gatewayZ425. The first flight is800cm wide; the second is500cm wide. Runs are50cm and rises25cm throughout.
- South: existing SM0465–0474 provide ten approach terrace risers fromZ0 to250; existing SM0458–0464 provide seven more to gatewayZ425. These mirror the north dimensions.
- West: source element21 is a continuous Western court wall, retained within SM2629 outer-envelope union. There is no measured Outer W gateway. Preserve it; use the exterior platform to reach the existing gates.

Each approach has200cm of generatedZ0 platform coverage immediately before its first riser. All three approach footprints clear both protected200cm wall/plaza buffers. Generator checks use the actual platform triangle union, source model boxes, exported manifest bounds and historical native inventory identities. Exact complete asset names, source indices, bounds and historical component paths are in `gateway-approach-audit.json`.

Generate: `python Scripts/create_gateway_approaches.py` with Python3.12 and the existing read-only Shapely dependency directory. Independent check: `python SourceAssets/mount-access/GatewayV3/check_gateway_v3.py`.

`native-route-inputs.json` contains ordered floor-level waypoint inputs for future continuous native tests. These are not teleport instructions or walking receipts. The north/south audit ends at the425cm vestibule; interior transitions to the300cm court, live headroom and collision remain separate checks. Historical native component identities must be reconciled in the current future map. Frozen V1 and OpeningV2 files are hash-verified unchanged. No native execution, map change, geometry duplication or git operation occurred.
