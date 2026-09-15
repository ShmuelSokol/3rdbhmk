# Photo pawn visibility — narrowed production change, 15 September 2026

Coordinator acceptance: Editor and Game compiled/linked the final production policy.
`probe-20260915T161445204Z.json` passed all 18 native phases, including an additional
session and Enter while already active. Only CharacterMesh0 was selected; exact flags,
unselected primitives and the pawn camera restored, and all 20 source maps stayed
unchanged. The final native R1 PNG was visually inspected and both rods are absent.
See `production-acceptance.json`. The child executable is c1f56f30...; this is still
the isolated runtime copy with cp24 cooked assets, not a full new cooked release.

Two native GPU probes identify the rods as the possessed player's world-space body:

- `probe20260915T160532280Z`: hiding the pawn's two skeletal components removes the
  rods. Both exact prior flags restore, PNG/readback/normal exit pass, all20 maps unchanged.
- `probe20260915T160700832Z`: hiding only CharacterMesh0 removes both rods while
  FirstPersonMesh retains its original visible/hidden flags. Restoration and normal
  exit pass, all20 maps unchanged.

CharacterMesh0 is FirstPersonPrimitiveType WorldSpaceRepresentation (2), ownerNoSee
true. The normal pawn camera uses first-person parameters; the detached photo camera
changes the view actor, exposing the world-space representation. The first-person
component (type1) alone was not needed for the rod removal.

The production fix selects by the UE rendering role, not by Manny or component name:
on successful photo Enter, hide only the possessed pawn's own skeletal components
whose FirstPersonPrimitiveType is WorldSpaceRepresentation. Preserve the exact visible
and hidden-in-game flags in valid weak component references, then restore on Exit,
Deinitialize and re-entry. Changes do not propagate to attachments. FirstPerson/type1,
None/ordinary skeletal components, residents, static components, owner flags,
first-person settings, collision and materials remain unchanged. A pawn without a
world-space body is a valid no-op. No saved assets/maps are changed.

PreparePhotoPawnVisibility and RestorePhotoPawnVisibility now run without diagnostic
flags. The diagnostics observe this same production selection by default. Only with
`-MikdashPhotoPawnDiagnostic` may the optional
`-MikdashPhotoPawnComponent=<exact case-sensitive name>` override selection for a
component isolation experiment. A missing/ambiguous explicit name hides nothing and
records failure. A missing pawn records diagnostic failure, including if possession
is lost during the automatic settling period. Normal photo mode still permits a
controller without a pawn and simply has no body to hide.

Per-phase JSON/log remains opt-in and records possessed and observed pawn identity,
actual camera/view target, all pawn primitives, mesh/full transforms/quaternion/scale,
bounds, attachments, first-person and owner visibility flags, exact selected baseline
flags, restored flags and invalid weak references. Receipts are
`Saved/Diagnostics/PhotoPawn-<UTC ticks>-NNN.json`; `diagnosticSelected` names the
selected component readback field for compatibility with the first probes.

Automatic native test: `-MikdashPhotoPawnDiagnostic -MikdashPhotoPawnProbe`, with no
component override, exercises the production path. It waits for a pawn (120s bound),
settles 15s, enters photo mode, waits3s, requests TakePhoto(2), allows >=5s PNG flush
(30s timeout), exits, and allows1s for the restored camera blend. It then performs one
additional Enter/Exit cycle including a repeated Enter while active, waits for the
restored view, saves the final receipt and requests normal exit. No second screenshot
is needed for the restoration cycle. Final fields: probePhotoPath, probePhotoExists,
probePassed, visibilityPolicy. The policy must be
`possessed-pawn-world-space-representation` for production-path acceptance.
The screenshot normally lands in `<launch directory>/MikdashPhotos/*.png`.

Only a successfully saved final receipt permits automatic exit. Failed PNG request,
missing PNG, missing pawn or readback failure is recorded explicitly. If the final
write fails, the error stays in the log and the external watchdog must stop the run.
The interactive diagnostic alone never launches the automated sequence or exits.

Source is restricted to MikdashPhotoMode.h/.cpp. Initial diagnostic Editor and Game
compilation passed before both native component probes. This narrowed default policy,
missing-pawn correction and extended re-entry probe now need serial verification and
fresh GPU/readback acceptance before being called shipped. Worker launches no
Unreal/UBT job and performs no publication.
