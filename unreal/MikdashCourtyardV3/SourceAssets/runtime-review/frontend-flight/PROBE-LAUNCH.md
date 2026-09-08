# Bounded live probe with isolated progress

Launch a fresh UnrealEditor.exe with the project and main map, real RHI, no other native job. Use `-ExecCmds="py C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_frontend_probe_entry.py"`, `-unattended -NoSplash`, a unique absolute log path, and optionally `-DirectIntroFlight -TestIntegratedSystems -TestTour`.

Supply a unique alphanumeric test prefix beginning AstraProbe_ in BOTH switches (replace STAMP consistently):

```
-TestSavePrefix=AstraProbe_STAMP
-ini:Game:[/Script/MikdashRuntime.MikdashSaveSystem]:SlotNamePrefix=AstraProbe_STAMP,[/Script/MikdashRuntime.MikdashSettingsSubsystem]:SaveSlot=AstraProbe_STAMP_Settings
```

The probe validates live slot names, preserves non-test save-file hashes, requests PIE teardown and exits. No default config or normal visitor save slot is edited. Config-only properties cannot be read/written through Python CDO access; raw names still report protected. The command-line config syntax was checked against installed ConfigCacheIni.cpp and exercised in the successful143744 receipt. Keep test saves as isolated evidence; don't sweep the SaveGames directory.

The180-second watchdog starts when Python begins, after editor startup. The coordinator must additionally bound editor startup and check the owned PID/log if no receipt appears. The entry wrapper quits on preflight exceptions before the normal tick watchdog exists. Read status/errors/pieEnded/mapBytesUnchanged/saveIsolation from the final receipt, not only process exit. Tour APIs are not route-walking, audio, rendering, packaged-content or physical-keyboard acceptance.
