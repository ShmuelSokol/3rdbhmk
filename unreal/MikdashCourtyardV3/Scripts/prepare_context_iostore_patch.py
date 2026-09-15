"""Prepare reviewed IoStore/pak input text only. Never runs a process or edits an archive."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime, timezone
from uuid import uuid4

STUDIES = Path("C:/Mikdash/Working-5.8/ContextPatchStudies")
PROJECT = Path(__file__).resolve().parents[1]
PROJECT_NAME = "MikdashCourtyardV3"
CONTAINER = "ContextCoursingV2_1_P"
MASTERS = frozenset({
    "/Game/MikdashV3/JerusalemContext/ContextMaterialsV1/Materials/M_Context_CityWall",
    "/Game/MikdashV3/JerusalemContext/ContextMaterialsV1/Materials/M_Context_Building",
    "/Game/MikdashV3/JerusalemContext/CityFacadeV1/Materials/M_CityFacadeV1",
})
AUDIT_SHA = "091504419cf3faaa97213b259c5d2cf208550e3ee552066a5d3e06fa331c6467"
AUDIT_SCRIPT_SHA = "379c87445600ded87af57532fee67945329ca60fcdb4ace06fea5eb5fa7704ce"
CONTEXT = "/Game/MikdashV3/JerusalemContext/"
DESCENDANTS = frozenset(
    [CONTEXT + "CityDetailV1/Materials/MI_CityDetail_" + name
     for name in ("Canvas", "CityStone", "DarkPlant", "Laundry", "Meleke", "Metal")]
    + [CONTEXT + "CityFacadeV1/Materials/MI_CityFacade_CityStone",
       CONTEXT + "OldCityFacadesV1/Materials/MI_OldCityPlaster",
       CONTEXT + "ContextMaterialsV1/Materials/ExteriorFixesV1/MI_M_Context_Building_ExteriorV1",
       CONTEXT + "ContextMaterialsV1/Materials/ExteriorFixesV1/MI_M_Context_CityWall_ExteriorV1"])
FAMILIES = MASTERS | DESCENDANTS


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_audit(path: Path, project: Path = PROJECT) -> dict:
    """Pinned native discovery only; unknown unrelated instances never expand this set."""
    path = path.resolve()
    require(sha(path) == AUDIT_SHA, "Dependency audit is not the pinned native receipt")
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    require(data.get("schemaVersion") == 1 and data.get("status") == "audited_with_explicit_unknowns", "Dependency audit not passing")
    require(data.get("scriptSha256") == AUDIT_SCRIPT_SHA and
            sha(project / "Scripts/audit_context_patch_dependencies.py") == AUDIT_SCRIPT_SHA,
            "Dependency audit script identity changed")
    for name in ("ownedContext", "mapsUnchanged", "sourceAssetsUnchanged"):
        require(data.get(name) is True, "Dependency audit guard failed: " + name)
    for name in ("mapSaved", "assetSaved"):
        require(data.get(name) is False, "Dependency audit saved content")
    for name in ("errors", "sourceHashUnavailable", "dirtyAfter"):
        require(data.get(name) == [], "Dependency audit has errors/unverified state: " + name)
    require(len(data.get("masters", [])) == 3 and set(data["masters"]) == MASTERS, "Dependency audit roots differ")
    instances = data.get("instances", [])
    require(len(instances) == 10 and {row["package"] for row in instances} == DESCENDANTS, "Dependency audit descendant set differs")
    for row in instances:
        require(row["class"] == "MaterialInstanceConstant" and row["parentChain"][0] == row["package"]
                and row["parentChain"][-1] in MASTERS and row["parent"] == row["parentChain"][1], "Unverified material parent chain")
    registry = data.get("registry", {})
    require(registry.get("discoveryMethodsAgree") is True and registry.get("isLoadingAssetsAfterWait") is False,
            "Dependency discovery incomplete")
    for name in ("descendantsFromParentTags", "descendantsFromChildAPI"):
        require(len(registry.get(name, [])) == 10 and set(registry[name]) == DESCENDANTS, "Dependency discovery set differs")
    before, after = data.get("sourceHashesBefore", {}), data.get("sourceHashesAfter", {})
    require(set(before) == FAMILIES and before == after, "Dependency audit requires exactly 13 unchanged source hashes")
    for package, expected in after.items():
        require(sha(project / "Content" / (package[6:] + ".uasset")) == expected, "Audited source changed: " + package)
    return {"receipt": str(path), "receiptSha256": AUDIT_SHA, "scriptSha256": AUDIT_SCRIPT_SHA,
            "packages": sorted(FAMILIES), "sourceHashes": after,
            "scope": "Pinned 3 masters plus 10 discovered descendants; static permutation unknowns retained; unrelated unknown-parent instances excluded."}


def quoted(value: str | Path) -> str:
    text = str(value).replace("\\", "/")
    require(not any(c in text for c in '\"\r\n\x00'), "Unsafe response-file token")
    return '"' + text + '"'


def inside(path: Path, root: Path) -> Path:
    result = path.resolve()
    try:
        result.relative_to(root.resolve())
    except ValueError:
        raise ValueError("Path escapes isolated study")
    return result


def validate(receipt_path: Path, allowed: list[str], study_root: Path = STUDIES,
             dependency_audit: Path = None) -> dict:
    receipt_path = inside(receipt_path, study_root)
    study = receipt_path.parent
    data = json.loads(receipt_path.read_text(encoding="utf-8-sig"))
    require(data.get("status") == "cook-passed-package-review-pending", "Cook receipt is not successful")
    require(data.get("exitCode") == 0 and data.get("nativeLaunched") is True, "Missing successful native cook exit")
    require(Path(data.get("study", "")).resolve() == study, "Receipt belongs to a different study")
    for field in ("mapsUnchanged", "sourceMastersUnchanged", "contentMetadataUnchanged"):
        require(data.get(field) is True, "Unverified production source preservation: " + field)
    evidence = data.get("logEvidence", {})
    require(evidence.get("successSummary") is True and evidence.get("fatalOrError") is False, "Cook success/error evidence invalid")
    require(evidence.get("mapEvidence") == [] and data.get("cookedMapOutputs") == [], "Cook receipt reports map activity")
    require(bool(allowed) and len(set(allowed)) == len(allowed), "Provide a nonempty, duplicate-free explicit allowlist")
    require(set(allowed) <= FAMILIES, "Package outside the bounded context family set")
    audit = None
    if set(allowed) - MASTERS or data.get("allCoursingFamilies"):
        require(dependency_audit is not None, "Descendants/family cook require an explicit pinned dependency audit")
        audit = validate_audit(dependency_audit)
        require(data.get("dependencyAudit", {}).get("receiptSha256") == audit["receiptSha256"], "Cook did not use the same pinned audit")
        require(data.get("requestedSourceHashesUnchanged") is True and
                data.get("requestedSourceHashesBefore") == audit["sourceHashes"], "Cook lacks preservation proof for all 13 audited packages")
    args = data.get("arguments", [])
    for flag in ("-CookSinglePackage", "-CookSkipRequests", "-SkipZenStore",
                 "-ini:Game:[/Script/UnrealEd.ProjectPackagingSettings]:bShareMaterialShaderCode=False"):
        require(flag in args, "Required isolated/inline cook argument missing: " + flag)
    requested = {package for arg in args if arg.startswith("-Package=") for package in arg.split("=", 1)[1].split("+")}
    if data.get("allCoursingFamilies"):
        require(requested == FAMILIES and set(data.get("requestedPackages", [])) == FAMILIES, "Family cook must request exactly the pinned 13 packages")
    require(set(allowed) <= requested, "Allowlist contains a dependency that was not explicitly requested by this cook")
    require(set(allowed) <= set(evidence.get("cookingPackages", [])), "Allowed master absent from native package census")
    cooked = inside(study / "Cooked" / "Windows", study)
    require(cooked.is_dir(), "Missing isolated Windows cook")
    require(not any(p.suffix.lower() == ".umap" for p in cooked.rglob("*")), "Actual cook contains a map output")
    outputs = data.get("outputs", [])
    require(bool(outputs), "Receipt has no output census")
    inventory: dict[str, dict] = {}
    for row in outputs:
        relative = PurePosixPath(row["path"].replace("\\", "/"))
        require(not relative.is_absolute() and ".." not in relative.parts and ":" not in str(relative), "Unsafe cook output path")
        path = inside(study.joinpath(*relative.parts), cooked)
        key = path.relative_to(study).as_posix()
        require(key.casefold() not in {k.casefold() for k in inventory}, "Duplicate output census path")
        require(path.is_file() and path.stat().st_size == row["bytes"] and sha(path) == row["sha256"], "Cook output changed or missing: " + key)
        inventory[key] = {"path": path, "sha256": row["sha256"], "bytes": row["bytes"]}
    actual = {p.relative_to(study).as_posix() for p in cooked.rglob("*") if p.is_file()}
    require(actual == set(inventory), "Cook output set changed after receipt")
    metadata = {}
    for name in ("packagestore.manifest", "scriptobjects.bin"):
        matches = [v for v in inventory.values() if v["path"].name.casefold() == name]
        require(len(matches) == 1, "Need exactly one fresh cook metadata file: " + name)
        require(matches[0]["bytes"] > 0, "Empty cook metadata file: " + name)
        metadata[name] = matches[0]
    selected, implicit = [], []
    for package in allowed:
        base = cooked / PROJECT_NAME / "Content" / package[6:]
        siblings = sorted(base.parent.glob(base.name + ".*"))
        require(bool(siblings), "No cooked files for allowed master: " + package)
        found = set()
        for path in siblings:
            suffix = path.name[len(base.name):]
            require(suffix in {".uasset", ".uexp", ".ubulk", ".uptnl", ".m.ubulk"}, "Unreviewed package segment: " + path.name)
            found.add(suffix)
            key = path.relative_to(study).as_posix()
            require(key in inventory, "Allowed file missing from verified census")
            row = dict(inventory[key], package=package,
                       mount="../../../" + path.relative_to(cooked).as_posix())
            (implicit if suffix == ".uexp" else selected).append(row)
        require({".uasset", ".uexp"} <= found, "Allowed package requires both .uasset and implicit .uexp")
    return {"study": study, "cooked": cooked, "receipt": receipt_path, "data": data,
            "allowed": allowed, "dependencyAudit": audit, "inventory": inventory, "metadata": metadata,
            "selected": selected, "implicit": implicit}


def emit(plan: dict) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    destination = inside(plan["study"] / ("ContainerRecipeV1-" + stamp + "-" + uuid4().hex[:8]), plan["study"])
    destination.mkdir()  # unique and never overwrites any previous recipe
    containers = destination / "Containers"
    containers.mkdir()
    build_only = destination / "BuildOnly"
    build_only.mkdir()
    response = destination / "IoStoreResponse.txt"
    response.write_text("".join(f'{quoted(row["path"])} {quoted(row["mount"])}\n' for row in plan["selected"]), encoding="utf-8")
    commands = destination / "IoStoreCommands.txt"
    commands.write_text(f'-Output={quoted(containers / (CONTAINER + ".utoc"))} -ContainerName={CONTAINER} -ResponseFile={quoted(response)}\n', encoding="utf-8")
    marker = destination / "ContextCoursingV2-patch-marker.json"
    marker.write_text(json.dumps({"scope": "isolated container experiment; not visual acceptance", "container": CONTAINER,
                                  "allowedPackages": plan["allowed"], "cookReceiptSha256": sha(plan["receipt"])}, indent=2) + "\n", encoding="utf-8")
    pak_response = destination / "PakResponse.txt"
    pak_response.write_text(f'{quoted(marker)} {quoted("../../../" + PROJECT_NAME + "/ContextCoursingV2-patch-marker.json")}\n', encoding="utf-8")
    tool = "C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealPak.exe"
    invocation = [str(PROJECT / (PROJECT_NAME + ".uproject")),
                  "-CreateGlobalContainer=" + str(build_only / "global.utoc"),
                  "-PackageStoreManifest=" + str(plan["metadata"]["packagestore.manifest"]["path"]),
                  "-ScriptObjects=" + str(plan["metadata"]["scriptobjects.bin"]["path"]),
                  "-CookedDirectory=" + str(plan["cooked"]), "-Commands=" + str(commands),
                  "-platform=Windows", "-unattended"]
    recipe = {"status": "prepared-offline-native-container-test-pending", "nativeLaunched": False,
              "cookReceipt": str(plan["receipt"]), "cookReceiptSha256": sha(plan["receipt"]),
              "builderSha256": sha(Path(__file__)), "allowedPackages": plan["allowed"],
              "dependencyAudit": plan["dependencyAudit"],
              "ioStoreInputs": plan["selected"], "implicitUexpInputs": plan["implicit"],
              "freshCookMetadata": plan["metadata"],
              "excludedCookOutputs": [key for key, row in plan["inventory"].items()
                                      if row["path"] not in {r["path"] for r in plan["selected"] + plan["implicit"]}],
              "ioStoreInvocation": {"executable": tool, "arguments": invocation},
              "companionPakInvocation": {"executable": tool, "arguments": [str(containers / (CONTAINER + ".pak")), "-Create=" + str(pak_response), "-unattended"]},
              "candidateBundle": [str(containers / (CONTAINER + ext)) for ext in (".pak", ".utoc", ".ucas")],
              "neverDeploy": [str(build_only), "global.*", "AssetRegistry.bin", "DevelopmentAssetRegistry.bin", "*.ushaderbytecode", "ShaderArchive-*"],
              "limitations": "No commands executed. No dependency auto-inclusion. Inputs must be revalidated before native creation; base dependency, encryption/signing, mount priority, package schema and shader rendering compatibility remain unproved. Global files are construction-only."}
    for name in ("IoStoreResponse.txt", "IoStoreCommands.txt", "PakResponse.txt", marker.name):
        recipe.setdefault("preparedFileSha256", {})[name] = sha(destination / name)
    result = destination / "recipe.json"
    result.write_text(json.dumps(recipe, indent=2, default=str) + "\n", encoding="utf-8")
    return result


class RecipeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.study = self.root / "study"
        self.study.mkdir()
        self.receipt = self.study / "receipt.json"
        self.package = sorted(MASTERS)[-1]  # explicit requested master, arbitrary deterministic fixture
        base = "Cooked/Windows/" + PROJECT_NAME
        self.asset = base + "/Content/" + self.package[6:]
        paths = [self.asset + ".uasset", self.asset + ".uexp", self.asset + ".ubulk",
                 base + "/Metadata/packagestore.manifest", base + "/Metadata/scriptobjects.bin",
                 base + "/AssetRegistry.bin", base + "/Content/Dependency.uasset"]
        self.data = {"status": "cook-passed-package-review-pending", "study": str(self.study), "nativeLaunched": True, "exitCode": 0,
                     "mapsUnchanged": True, "sourceMastersUnchanged": True, "contentMetadataUnchanged": True,
                     "cookedMapOutputs": [], "logEvidence": {"successSummary": True, "fatalOrError": False, "mapEvidence": [], "cookingPackages": [self.package]},
                     "arguments": ["-Package=" + self.package, "-CookSinglePackage", "-CookSkipRequests", "-SkipZenStore", "-ini:Game:[/Script/UnrealEd.ProjectPackagingSettings]:bShareMaterialShaderCode=False"], "outputs": []}
        for relative in paths:
            path = self.study / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"synthetic-test-only")
            self.data["outputs"].append({"path": relative, "bytes": path.stat().st_size, "sha256": sha(path)})
        self.save()

    def save(self):
        self.receipt.write_text(json.dumps(self.data), encoding="utf-8")

    def check(self, allowed=None):
        return validate(self.receipt, allowed or [self.package], self.root)

    def test_explicit_segments_and_marker_only_pak(self):
        result = emit(self.check())
        recipe = json.loads(result.read_text())
        response = (result.parent / "IoStoreResponse.txt").read_text()
        self.assertIn("../../../MikdashCourtyardV3/Content/", response)
        self.assertNotIn(".uexp", response)
        self.assertNotIn("Dependency", response)
        self.assertNotIn("AssetRegistry", response)
        self.assertEqual(len(recipe["ioStoreInputs"]), 2)
        self.assertEqual(len(recipe["implicitUexpInputs"]), 1)
        self.assertEqual(len((result.parent / "PakResponse.txt").read_text().splitlines()), 1)
        self.assertFalse(recipe["nativeLaunched"])

    def test_failed_cook(self):
        self.data["status"] = "failed"; self.save()
        with self.assertRaises(ValueError): self.check()

    def test_empty_outputs(self):
        self.data["outputs"] = []; self.save()
        with self.assertRaises(ValueError): self.check()

    def test_map_receipt(self):
        self.data["cookedMapOutputs"] = ["Map.umap"]; self.save()
        with self.assertRaises(ValueError): self.check()

    def test_unlisted_map_on_disk(self):
        (self.study / "Cooked/Windows/Map.umap").write_bytes(b"map")
        with self.assertRaises(ValueError): self.check()

    def test_changed_implicit_companion(self):
        (self.study / (self.asset + ".uexp")).write_bytes(b"changed")
        with self.assertRaises(ValueError): self.check()

    def test_missing_fresh_metadata(self):
        row = next(r for r in self.data["outputs"] if r["path"].endswith("scriptobjects.bin"))
        (self.study / row["path"]).unlink()
        self.data["outputs"].remove(row); self.save()
        with self.assertRaises(ValueError): self.check()

    def test_master_not_requested(self):
        with self.assertRaises(ValueError): self.check([next(p for p in MASTERS if p != self.package)])

    def test_dependency_not_allowed(self):
        with self.assertRaises(ValueError): self.check(["/Game/Dependency"])

    def test_descendant_requires_explicit_audit(self):
        with self.assertRaises(ValueError): self.check([next(iter(DESCENDANTS))])

    def test_unpinned_audit_refused(self):
        with self.assertRaises(ValueError): validate_audit(self.receipt)

    def test_path_escape(self):
        self.data["outputs"][0]["path"] = "../outside.uasset"; self.save()
        with self.assertRaises(ValueError): self.check()

    def test_changed_source_evidence(self):
        self.data["mapsUnchanged"] = False; self.save()
        with self.assertRaises(ValueError): self.check()

    def test_response_injection(self):
        with self.assertRaises(ValueError): quoted('bad"\n-Create=other')


class AuditTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.project = Path(temp.name)
        script = self.project / "Scripts/audit_context_patch_dependencies.py"
        script.parent.mkdir()
        script.write_text("# synthetic audit identity\n")
        self.script_sha = sha(script)
        hashes = {}
        for package in FAMILIES:
            source = self.project / "Content" / (package[6:] + ".uasset")
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_bytes(package.encode())
            hashes[package] = sha(source)
        root = sorted(MASTERS)[0]
        self.data = {"schemaVersion": 1, "status": "audited_with_explicit_unknowns", "scriptSha256": self.script_sha,
                     "masters": sorted(MASTERS), "instances": [{"package": p, "class": "MaterialInstanceConstant",
                     "parent": root, "parentChain": [p, root]} for p in sorted(DESCENDANTS)],
                     "ownedContext": True, "mapsUnchanged": True, "sourceAssetsUnchanged": True,
                     "mapSaved": False, "assetSaved": False, "errors": [], "sourceHashUnavailable": [], "dirtyAfter": [],
                     "sourceHashesBefore": hashes, "sourceHashesAfter": dict(hashes),
                     "registry": {"discoveryMethodsAgree": True, "isLoadingAssetsAfterWait": False,
                                  "descendantsFromParentTags": sorted(DESCENDANTS), "descendantsFromChildAPI": sorted(DESCENDANTS)}}
        self.receipt = self.project / "audit.json"

    def check(self):
        self.receipt.write_text(json.dumps(self.data))
        with patch.dict(globals(), AUDIT_SHA=sha(self.receipt), AUDIT_SCRIPT_SHA=self.script_sha):
            return validate_audit(self.receipt, self.project)

    def test_exact_thirteen_sources_pass(self):
        self.assertEqual(set(self.check()["packages"]), FAMILIES)
        self.assertEqual(len(FAMILIES), 13)

    def test_changed_source_refused(self):
        (self.project / "Content" / (sorted(FAMILIES)[0][6:] + ".uasset")).write_bytes(b"changed")
        with self.assertRaises(ValueError): self.check()

    def test_wrong_root_refused(self):
        self.data["masters"][0] = "/Game/UnknownMaster"
        with self.assertRaises(ValueError): self.check()

    def test_unknown_descendant_refused(self):
        self.data["instances"][0]["package"] = "/Game/UnknownInstance"
        with self.assertRaises(ValueError): self.check()

    def test_failed_audit_refused(self):
        self.data["status"] = "refused_or_failed"
        with self.assertRaises(ValueError): self.check()

    def test_changed_script_refused(self):
        (self.project / "Scripts/audit_context_patch_dependencies.py").write_text("changed")
        with self.assertRaises(ValueError): self.check()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--allow-package", action="append", default=[], choices=sorted(FAMILIES))
    parser.add_argument("--dependency-audit", type=Path)
    parser.add_argument("--validate-audit", type=Path, help="Validate pinned receipt/script/current 13 source hashes; print JSON only")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(cls) for cls in (RecipeTests, AuditTests))
        return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1
    if args.validate_audit:
        try:
            print(json.dumps(validate_audit(args.validate_audit)))
        except (ValueError, KeyError, OSError, TypeError) as error:
            parser.exit(1, "Refused: " + str(error) + "\n")
        return 0
    if not args.receipt or not args.allow_package:
        parser.error("--receipt and explicit --allow-package are required")
    try:
        result = emit(validate(args.receipt, args.allow_package, dependency_audit=args.dependency_audit))
    except (ValueError, KeyError, OSError, TypeError) as error:
        parser.exit(1, "Refused: " + str(error) + "\n")
    print(json.dumps({"recipe": str(result), "nativeLaunched": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
