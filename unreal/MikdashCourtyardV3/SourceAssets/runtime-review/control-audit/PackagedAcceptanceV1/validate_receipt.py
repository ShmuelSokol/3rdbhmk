"""Offline validation of one packaged-release evidence receipt; never executes game."""
import argparse
import hashlib
import json
from pathlib import Path

CHECKS = ('startup_no_capture', 'physical_p_pause_resume', 'physical_escape_pause_resume',
          'physical_wasd_arrows', 'physical_mouse_look_release', 'physical_stairs_roundtrip',
          'pause_stops_motion', 'focus_return_stays_paused', 'mute_audible', 'mute_fresh_process_persistence')


def validate(data, fixture_mode=False):
    errors = []
    def require(condition, message):
        if not condition:
            errors.append(message)
    require(isinstance(data, dict), 'Receipt must be an object')
    if not isinstance(data, dict):
        return errors
    fixture = data.get('testFixture') is True
    require(fixture == fixture_mode, 'Fixture and real acceptance modes must not mix')
    require(data.get('schema') == 'PackagedAcceptanceV1', 'Wrong schema')
    build = data.get('build', {})
    if not isinstance(build, dict):
        return errors + ['Build must be an object']
    bid = build.get('id')
    digest = build.get('sha256', '')
    require(isinstance(bid, str) and bool(bid.strip()), 'Build id required')
    require(isinstance(digest, str) and len(digest) == 64 and all(c in '0123456789abcdef' for c in digest), 'Build SHA256 required')
    require(build.get('artifactKind') == 'complete_release_archive', 'Hash must identify complete release archive')
    require(isinstance(build.get('bytes'), int) and not isinstance(build.get('bytes'), bool) and build['bytes'] > 0, 'Archive byte size required')
    require(bool(build.get('artifactPath')), 'Archive path required')
    evidence = data.get('evidence', {})
    require(isinstance(evidence, dict), 'Evidence registry required')
    if not isinstance(evidence, dict):
        return errors
    for key, item in evidence.items():
        if not isinstance(item, dict):
            errors.append('Invalid evidence: ' + key)
            continue
        require(item.get('buildId') == bid and item.get('buildSha256') == digest, 'Mixed build evidence: ' + key)
        h = item.get('sha256', '')
        require(isinstance(h, str) and len(h) == 64 and all(c in '0123456789abcdef' for c in h), 'Evidence hash invalid: ' + key)
        require(bool(item.get('path')), 'Evidence path required: ' + key)
    def refs(value, label):
        require(isinstance(value, list) and bool(value) and all(isinstance(r, str) and r in evidence for r in value), 'Evidence references required: ' + label)
    provenance = data.get('provenance', {})
    if not isinstance(provenance, dict):
        return errors + ['Provenance must be an object']
    require(provenance.get('buildId') == bid and provenance.get('buildSha256') == digest, 'Mixed provenance build')
    require(provenance.get('cookMode') == 'fresh_cook' and provenance.get('cookExitCode') == 0, 'Successful fresh cook required')
    require(provenance.get('packageExitCode') == 0, 'Successful package required')
    require(bool(provenance.get('mapPackage')), 'Map package required')
    mh = provenance.get('mapSha256', '')
    require(isinstance(mh, str) and len(mh) == 64 and all(c in '0123456789abcdef' for c in mh), 'Map SHA256 required')
    refs(provenance.get('evidenceRefs'), 'provenance')
    sessions = data.get('sessions', [])
    require(isinstance(sessions, list) and bool(sessions), 'Physical sessions required')
    by_id = {}
    if isinstance(sessions, list):
        for session in sessions:
            if not isinstance(session, dict):
                errors.append('Invalid session'); continue
            sid = session.get('id')
            require(isinstance(sid, str) and bool(sid) and sid not in by_id, 'Unique session id required')
            if isinstance(sid, str):
                by_id[sid] = session
            require(session.get('buildId') == bid and session.get('buildSha256') == digest, 'Mixed session build')
            require(session.get('environment') == 'packaged' and session.get('inputOrigin') == 'physical_operator', 'Physical packaged session required')
            require(bool(session.get('operator')) and bool(session.get('startedUtc')) and bool(session.get('processId')), 'Operator, time and process identity required')
            duration = session.get('durationSeconds')
            require(isinstance(duration, (int, float)) and not isinstance(duration, bool) and 0 < duration <= 180, 'Session must be bounded to 180 seconds')
            require(session.get('closedCleanly') is True, 'Clean session shutdown required')
            refs(session.get('evidenceRefs'), 'session')
    checks = data.get('checks', {})
    if not isinstance(checks, dict):
        return errors + ['Checks must be an object']
    for name in CHECKS:
        check = checks.get(name, {})
        if not isinstance(check, dict):
            errors.append('Invalid check: ' + name); continue
        require(check.get('result') == 'pass', 'Missing/pass required: ' + name)
        require(check.get('buildId') == bid and check.get('buildSha256') == digest, 'Mixed check build: ' + name)
        require(check.get('inputOrigin') == 'physical_operator', 'Synthetic cannot pass: ' + name)
        require(check.get('sessionId') in by_id, 'Known session required: ' + name)
        require(bool(check.get('observation')) and bool(check.get('eventUtc')), 'Explicit observation and timestamp required: ' + name)
        refs(check.get('evidenceRefs'), name)
    persistence = checks.get('mute_fresh_process_persistence', {})
    if isinstance(persistence, dict):
        before, after = by_id.get(persistence.get('beforeSessionId')), by_id.get(persistence.get('sessionId'))
        require(before is not None and after is not None and before.get('processId') != after.get('processId'), 'Mute persistence requires two distinct fresh processes')
        require(persistence.get('observedBeforeAnyToggle') is True, 'Persistence must be observed before any fresh-process toggle')
    return errors


def verify_files(data, base):
    errors = []
    entries = [('build', data.get('build', {}))] + list(data.get('evidence', {}).items())
    for label, item in entries:
        path = Path(item.get('artifactPath' if label == 'build' else 'path', ''))
        if not path.is_absolute():
            path = base / path
        try:
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != item.get('sha256'):
                errors.append('File hash mismatch: ' + label)
            if label == 'build' and len(raw) != item.get('bytes'):
                errors.append('Archive byte size mismatch')
        except OSError as exc:
            errors.append('Cannot read ' + label + ': ' + str(exc))
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('receipt', type=Path)
    args = parser.parse_args()
    data = json.loads(args.receipt.read_text(encoding='utf-8-sig'))
    errors = validate(data)
    if not errors:
        errors += verify_files(data, args.receipt.parent)
    print(json.dumps({'status': 'rejected' if errors else 'receipt_complete_requires_evidence_review',
                      'errors': errors, 'limitation': 'Integrity/schema validation cannot authenticate physical actions or judge captured behavior.'}, indent=2))
    raise SystemExit(1 if errors else 0)


if __name__ == '__main__':
    main()
