@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 exit /b 1
cd /d "%~dp0"
if not exist build mkdir build
cl /nologo /std:c++14 /EHsc /W4 /WX /I"..\..\..\Plugins\MikdashRuntime\Source\MikdashRuntime\Public" test_surface_routing.cpp /Fo"build\test_surface_routing.obj" /Fe"build\test_surface_routing.exe"
if errorlevel 1 exit /b 1
build\test_surface_routing.exe
exit /b %errorlevel%
