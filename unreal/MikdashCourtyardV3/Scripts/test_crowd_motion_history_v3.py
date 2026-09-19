"""Evaluate the actual stock-node builder against independent vertex trajectories.

Synthetic VAT clips isolate history/phase/blend/basis maths. Native texture
sampling, velocity-buffer output and temporal-AA appearance remain engine gates.
"""
import math
import random
import struct
import unittest
from types import SimpleNamespace
from crowd_motion_history_v3 import previous_wpo


def f32(v):
    return struct.unpack('f', struct.pack('f', v))[0]


def rot(v, degrees, scale=1):
    a = math.radians(degrees)
    c, s = math.cos(a), math.sin(a)
    return ((c*v[0]-s*v[1])*scale, (s*v[0]+c*v[1])*scale, v[2]*scale)


def walk(phase):
    return (8*math.sin(2*math.pi*phase), 4*math.cos(2*math.pi*phase), 3*math.sin(4*math.pi*phase))


def idle(time, offset):
    phase = (offset + time*(.92+.16*((offset*7.31) % 1))/3.2) % 1
    return (math.sin(2*math.pi*phase), 2*math.cos(2*math.pi*phase), math.sin(4*math.pi*phase))


def delta(state, time, offset):
    dt = max(-.25, min(state['horizon'], time-state['time']))
    w = walk((state['phase']+dt*state['rate']) % 1)
    i = idle(time, offset)
    blend = max(0, min(1, (time-state['switch'])/.25))
    alpha = blend if state['idle'] else 1-blend
    return tuple(a*(1-alpha)+b*alpha for a, b in zip(w, i))


def world(state, time, rest, offset, scale):
    local = tuple(a+b for a, b in zip(rest, delta(state, time, offset)))
    body = rot(local, state['heading'], scale)
    dt = max(-.25, min(state['horizon'], time-state['time']))
    return tuple(p+b+v*dt for p, b, v in zip(state['position'], body, state['velocity']))


class Node:
    def __init__(self, kind, *args):
        self.kind, self.args, self.inputs, self.props = kind, args, {}, {}

    def set_editor_property(self, name, value):
        self.props[name] = value


class Graph:
    def __init__(self, state, previous, updated, rest, offset, scale):
        kinds = ('Add', 'Subtract', 'Multiply', 'Divide', 'AppendVector', 'Frac', 'Saturate',
                 'OneMinus', 'PreSkinnedPosition', 'If', 'PreviousFrameSwitch')
        self.ue = SimpleNamespace(**{'MaterialExpression'+k: k for k in kinds})
        self.state, self.rest, self.offset, self.scale = state, rest, offset, scale
        old = previous
        angle = math.radians(old['heading']-state['heading'])
        self.data = dict(zip(range(11, 26), map(f32, [
            *(a-b for a, b in zip(old['position'], state['position'])), math.cos(angle), math.sin(angle),
            old['phase'], old['time'], old['rate'], *old['velocity'], old['idle'], old['switch'], old['horizon'], updated])))

    def make(self, kind): return Node(kind)
    def custom_data(self, index, *_): return Node('Constant', self.data[index])
    def const(self, value): return Node('Constant', value)
    def op(self, kind, a, b): return Node(kind, a, b)
    def unary(self, kind, a): return Node(kind, a)
    def mask(self, value, c): return Node('Mask', value, 'rgb'.index(c))
    def clamp(self, value, lo, hi): return Node('Clamp', value, lo, hi)
    def lerp(self, a, b, weight): return Node('Lerp', a, b, weight)
    def link(self, src, dst, names): dst.inputs[names[0]] = src

    def evaluate(self, root, time, previous_frame):
        cache = {}
        def componentwise(a, b, fn):
            if isinstance(a, tuple) or isinstance(b, tuple):
                a = a if isinstance(a, tuple) else (a,)*len(b)
                b = b if isinstance(b, tuple) else (b,)*len(a)
                return tuple(fn(x, y) for x, y in zip(a, b))
            return fn(a, b)
        def ev(n):
            if n in cache: return cache[n]
            k = n.kind
            if k == 'Constant': out = n.args[0]
            elif k == 'Time': out = time
            elif k == 'PreSkinnedPosition': out = self.rest
            elif k == 'Current':
                absolute = world(self.state, time, self.rest, self.offset, self.scale)
                basis = rot(self.rest, self.state['heading'], self.scale)
                out = tuple(a-p-b for a, p, b in zip(absolute, self.state['position'], basis))
            elif k == 'Idle': out = idle(time, self.offset)
            elif k == 'Walk': out = walk(ev(n.args[0]))
            elif k == 'World': out = rot(ev(n.args[0]), self.state['heading'], self.scale)
            elif k == 'Mask': out = ev(n.args[0])[n.args[1]]
            elif k == 'PreviousFrameSwitch': out = ev(n.inputs['Previous Frame' if previous_frame else 'Current Frame'])
            elif k == 'If':
                a, b = ev(n.inputs['A']), ev(n.inputs['B'])
                out = ev(n.inputs['A < B' if a < b else 'A > B' if a > b else 'A == B'])
            elif k == 'Clamp': out = max(ev(n.args[1]), min(ev(n.args[2]), ev(n.args[0])))
            elif k == 'Lerp':
                a, b, w = map(ev, n.args)
                out = componentwise(a, b, lambda x, y: x*(1-w)+y*w)
            elif k == 'Frac': out = ev(n.args[0]) % 1
            elif k == 'Saturate': out = max(0, min(1, ev(n.args[0])))
            elif k == 'OneMinus': out = 1-ev(n.args[0])
            elif k == 'AppendVector':
                a, b = map(ev, n.args)
                out = (a if isinstance(a, tuple) else (a,))+(b if isinstance(b, tuple) else (b,))
            else:
                fn = {'Add': lambda a,b:a+b, 'Subtract': lambda a,b:a-b,
                      'Multiply': lambda a,b:a*b, 'Divide': lambda a,b:a/b}[k]
                out = componentwise(*map(ev, n.args), fn)
            cache[n] = out
            return out
        return ev(root)


