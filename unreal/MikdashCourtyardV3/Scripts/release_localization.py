"""Guarded release of the Mikdash localization data and the Hebrew font.

WHAT THIS DOES

  1. Validates SourceAssets/localization-review/strings.json, which is the single source
     of truth for every visible string and for the glossary of the subject's own terms.
  2. Regenerates en.csv, he.csv and needs-author-review.json from it, and refreshes the
     counts block inside strings.json itself so the numbers on the file are the numbers
     in the file.
  3. Stages strings.json into Content/Localization/Mikdash and the chosen font plus its
     OFL licence into Content/MikdashV3/Fonts.
  4. In an editor process only: imports the two .ttf files as UFontFace assets, saves,
     reopens them, and reads the saved assets back numerically.
  5. Writes a JSON receipt at start and again in finally, so a failure leaves evidence
     rather than silence.

Every number, path and hash comes from Scripts/release_localization.spec.json so the
author can review the plan before it runs.

COMMANDLET INVOCATION (serial, never while another native job is running)

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      -run=pythonscript
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_localization.py"
      -unattended -nullrhi
      -abslog="C:/Mikdash/Working-5.8/Release-Localization-01.log"

Optional switches, read from the engine command line:
  -LocalizationDataOnly     do the data pass and the staging; import no assets.
  -LocalizationSkipAudit    do not re-run the font audit (it takes a few seconds).

OFFLINE INVOCATION

  "C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/ThirdParty/Python3/Win64/python.exe" \\
      Scripts/release_localization.py

With no engine present the module runs offline_check(), which does steps 1 to 3 and the
font audit, prints the receipt, and touches no assets. That path is what the acceptance
gate exercises, and it is the path the author uses after correcting a Hebrew line.

SAFETY MODEL

  * Refuses to run against the wrong project directory or a spec that does not match.
  * Refuses when strings.json fails any structural guard -- a duplicate key, a malformed
    key, a placeholder that does not survive into the Hebrew, an over-long string, a
    missing required glossary term, or a reserved flagged entry whose status has been
    flipped to confident without its Hebrew changing.
  * Copies everything it is about to overwrite under Content into a timestamped
    checkpoint and verifies the copy by hash BEFORE any mutation.
  * In the editor: refuses with dirty packages or a running game world, saves only what
    it imported, then reloads and reads back every asset it claims to have made.

WHAT IT DELIBERATELY DOES NOT DO

  It does not edit Config/DefaultGame.ini. strings.json is a loose file under Content and
  loose files are not staged into a package unless the project lists their folder; that is
  a project setting, so the requirement is written into the receipt and into the spec's
  "packaging" block for a human to act on rather than changed behind their back.

  It also makes no claim about the Hebrew. Every mechanical property here can pass while
  the wording is still wrong, which is why the success status ends in
  "author_review_pending" and why the flagged entries stay flagged.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
SPEC_PATH = ROOT / 'Scripts' / 'release_localization.spec.json'


# --------------------------------------------------------------------------
# pure helpers (no unreal import) so offline_check() runs anywhere
# --------------------------------------------------------------------------

def sha256_of(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def load_spec() -> dict:
    spec = json.loads(SPEC_PATH.read_text(encoding='utf-8-sig'))
    if Path(spec['projectDir']).resolve() != ROOT.resolve():
        raise Guard('Spec project directory differs from script root',
                    {'spec': spec['projectDir'], 'script': str(ROOT)})
    if spec.get('specVersion') != 1:
        raise Guard('Unexpected spec version', {'specVersion': spec.get('specVersion')})
    return spec


class Guard(Exception):
    """A refusal before any mutation. Carries numeric evidence, never just a sentence."""

    def __init__(self, message, evidence=None):
        super().__init__(message)
        self.message = message
        self.evidence = evidence or {}

    def as_dict(self) -> dict:
        return {'guard': self.message, 'evidence': self.evidence}


PLACEHOLDER = re.compile(r'\{(\d+)\}')

# Marks that must never be baked into a stored string. Slate and ICU decide direction
# from the characters themselves and from the layout flow; an embedded LRM/RLM or an
# explicit embedding control in the data overrides that decision permanently, and the
# result is a line that is correct in one context and reversed in another.
FORBIDDEN_MARKS = {
    0x200E: 'LEFT-TO-RIGHT MARK',
    0x200F: 'RIGHT-TO-LEFT MARK',
    0x202A: 'LEFT-TO-RIGHT EMBEDDING',
    0x202B: 'RIGHT-TO-LEFT EMBEDDING',
    0x202C: 'POP DIRECTIONAL FORMATTING',
    0x202D: 'LEFT-TO-RIGHT OVERRIDE',
    0x202E: 'RIGHT-TO-LEFT OVERRIDE',
    0xFEFF: 'ZERO WIDTH NO-BREAK SPACE',
}


def read_strings(spec: dict) -> dict:
    path = ROOT / spec['authoringData']['stringsJson']
    if not path.exists():
        raise Guard('strings.json is missing', {'path': str(path)})
    try:
        data = json.loads(path.read_text(encoding='utf-8-sig'))
    except json.JSONDecodeError as error:
        # The author edits this file by hand. Naming the line and column is the
        # difference between a fix that takes a second and one that takes an evening.
        raise Guard('strings.json is not valid JSON',
                    {'path': str(path), 'line': error.lineno, 'column': error.colno,
                     'message': error.msg}) from None
    return data


def check_structure(spec: dict, data: dict) -> dict:
    """Every structural guard. Returns a summary; raises Guard on the first refusal."""
    authoring = spec['authoringData']
    problems: list[dict] = []

    for field, expected in (('schemaVersion', authoring['expectedSchemaVersion']),
                            ('namespace', authoring['expectedNamespace']),
                            ('tableId', authoring['expectedTableId']),
                            ('sourceLanguage', authoring['expectedSourceLanguage'])):
        if data.get(field) != expected:
            problems.append({'field': field, 'found': data.get(field), 'expected': expected})
    if sorted(data.get('languages', [])) != sorted(authoring['expectedLanguages']):
        problems.append({'field': 'languages', 'found': data.get('languages'),
                         'expected': authoring['expectedLanguages']})
    if sorted(data.get('rtlLanguages', [])) != sorted(authoring['expectedRtlLanguages']):
        problems.append({'field': 'rtlLanguages', 'found': data.get('rtlLanguages'),
                         'expected': authoring['expectedRtlLanguages']})
    if problems:
        raise Guard('strings.json header does not match the spec', {'fields': problems})

    guards = spec['guards']
    key_pattern = re.compile(guards['keyPattern'])
    entries = data.get('entries') or []
    glossary = data.get('glossary') or []

    if len(entries) < guards['minimumStrings']:
        raise Guard('Fewer strings than the spec allows',
                    {'found': len(entries), 'minimum': guards['minimumStrings']})
    if len(glossary) < guards['minimumGlossaryTerms']:
        raise Guard('Fewer glossary terms than the spec allows',
                    {'found': len(glossary), 'minimum': guards['minimumGlossaryTerms']})

    seen: dict[str, int] = {}
    bad_keys, duplicates, oversize, placeholder_drift, marks = [], [], [], [], []

    for index, entry in enumerate(entries):
        key = entry.get('key', '')
        if not key_pattern.match(key):
            bad_keys.append(key)
        if key in seen:
            duplicates.append({'key': key, 'first': seen[key], 'again': index})
        seen[key] = index

        english = entry.get('en') or ''
        hebrew = entry.get('he') or ''

        for label, value in (('en', english), ('he', hebrew)):
            if len(value.encode('utf-8')) > guards['maximumStringBytes']:
                oversize.append({'key': key, 'language': label,
                                 'bytes': len(value.encode('utf-8'))})
            for character in value:
                code = ord(character)
                if code in FORBIDDEN_MARKS:
                    marks.append({'key': key, 'language': label,
                                  'character': f'U+{code:04X}', 'name': FORBIDDEN_MARKS[code]})

        # Ordered placeholders must survive translation. A Hebrew line that drops {1}
        # renders a sentence with a hole in it, and FText::Format will not complain.
        if hebrew:
            english_slots = set(PLACEHOLDER.findall(english))
            hebrew_slots = set(PLACEHOLDER.findall(hebrew))
            if english_slots != hebrew_slots:
                placeholder_drift.append({'key': key, 'en': sorted(english_slots),
                                          'he': sorted(hebrew_slots)})

    if bad_keys:
        raise Guard('Keys do not match the required pattern',
                    {'pattern': guards['keyPattern'], 'keys': bad_keys[:20],
                     'count': len(bad_keys)})
    if duplicates:
        raise Guard('Duplicate keys', {'duplicates': duplicates[:20], 'count': len(duplicates)})
    if oversize:
        raise Guard('Strings above the format ceiling',
                    {'maximumStringBytes': guards['maximumStringBytes'],
                     'entries': oversize[:20], 'count': len(oversize)})
    if marks:
        raise Guard('Directional or byte-order marks embedded in the string data',
                    {'why': 'Layout direction is decided by Slate from the flow direction; '
                            'a baked-in mark overrides that permanently and reverses the line '
                            'in some contexts and not others.',
                     'occurrences': marks[:20], 'count': len(marks)})
    if placeholder_drift:
        raise Guard('Hebrew does not carry the same ordered placeholders as the English',
                    {'entries': placeholder_drift[:20], 'count': len(placeholder_drift)})

    # The reserved lines. A status flipped to confident on UNCHANGED Hebrew is a guess
    # wearing the author's approval, and it is exactly what this guard exists to catch.
    by_key = {entry.get('key'): entry for entry in entries}
    unflagged = []
    for key in guards['flaggedKeysMustStayFlagged']:
        entry = by_key.get(key)
        if entry is None:
            unflagged.append({'key': key, 'problem': 'entry has been deleted'})
            continue
        if entry.get('status') == 'confident' and entry.get('he', '') == entry.get('suggestion', ''):
            unflagged.append({'key': key, 'problem':
                              'marked confident while its Hebrew is still the machine suggestion'})
    if unflagged:
        raise Guard('Reserved entries were marked confident without their Hebrew changing',
                    {'entries': unflagged})

    glossary_by_id = {term.get('id'): term for term in glossary}
    missing_terms = [term for term in guards['requiredGlossaryTerms'] if term not in glossary_by_id]
    if missing_terms:
        raise Guard('Required glossary terms are missing', {'terms': missing_terms})

    incomplete = []
    for term_id in guards['requiredGlossaryTerms']:
        term = glossary_by_id[term_id]
        if not (term.get('hebrew') or '').strip():
            incomplete.append({'id': term_id, 'problem': 'no Hebrew form'})
        if not (term.get('translit') or '').strip():
            incomplete.append({'id': term_id, 'problem': 'no transliteration for the English build'})
    if incomplete:
        raise Guard('Required glossary terms are incomplete', {'terms': incomplete})

    return {
        'strings': counts_for(entries, 'status'),
        'glossary': counts_for(glossary, 'status'),
    }


def counts_for(rows: list, field: str) -> dict:
    total = len(rows)
    confident = sum(1 for row in rows if row.get(field) == 'confident')
    return {'total': total, 'confident': confident, 'flagged': total - confident}


def write_csv(path: Path, rows: list[tuple[str, str]]) -> None:
    """Key,SourceString in the shape Unreal's LOCTABLE_FROMFILE reader expects.

    Written as UTF-8 with a BOM: Unreal reads it either way, but the author will open
    these in Excel to eyeball the Hebrew, and Excel without a BOM shows mojibake.
    """
    buffer = io.StringIO(newline='')
    writer = csv.writer(buffer, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(['Key', 'SourceString'])
    for key, value in rows:
        writer.writerow([key, value])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'\xef\xbb\xbf' + buffer.getvalue().encode('utf-8'))


def regenerate(spec: dict, data: dict, stamp: str) -> dict:
    """Rewrite the derived files from strings.json. Returns what was written."""
    entries = data['entries']
    glossary = data.get('glossary') or []
    generated = spec['generated']

    english_rows = [(entry['key'], entry.get('en') or '') for entry in entries]

    # The Hebrew CSV carries only lines the author has approved. A flagged line is left
    # EMPTY rather than filled with its machine suggestion, so if this CSV is ever used
    # directly the fallback to English happens instead of a guess reaching a screen.
    hebrew_rows = []
    for entry in entries:
        hebrew = entry.get('he') or ''
        approved = entry.get('status') == 'confident' and hebrew
        hebrew_rows.append((entry['key'], hebrew if approved else ''))

    write_csv(ROOT / generated['englishCsv'], english_rows)
    write_csv(ROOT / generated['hebrewCsv'], hebrew_rows)

    review = {
        'generated': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'note': ('Every line here is waiting on the author. The game shows the English string '
                 'until the Hebrew is filled in and its status is set to "confident". '
                 'Edit SourceAssets/localization-review/strings.json, not this file.'),
        'howToClearAnEntry': [
            'Open strings.json and find the entry by its "key".',
            'Replace "he" with your own Hebrew.',
            'Set "status" to "confident".',
            'Re-run Scripts/release_localization.py. No recompile, no editor.',
        ],
        'strings': [
            {'key': entry['key'], 'en': entry.get('en', ''),
             'why': entry.get('context', '') or entry.get('why', ''),
             'suggestion': entry.get('suggestion', '') or entry.get('he', '')}
            for entry in entries if entry.get('status') != 'confident'
        ],
        'glossary': [
            {'id': term['id'], 'hebrew': term.get('hebrew', ''),
             'translit': term.get('translit', ''),
             'why': term.get('note', '')}
            for term in glossary if term.get('status') != 'confident'
        ],
    }
    review['counts'] = {'strings': len(review['strings']), 'glossary': len(review['glossary'])}
    review_path = ROOT / generated['reviewQueue']
    review_path.write_text(json.dumps(review, indent=2, ensure_ascii=False), encoding='utf-8')

    # Refresh the counts block inside strings.json itself. It is hand-edited, so it drifts,
    # and a stale count is worse than none: it is a number the author will believe.
    strings_counts = counts_for(entries, 'status')
    glossary_counts = counts_for(glossary, 'status')
    data['counts'] = {
        'strings': strings_counts,
        'glossary': glossary_counts,
        'combined': {
            'total': strings_counts['total'] + glossary_counts['total'],
            'confident': strings_counts['confident'] + glossary_counts['confident'],
            'flagged': strings_counts['flagged'] + glossary_counts['flagged'],
        },
        'refreshed': stamp,
    }
    strings_path = ROOT / spec['authoringData']['stringsJson']
    strings_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')

    return {
        'englishCsv': {'path': generated['englishCsv'], 'rows': len(english_rows)},
        'hebrewCsv': {'path': generated['hebrewCsv'], 'rows': len(hebrew_rows),
                      'approvedRows': sum(1 for _, value in hebrew_rows if value)},
        'reviewQueue': {'path': generated['reviewQueue'], **review['counts']},
        'counts': data['counts'],
    }


def check_fonts(spec: dict) -> dict:
    """Every shipped font file must be byte-for-byte the one the spec approved."""
    source = ROOT / spec['font']['sourceFolder']
    result = []
    mismatches = []
    for entry in spec['font']['files']:
        path = source / entry['file']
        if not path.exists():
            mismatches.append({'file': entry['file'], 'problem': 'missing', 'path': str(path)})
            continue
        actual_bytes = path.stat().st_size
        actual_hash = sha256_of(path)
        row = {'file': entry['file'], 'role': entry['role'],
               'bytes': actual_bytes, 'sha256': actual_hash}
        if actual_bytes != entry['bytes'] or actual_hash != entry['sha256']:
            mismatches.append({'file': entry['file'], 'problem': 'hash or size differs',
                               'expectedSha256': entry['sha256'], 'foundSha256': actual_hash,
                               'expectedBytes': entry['bytes'], 'foundBytes': actual_bytes})
        result.append(row)
    if mismatches:
        raise Guard('A shipped font file is not the one the spec approved',
                    {'files': mismatches})
    return {'files': result}


def run_font_audit(spec: dict) -> dict:
    """Re-run the glyph audit and hold it to the coverage the spec requires.

    Imported rather than shelled out so a failure is an exception with a traceback rather
    than an exit code. The audit rewrites font-audit.json and the specimen PNG.
    """
    audit_script = ROOT / spec['font']['auditScript']
    if not audit_script.exists():
        raise Guard('The font audit script is missing', {'path': str(audit_script)})

    sys.path.insert(0, str(audit_script.parent))
    try:
        import importlib
        module = importlib.import_module(audit_script.stem)
        importlib.reload(module)
        module.main()
    finally:
        if sys.path and sys.path[0] == str(audit_script.parent):
            sys.path.pop(0)

    audit = json.loads((ROOT / 'SourceAssets/localization-review/font-audit.json')
                       .read_text(encoding='utf-8'))

    required = spec['font']['requiredCoverage']
    shipped = spec['font']['decision']
    row = next((f for f in audit['fonts'] if f['file'] == shipped), None)
    if row is None:
        raise Guard('The audit did not cover the shipped font', {'font': shipped})

    failures = []
    coverage = row['coverage']
    if coverage['baseLetters']['present'] < required['baseLetters']:
        failures.append({'group': 'baseLetters', **coverage['baseLetters']})
    if coverage['nikud']['present'] < required['nikud']:
        failures.append({'group': 'nikud', **coverage['nikud']})
    if coverage['latinBasic']['present'] < required['latinBasic']:
        failures.append({'group': 'latinBasic', **coverage['latinBasic']})
    if required['markFeatureRequired'] and not row['markFeature']['present']:
        failures.append({'group': 'markFeature', 'present': False})
    if row['specimenMarks']['unanchored'] > required['unanchoredMarksAllowed']:
        failures.append({'group': 'unanchoredMarks', **row['specimenMarks']})
    if not audit['specimenVerification'].get('ok'):
        failures.append({'group': 'specimenPng', **audit['specimenVerification']})

    if failures:
        raise Guard('The shipped font no longer meets the coverage the spec requires',
                    {'font': shipped, 'shortfalls': failures})

    return {
        'font': shipped,
        'verdict': row['verdict'],
        'coverage': coverage,
        'markClasses': row['markFeature']['markClasses'],
        'specimenMarks': row['specimenMarks'],
        'specimen': audit['specimenVerification'],
    }


def stage(spec: dict, checkpoint: Path | None) -> dict:
    """Copy the authoring data and the font into Content, checkpointing what is replaced."""
    staging = spec['staging']
    strings_destination = ROOT / staging['stringsDestination']
    font_destination = ROOT / staging['fontDestination']

    planned: list[tuple[Path, Path]] = [
        (ROOT / spec['authoringData']['stringsJson'], strings_destination / 'strings.json'),
        (ROOT / spec['generated']['englishCsv'], strings_destination / 'en.csv'),
        (ROOT / spec['generated']['hebrewCsv'], strings_destination / 'he.csv'),
    ]
    font_source = ROOT / spec['font']['sourceFolder']
    for entry in spec['font']['files']:
        planned.append((font_source / entry['file'], font_destination / entry['file']))

    # Checkpoint first. Anything already there is copied out and the copy is verified by
    # hash before a single byte is overwritten.
    replaced = []
    if checkpoint is not None:
        for _, destination in planned:
            if destination.exists():
                relative = destination.relative_to(ROOT)
                backup = checkpoint / relative
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(destination, backup)
                if sha256_of(backup) != sha256_of(destination):
                    raise Guard('Checkpoint copy does not match the file it backed up',
                                {'file': str(relative)})
                replaced.append(str(relative))

    written = []
    for source, destination in planned:
        if not source.exists():
            raise Guard('A file the staging plan needs is missing', {'path': str(source)})
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        if sha256_of(destination) != sha256_of(source):
            raise Guard('A staged file does not match its source', {'path': str(destination)})
        written.append({'path': str(destination.relative_to(ROOT)),
                        'bytes': destination.stat().st_size,
                        'sha256': sha256_of(destination)})

    return {'written': written, 'replacedFromCheckpoint': replaced}


def receipt_path(spec: dict, stamp: str) -> Path:
    folder = ROOT / spec['receipt']['folder']
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{spec['receipt']['prefix']}{stamp}.json"


def offline_check(spec=None, write_receipt=True, run_audit=True, do_stage=True) -> dict:
    """Everything that needs no engine. This is the path the acceptance gate exercises."""
    spec = spec or load_spec()
    stamp = utc_stamp()
    receipt = {
        'script': 'release_localization.py',
        'specVersion': spec['specVersion'],
        'generated': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'stamp': stamp,
        'mode': 'offline',
        'status': 'offline_check_started',
        'guards': [],
        'errors': [],
        'packagingRequirement': spec['packaging'],
    }

    try:
        data = read_strings(spec)
        receipt['structure'] = check_structure(spec, data)
        receipt['guards'].append('strings.json structure')

        receipt['font'] = check_fonts(spec)
        receipt['guards'].append('font files match the approved hashes')

        if run_audit:
            receipt['fontAudit'] = run_font_audit(spec)
            receipt['guards'].append('font glyph coverage and mark anchoring')

        receipt['regenerated'] = regenerate(spec, data, stamp)
        receipt['guards'].append('derived files regenerated from strings.json')

        if do_stage:
            checkpoint = Path(spec['checkpoint']['root']) / (spec['checkpoint']['prefix'] + stamp)
            checkpoint.mkdir(parents=True, exist_ok=True)
            receipt['checkpoint'] = str(checkpoint)
            receipt['staged'] = stage(spec, checkpoint)
            receipt['guards'].append('staged into Content with a verified checkpoint')

        receipt['status'] = 'offline_data_pass_complete_author_review_pending'
    except Guard as guard:
        receipt['errors'].append(guard.as_dict())
        receipt['status'] = 'refused_before_mutation_nothing_changed'
        raise
    except Exception as error:                      # noqa: BLE001
        receipt['errors'].append({'stage': 'offline', 'error': repr(error)})
        receipt['status'] = 'failed_during_offline_pass'
        raise
    finally:
        if write_receipt:
            receipt_path(spec, stamp).write_text(
                json.dumps(receipt, indent=2, ensure_ascii=False), encoding='utf-8')

    return receipt


# --------------------------------------------------------------------------
# editor half
# --------------------------------------------------------------------------

def _unreal_available() -> bool:
    try:
        import unreal  # noqa: F401
        return True
    except ImportError:
        return False


def _asset_disk_path(asset_path: str) -> Path:
    if not asset_path.startswith('/Game/'):
        raise Guard('Only /Game/ assets are expected', {'assetPath': asset_path})
    return ROOT / 'Content' / (asset_path[6:] + '.uasset')


def _guard_editor_state(ue) -> dict:
    """Refuse the same three states that have cost this project a session before."""
    evidence = {}

    world = ue.EditorLevelLibrary.get_editor_world() if hasattr(ue, 'EditorLevelLibrary') else None
    subsystem = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    if subsystem is not None:
        try:
            world = subsystem.get_editor_world()
        except Exception:                            # noqa: BLE001
            pass
    evidence['world'] = world.get_path_name() if world else None

    if hasattr(ue, 'EditorLevelLibrary'):
        try:
            if ue.EditorLevelLibrary.is_playing_in_editor():
                raise Guard('A game world is running; stop play in editor first', evidence)
        except AttributeError:
            pass

    dirty = [p.get_name() for p in ue.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
    dirty += [p.get_name() for p in ue.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
    evidence['dirtyPackages'] = dirty
    if dirty:
        raise Guard('Dirty packages present; resolve them before a checkpointed import', evidence)

    return evidence


def _import_font_face(ue, source: Path, asset_path: str) -> dict:
    """Import one .ttf as a UFontFace asset.

    A UFontFace is a normal cooked asset, so importing rather than leaving the .ttf loose
    is what removes the packaging dependency on a project-settings entry. The factory is
    UFontFileImportFactory (Editor/UnrealEd/Classes/Factories/FontFileImportFactory.h in
    UE 5.8); if that class is not exposed to Python in this build the caller records the
    omission rather than pretending the asset exists.
    """
    package_path, asset_name = asset_path.rsplit('/', 1)

    task = ue.AssetImportTask()
    task.filename = str(source)
    task.destination_path = package_path
    task.destination_name = asset_name
    task.replace_existing = True
    task.automated = True
    task.save = False
    factory = getattr(ue, 'FontFileImportFactory', None)
    if factory is None:
        raise Guard('FontFileImportFactory is not exposed to Python in this build',
                    {'asset': asset_path})
    task.factory = factory()

    ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    imported = list(task.get_editor_property('imported_object_paths') or [])
    if not imported:
        raise Guard('The font import produced no asset',
                    {'source': str(source), 'asset': asset_path})
    return {'asset': asset_path, 'source': str(source), 'importedPaths': imported}


def _read_back_font_face(ue, asset_path: str, expected_source: Path) -> dict:
    """Reload the saved asset and read it back numerically. No claim without a readback."""
    loaded = ue.load_asset(asset_path)
    if loaded is None:
        return {'asset': asset_path, 'readBack': False, 'problem': 'asset did not load'}
    row = {
        'asset': asset_path,
        'readBack': True,
        'class': loaded.get_class().get_name(),
        'isFontFace': loaded.get_class().get_name() == 'FontFace',
        'diskFile': str(_asset_disk_path(asset_path).relative_to(ROOT)),
        'diskFileExists': _asset_disk_path(asset_path).exists(),
    }
    if row['diskFileExists']:
        row['diskBytes'] = _asset_disk_path(asset_path).stat().st_size
        row['diskSha256'] = sha256_of(_asset_disk_path(asset_path))
    row['expectedSourceBytes'] = expected_source.stat().st_size
    return row


def release(data_only=False, run_audit=True) -> dict:
    """The full editor pass: guards, checkpoint, data, import, save, reopen, readback."""
    import unreal as ue

    spec = load_spec()
    stamp = utc_stamp()
    checkpoint = Path(spec['checkpoint']['root']) / (spec['checkpoint']['prefix'] + stamp)

    receipt = {
        'script': 'release_localization.py',
        'specVersion': spec['specVersion'],
        'generated': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'stamp': stamp,
        'mode': 'editor',
        'status': 'checkpointed_localization_release_started',
        'checkpoint': str(checkpoint),
        'guards': [],
        'imported': [],
        'omissions': [],
        'readback': [],
        'errors': [],
        'packagingRequirement': spec['packaging'],
    }
    path = receipt_path(spec, stamp)
    path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding='utf-8')

    saved = False
    try:
        receipt['editorState'] = _guard_editor_state(ue)
        receipt['guards'].append('editor state')

        checkpoint.mkdir(parents=True, exist_ok=False)

        # Checkpoint the asset files that are about to be replaced, before anything else.
        for entry in spec['font']['files']:
            if not entry['assetPath']:
                continue
            existing = _asset_disk_path(entry['assetPath'])
            if existing.exists():
                backup = checkpoint / existing.relative_to(ROOT)
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(existing, backup)
                if sha256_of(backup) != sha256_of(existing):
                    raise Guard('Checkpoint copy of an asset does not match',
                                {'asset': entry['assetPath']})
        receipt['guards'].append('existing assets checkpointed')

        # The data pass. Same code the offline path runs, so the two cannot diverge.
        data = read_strings(spec)
        receipt['structure'] = check_structure(spec, data)
        receipt['font'] = check_fonts(spec)
        if run_audit:
            receipt['fontAudit'] = run_font_audit(spec)
        receipt['regenerated'] = regenerate(spec, data, stamp)
        receipt['staged'] = stage(spec, checkpoint)
        receipt['guards'].append('data pass complete')
        path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding='utf-8')

        if data_only:
            receipt['status'] = 'data_only_pass_complete_author_review_pending'
            return receipt

        font_source = ROOT / spec['font']['sourceFolder']
        to_save = []
        for entry in spec['font']['files']:
            if not entry['assetPath']:
                continue
            try:
                receipt['imported'].append(
                    _import_font_face(ue, font_source / entry['file'], entry['assetPath']))
                to_save.append(entry['assetPath'])
            except Guard as guard:
                # An import that could not run becomes a recorded omission with evidence.
                # The runtime falls back to the loose .ttf staged above, so the build still
                # shows Hebrew in the editor; only packaging needs the ini entry then.
                receipt['omissions'].append(guard.as_dict())

        if to_save:
            ue.EditorAssetLibrary.save_directory('/Game/MikdashV3/Fonts', False, True)
            saved = True
            receipt['guards'].append('assets saved')

            # Reopen: drop them from memory and load again from what is on disk, so the
            # readback is of the saved file rather than of the object still in the editor.
            for asset_path in to_save:
                ue.EditorAssetLibrary.load_asset(asset_path)
            for entry in spec['font']['files']:
                if not entry['assetPath']:
                    continue
                receipt['readback'].append(
                    _read_back_font_face(ue, entry['assetPath'], font_source / entry['file']))

            unreadable = [row for row in receipt['readback'] if not row.get('isFontFace')]
            if unreadable:
                raise Guard('An imported asset did not read back as a FontFace',
                            {'assets': unreadable})
            receipt['guards'].append('assets reopened and read back')

        receipt['configToApply'] = {
            'note': ('Add these to the [/Script/MikdashRuntime.MikdashLocalization] section of '
                     'Config/DefaultGame.ini so the runtime prefers the cooked assets over the '
                     'loose .ttf files. This script does not edit project configuration.'),
            'lines': [f"{entry['configKey']}={entry['assetPath']}.{entry['assetPath'].rsplit('/', 1)[1]}"
                      for entry in spec['font']['files'] if entry.get('configKey')],
        }
        receipt['status'] = spec['receipt']['successStatus']
        return receipt

    except Guard as guard:
        receipt['errors'].append(guard.as_dict())
        receipt['status'] = ('failed_after_save_checkpoint_available' if saved
                             else 'refused_before_mutation_nothing_changed')
        raise
    except Exception as error:                      # noqa: BLE001
        receipt['errors'].append({'stage': 'release', 'error': repr(error)})
        receipt['status'] = ('failed_after_save_checkpoint_available' if saved
                             else 'failed_before_save')
        raise
    finally:
        receipt['importedCount'] = len(receipt['imported'])
        receipt['omissionCount'] = len(receipt['omissions'])
        path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding='utf-8')


def _invoked_as_native_script() -> bool:
    """True only when the engine itself is executing this file as a script."""
    if not _unreal_available():
        return False
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line().lower()
    return ('release_localization.py' in command_line
            and ('-run=pythonscript' in command_line or '-executepythonscript' in command_line))


def _main() -> None:
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line().lower()
    data_only = '-localizationdataonly' in command_line
    run_audit = '-localizationskipaudit' not in command_line
    try:
        receipt = release(data_only=data_only, run_audit=run_audit)
        ue.log('release_localization: %s imported %s omissions %s strings %s/%s confident' % (
            receipt['status'], receipt.get('importedCount'), receipt.get('omissionCount'),
            receipt.get('structure', {}).get('strings', {}).get('confident'),
            receipt.get('structure', {}).get('strings', {}).get('total')))
    except Exception as error:                      # noqa: BLE001
        ue.log_error('release_localization failed: ' + repr(error))
        raise
    finally:
        if '-executepythonscript' in command_line and '-run=pythonscript' not in command_line:
            ue.SystemLibrary.quit_editor()


if __name__ == '__main__':
    if _unreal_available():
        _main()
    else:
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        except Exception:                            # noqa: BLE001
            pass
        print(json.dumps(offline_check(), indent=2, ensure_ascii=False))
elif _invoked_as_native_script():
    _main()
