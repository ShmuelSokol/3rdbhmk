"""Analytical counterexamples for the observed HISM/current-custom-data path.

This models world translation and heading only, not VAT deformation, pixels or
actual recorded agent trajectories. It is not a production fix or visual gate.
"""
import argparse
from dataclasses import dataclass
import json
import math
from pathlib import Path


@dataclass(frozen=True)
class Anchor:
    time: float
    position: tuple
    velocity: tuple
    heading: float
    horizon: float = 0.2


def vertex(state, time, local=(0., 0.)):
    dt = min(state.horizon, max(-0.25, time - state.time))
    angle = math.radians(state.heading)
    rotated = (math.cos(angle) * local[0] - math.sin(angle) * local[1],
               math.sin(angle) * local[0] + math.cos(angle) * local[1])
    return tuple(state.position[i] + state.velocity[i] * dt + rotated[i] for i in range(2))


def audit():
    previous_time, update_time = 0.1 - 1 / 60, 0.1
    old = Anchor(0., (0., 0.), (100., 0.), 0.)
    origin = vertex(old, update_time)
    cases = [
        ('constant-motion-reanchor-control', Anchor(update_time, origin, (100., 0.), 0.), (20., 0.)),
        ('right-angle-turn-root', Anchor(update_time, origin, (0., 100.), 90.), (0., 0.)),
        ('right-angle-turn-offset-vertex', Anchor(update_time, origin, (0., 100.), 90.), (20., 0.)),
        ('stop-root', Anchor(update_time, origin, (0., 0.), 0.), (0., 0.)),
    ]
    results = []
    for name, current, local in cases:
        actual = vertex(old, previous_time, local)
        reconstructed = vertex(current, previous_time, local)
        # A complete preceding state selects the appropriate interval. A real
        # shader also needs to compensate the current instance basis and retain
        # old VAT phase/blend/rate data; this model does not implement that.
        selected = old if previous_time < current.time else current
        history = vertex(selected, previous_time, local)
        error = math.dist(actual, reconstructed)
        assert math.dist(actual, history) < 1e-10
        assert error < 1e-10 if name.endswith('control') else error > 1.
        results.append(dict(case=name, localVertexCm=local, previousWorldCm=actual,
                            currentStateReconstructionCm=reconstructed,
                            reconstructionErrorCm=error, fullPreviousStateModelErrorCm=math.dist(actual, history)))
    return dict(status='analytical-counterexamples-not-native-fix', updateTime=update_time,
                previousFrameTime=previous_time, frameSeconds=1/60, walkSpeedCmPerSecond=100,
                cases=results, limitations=[
                    'Synthetic transitions, not measured live agent history',
                    'No VAT deformation, blend transitions, shader implementation or rendered comparison',
                    'Full history model is a requirement illustration, not an adopted fix',
                    'Actual turn sizes/frequency must be measured before attributing visible smearing'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = audit()
    with args.out.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2)
        handle.write('\n')
    print(json.dumps(result, indent=2))