class HistoryTests(unittest.TestCase):
    def check_case(self, old, current, updated, times, scale=1):
        rest, offset = (20., -13., 135.), f32(.381)
        # Stored anchor/velocity/animation floats reproduce the actual GPU inputs.
        for state in (old, current):
            for key in ('time', 'phase', 'rate', 'horizon', 'switch'):
                state[key] = f32(state[key])
            state['velocity'] = tuple(map(f32, state['velocity']))
        g = Graph(current, old, updated, rest, offset, scale)
        root = previous_wpo(g, Node('Time'), {}, Node('Current'),
                            lambda phase, *_: Node('Walk', phase), g.const(72), None,
                            {'WalkPositionTexture': None}, g.const((1.,1.,1.)), g.const((0.,0.,0.)),
                            Node('Idle'), g.const(.25), g.const(.25), lambda n: Node('World', n))
        base = tuple(a+b for a, b in zip(current['position'], rot(rest, current['heading'], scale)))
        for time in times:
            for previous in (False, True):
                result = tuple(a+b for a, b in zip(base, g.evaluate(root, time, previous)))
                selected = old if previous and time < f32(updated) else current
                expected = world(selected, time, rest, offset, scale)
                self.assertLess(math.dist(result, expected), .0002, (time, previous, result, expected))

    def test_turn_stop_start_idle_heading_and_stale_snapshot(self):
        for old_idle, new_idle in ((0,0), (0,1), (1,0), (1,1)):
            for angle in (0, 67.5, 90, -179, 359):
                old = dict(position=(10000.,-38000.,468.), velocity=(90.,12.,2.) if not old_idle else (0.,0.,0.),
                           heading=37., time=2., phase=.27, rate=.65, horizon=.7, switch=1.98, idle=old_idle)
                current = dict(position=(10012.,-37998.,468.3), velocity=(-12.,90.,-2.) if not new_idle else (0.,0.,0.),
                               heading=37.+angle, time=2.2, phase=.41, rate=.72, horizon=.2, switch=2.2, idle=new_idle)
                self.check_case(old, current, 2.2, [2.2-1/30, f32(2.2), 2.2+1/30, 2.8], 1.08)

    def test_idle_heading_without_reanchor_uses_visit_time(self):
        old = dict(position=(0.,0.,0.), velocity=(0.,0.,0.), heading=0., time=1., phase=.2,
                   rate=0., horizon=0., switch=-1000., idle=1)
        current = dict(old, heading=90.)
        self.check_case(old, current, 3., [2.99, 3., 3.1])

    def test_initial_history_and_long_uptime(self):
        for updated in (0., 10000., 60000.):
            state = dict(position=(50000., 10000., 300.), velocity=(0.,0.,0.), heading=-90., time=updated,
                         phase=.93, rate=0., horizon=0., switch=-1000., idle=1)
            self.check_case(dict(state), dict(state), updated, [updated-1/60, updated, updated+1/60], .92)

    def test_random_transitions(self):
        rng = random.Random(19)
        for _ in range(150):
            def state():
                return dict(position=tuple(rng.uniform(-50000,50000) for _ in range(3)),
                            velocity=tuple(rng.uniform(-100,100) for _ in range(3)), heading=rng.uniform(-360,360),
                            time=rng.uniform(19.3,20), phase=rng.random(), rate=rng.random(), horizon=rng.uniform(0,.7),
                            switch=rng.uniform(19.5,20), idle=rng.randrange(2))
            old, current = state(), state()
            # Updates move locally; same precision and range as native anchor deltas.
            current['position'] = tuple(p+rng.uniform(-70,70) for p in old['position'])
            self.check_case(old, current, 20., [19.967,20.,20.033], rng.uniform(.92,1.08))


if __name__ == '__main__':
    unittest.main()
