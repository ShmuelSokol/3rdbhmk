"""Measure sampled live group movement; recovery counters alone do not prove travel."""
import argparse
import hashlib
import json
import math
from pathlib import Path
from analyze_crowd_motion_audit import fields


def analyze(path):
    raw = path.read_bytes()
    snapshots, agents, spacing, group_states = {}, {}, [], {}
    for line in raw.decode('utf-8-sig').splitlines():
        if 'CrowdSpacingV1 time=' in line:
            row = {k: float(v) for k, v in fields(line).items()}
            assert all(math.isfinite(v) for v in row.values()) and row['minimum'] >= 0
            assert 0 <= row['a'] < row['b'] < 48
            assert not spacing or row['time'] > spacing[-1]['time']
            spacing.append(row)
        if 'CrowdReviewV1 snapshot=' in line:
            row = {k: float(v) for k, v in fields(line).items()}
            index = int(row['snapshot'])
            assert index not in snapshots
            assert all(math.isfinite(v) for v in row.values())
            snapshots[index] = row
        elif 'CrowdReviewAgentV1 snapshot=' in line:
            row = {k: float(v) for k, v in fields(line).items()}
            index, agent = int(row['snapshot']), int(row['agent'])
            assert agent not in agents.setdefault(index, {})
            assert all(math.isfinite(v) for v in row.values())
            agents[index][agent] = row
        elif 'CrowdReviewGroupV1 snapshot=' in line:
            row = {k: float(v) for k, v in fields(line).items()}
            index, group = int(row['snapshot']), int(row['group'])
            assert all(math.isfinite(v) for v in row.values())
            assert group not in group_states.setdefault(index, {})
            assert row['mode'] in (0, 1, 2) and row['detours'] in (0, 1)
            group_states[index][group] = row
    assert sorted(snapshots) == sorted(agents) == list(range(13)), 'Expected0..60s snapshots'
    minimum_separation = float('inf')
    for index, summary in snapshots.items():
        rows = agents[index]
        assert sorted(rows) == list(range(48)) and summary['seeded'] == 48
        assert summary['walking'] == sum(not row['idle'] for row in rows.values())
        assert summary['resumeSeconds'] == 12 and summary['yawOffset'] == -90
        if index:
            assert 4.95 <= summary['time'] - snapshots[index - 1]['time'] <= 5.05
            assert summary['resumes'] >= snapshots[index - 1]['resumes']
        pairs = [(math.hypot(rows[a]['x'] - rows[b]['x'], rows[a]['y'] - rows[b]['y']), a, b)
                 for a in rows for b in rows if a < b]
        closest = min(pairs)
        summary['minimumSampledSeparationCm'] = closest[0]
        summary['closestAgents'] = list(closest[1:])
        minimum_separation = min(minimum_separation, closest[0])
    motion = []
    for agent in range(48):
        rows = [agents[i][agent] for i in range(13)]
        identity = {(r['group'], r['member'], r['standing']) for r in rows}
        assert len(identity) == 1, 'Visitor identity changed'
        distances = [math.hypot(b['x'] - a['x'], b['y'] - a['y']) for a, b in zip(rows, rows[1:])]
        motion.append(dict(agent=agent, group=int(rows[0]['group']), member=int(rows[0]['member']),
                           standing=bool(rows[0]['standing']), sampledTravelCm=sum(distances),
                           maxFiveSecondDisplacementCm=max(distances),
                           finalThirtySecondsSampledTravelCm=sum(distances[6:])))
    groups = []
    for group in sorted({r['group'] for r in motion if r['group'] >= 0}):
        members = [r for r in motion if r['group'] == group]
        leader = next(r for r in members if r['member'] == 0)
        groups.append(dict(group=group, members=len(members), standing=leader['standing'],
                           leaderSampledTravelCm=leader['sampledTravelCm'],
                           leaderFinalThirtySecondsTravelCm=leader['finalThirtySecondsSampledTravelCm']))
    if group_states:
        assert sorted(group_states) == list(range(13))
        for index, rows in group_states.items():
            assert sorted(rows) == [g['group'] for g in groups]
            for group, row in rows.items():
                leader = next(a for a in agents[index].values() if a['group'] == group and a['member'] == 0)
                assert row['identity'] == leader['agent']
    return dict(status='live-recovery-measured-not-navigation-acceptance',
                groupSteeringSnapshots=[row for index in sorted(group_states) for _, row in sorted(group_states[index].items())],
                frameSpacing=dict(samples=len(spacing), minimum=min(spacing, key=lambda r: r['minimum']) if spacing else None,
                                  limitation='Frame samples do not independently prove between-frame clearance'),
                logSha256=hashlib.sha256(raw).hexdigest(), snapshots=list(snapshots.values()),
                agents=motion, groups=groups, minimumSampledSeparationCm=minimum_separation,
                limitations=['Five-second displacement undercounts curved travel and misses between-sample collisions.',
                             'Resume counters indicate attempts, not successful recovery; inspect measured group travel.',
                             'One authored zone,48 people,two body variants; no main-map or performance acceptance.'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    args = parser.parse_args()
    report = analyze(args.folder / 'runtime.log')
    with (args.folder / 'recovery-analysis.json').open('x', encoding='utf-8') as handle:
        json.dump(report, handle, indent=2)
        handle.write('\n')
    print(json.dumps({k: report[k] for k in ('status', 'minimumSampledSeparationCm', 'groups')}, indent=2))
