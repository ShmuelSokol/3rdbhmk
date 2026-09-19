Offline experiment using the runtime group, point, segment, flow and spacing math.
Fixture values come from zones.json SHA256
b6445cc2460f52d2dbf45158fff86d7e12a4a382c7af03a7f6c03249233d3b24.
The three metric zones keep their coordinates in selected48. Global person ranges
use the native 10000-request apportionment. Native ground and obstacle checks are
omitted, so this is neither runtime acceptance nor a proof of zone capacity.

From a Visual Studio developer prompt in the project root:

    cl /std:c++17 /EHsc /O2 /I Plugins/MikdashRuntime/Source/MikdashRuntime/Public Scripts/study_crowd_packing.cpp /Fe:study.exe
    study.exe

Mode0 preserves the random candidate order; Mode1/2 sort the same1024 candidates
along the longer polygon axis in opposite directions. The plaza Mode0 reproduces
native239/271 and all15264 trials. Its refused cohorts are eight triples and two
groups of four, not singles. Sorting candidates improves some results but does
not fill all three zones. No candidate-sorting change was adopted in runtime.

The resulting implementation direction is whole-cohort fallback to another enabled
visitor zone after preferred placement fails, retaining every placement guard and
reporting preferred versus final distribution. Existing successful placements stay.
