"""Import the authored tiling water normal as a texture asset, so release_water.py can use it.

release_water.py resolves materials.water.normalCandidates by LOADING existing assets, and its
spec now lists /Game/MikdashV3/MaterialReview/MikdashWaterV1/Textures/T_Water_Normal first.
Nothing creates that asset, so this commandlet does — one texture, verified by readback.

    UnrealEditor-Cmd.exe <uproject> -run=pythonscript
        -script=C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/import_water_normal.py
        -unattended -nullrhi -abslog=<unique>

Never opens or touches a map. Refuses if the asset already exists (nothing to redo).
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import unreal as ue

ROOT = Path(r"C:\Mikdash\Working-5.8\MikdashCourtyardV3")
PNG = ROOT / "SourceAssets/water-review/textures/T_Water_Normal.png"
DEST_PATH = "/Game/MikdashV3/MaterialReview/MikdashWaterV1/Textures"
DEST_NAME = "T_Water_Normal"
RECEIPTS = ROOT / "SourceAssets/water-review"

stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
rec = {"status": "started", "stamp": stamp, "png": str(PNG), "asset": f"{DEST_PATH}/{DEST_NAME}"}
try:
    assert Path(ue.Paths.project_dir()).resolve() == ROOT.resolve(), "wrong project"
    assert PNG.exists(), "water normal PNG missing; run create_water_normal.py"
    rec["pngSha256"] = hashlib.sha256(PNG.read_bytes()).hexdigest()
    if ue.EditorAssetLibrary.does_asset_exist(rec["asset"]):
        rec["status"] = "already_exists_nothing_done"
        raise SystemExit

    task = ue.AssetImportTask()
    task.set_editor_property("filename", str(PNG))
    task.set_editor_property("destination_path", DEST_PATH)
    task.set_editor_property("destination_name", DEST_NAME)
    task.set_editor_property("automated", True)
    task.set_editor_property("save", True)
    task.set_editor_property("replace_existing", False)
    ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

    tex = ue.EditorAssetLibrary.load_asset(rec["asset"])
    assert tex, "import produced no asset"
    # A normal map: linear, TC_Normalmap. Setters may return False even when they work,
    # so every value is read back below rather than trusted.
    tex.set_editor_property("srgb", False)
    tex.set_editor_property("compression_settings", ue.TextureCompressionSettings.TC_NORMALMAP)
    tex.set_editor_property("flip_green_channel", False)
    assert ue.EditorAssetLibrary.save_loaded_asset(tex), "save failed (check for a zombie UnrealEditor)"

    again = ue.EditorAssetLibrary.load_asset(rec["asset"])
    rec["readback"] = {
        "srgb": again.get_editor_property("srgb"),
        "compression": str(again.get_editor_property("compression_settings")),
        "flipGreen": again.get_editor_property("flip_green_channel"),
        "sizeX": again.blueprint_get_size_x(), "sizeY": again.blueprint_get_size_y(),
    }
    assert rec["readback"]["srgb"] is False, "srgb readback"
    assert "NORMALMAP" in rec["readback"]["compression"].upper(), "compression readback"
    rec["status"] = "imported_saved_readback_ok"
except SystemExit:
    pass
except Exception as exc:  # noqa: BLE001
    rec.update(status="failed", error=str(exc) or repr(exc))
finally:
    RECEIPTS.mkdir(parents=True, exist_ok=True)
    (RECEIPTS / f"water-normal-import-{stamp}.json").write_text(json.dumps(rec, indent=2, default=str), encoding="utf-8")
    ue.log("MIKDASH_WATER_NORMAL " + json.dumps({"status": rec["status"], "error": rec.get("error")}))
