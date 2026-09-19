@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
cd /d "C:\Mikdash\Working-5.8\verify-motion-reservation-20260919T145841Z"
cl /nologo /std:c++17 /EHsc /W4 /O2 /I"C:\Mikdash\Working-5.8\MikdashCourtyardV3\Plugins\MikdashRuntime\Source\MikdashRuntime\Public" "C:\Mikdash\Working-5.8\MikdashCourtyardV3\SourceAssets\perf-review\crowd-vat\ResidentMotionReservation01\reproduce.cpp" /Fe:"C:\Mikdash\Working-5.8\verify-motion-reservation-20260919T145841Z\reproduce.exe" /link /SUBSYSTEM:CONSOLE
