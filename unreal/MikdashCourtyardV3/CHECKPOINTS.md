# Playable checkpoints

Shmuel asked (9 Sep 2026) for periodic production-ready builds: *"certain checkpoints where
you finish up a build and get it ready for production... so if you run into a session limit
and you lose all your work, at least I have some updated version of the game to use."*

A checkpoint is a **playable Windows build of the shipping map, produced from whatever state
the project is in at that moment**. It is not a release and it is not acceptance — it is
insurance, so no session limit can ever cost more than the work since the last one.

## Making one

```powershell
powershell -File C:\Mikdash\Working-5.8\MikdashCourtyardV3\Checkpoint-Build.ps1 -Label cp03
```

That is the whole command. The script:

1. **Waits** (default 60 min) for a free native slot — no editor, no UAT, no game running,
   and ≥6 GB free. It never fights the feature agents for the machine; if the slot never
   frees it prints `DEFERRED:` and exits 2 without cooking.
2. **Refuses** if Candidate48 is no longer the configured `GameDefaultMap` — a build of the
   wrong map is worse than no build.
3. Cooks with the only recipe that has ever passed on this box (see below).
4. Archives to `C:\Mikdash\Builds\Checkpoint-<label>-<stamp>\Windows`.
5. Hashes the **child** exe at `Windows\MikdashCourtyardV3\Binaries\Win64\` — not the
   launcher stub in the archive root, which is not the binary that changes.
6. Runs a **bounded startup smoke**: launches windowed at 1280×720, waits for a real window
   handle, records peak working set, then closes it.
7. Writes `checkpoint-receipt.json` into the job folder and copies it to
   `SourceAssets/build-review/checkpoint-<label>-<stamp>.json`.

Terminal status values, in order of goodness:

| status | meaning |
| --- | --- |
| `checkpoint_playable` | cooked, archived, and a window actually opened |
| `cook_passed_but_window_never_opened` | binary exists, did not start — do not hand it over |
| `failed` | cook failed, or a map file changed underneath the cook |
| `DEFERRED:` (exit 2) | machine was busy; nothing was cooked, nothing was harmed |

## Why the cook line is what it is

Every flag was paid for by a failed attempt:

- `cmd /c RunUAT.bat`, run from `Engine\Build\BatchFiles` — **never** from Git Bash, which
  mangles the `-project=` path.
- `-cookprocesscount=1` — a second cook process OOMs this 16 GB box.
- `-maxPartitionSize=1800000000` — keeps pak parts under GitHub's 2 GB per-asset limit, so
  a checkpoint can be published without re-cooking.
- `-clientconfig=Development` — Shipping strips the console and the on-screen diagnostics
  that make a preview build useful to look at.
- Hash the child exe, not the stub.
- **Call RunUAT by its full path, from a generated `.bat`.** This machine has
  `NoDefaultCurrentDirectoryInExePath=1`, so cmd will not run an executable it finds only in
  the current directory: `if exist RunUAT.bat` prints FOUND and `call RunUAT.bat` on the next
  line prints *"is not recognized as an internal or external command"*. Every historical
  `Astra-Cook-*.ps1` in this tree calls it bare after a `Push-Location` and would fail today
  for two independent reasons - that, and the fact that `Push-Location` never changes the
  process working directory cmd inherits. Passing the command as a `cmd /c` string does not
  work either: PowerShell re-quotes any argument containing spaces and cmd then strips quotes
  from an already-quoted path, collapsing the nesting. The `.bat` avoids all of it.
- **`-NeedGB 4.0`, not 6.** This box idles near 4.3 GB free of 15.9. A 6 GB gate never opens;
  it just waits the full timeout and DEFERs.

## Cadence

The heartbeat fires a checkpoint when **both** are true: none has been produced in ~2 hours,
and at least one substantive change has landed since the last one. A checkpoint of unchanged
bytes is just an hour of machine time.

## Handing one to Shmuel

Give the archive path and the status line. For a build he can download rather than run off
the local disk, the publish path is unchanged from Windows12: three ZIPs (App + Data01 +
Data02) preserving internal paths, extracted into one folder, launched from the **root**
`MikdashCourtyardV3.exe`. See `HANDOFF-WINDOWS12-PUBLISHED-20260909.md`.
