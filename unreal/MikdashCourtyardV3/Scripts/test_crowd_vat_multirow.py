"""Evaluate the production stock-node clip builder on synthetic packed VATs.

Uses the installed AnimToTexture layout: frame block starts at frame*rows*width;
vertex UV is ((column+.5)/width,(row+.5)/(frames*rows)). Not a GPU visual test.
"""
import ast
import itertools
import math
from pathlib import Path
import struct
from types import SimpleNamespace
import unittest


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


class Graph:
    def __init__(self, width, rows, frames):
        self.width, self.rows, self.frames = width, rows, frames

    def const(self, value): return f32(value)
    def mask(self, value, channel): return value['rg'.index(channel)]
    def unary(self, kind, value):
        return f32(math.floor(value) if kind == 'Floor' else value-math.floor(value))
    def op(self, kind, a, b):
        if kind == 'AppendVector': return (a, b)
        return f32({'Add': lambda: a+b, 'Multiply': lambda: a*b, 'Divide': lambda: a/b}[kind]())
    def tex(self, _name, _texture, uv):
        col = int((uv[0] % 1)*self.width)
        row = int((uv[1] % 1)*(self.frames*self.rows))
        return (row//self.rows, row % self.rows, col)
    def lerp(self, a, b, weight):
        return tuple(f32(x+(y-x)*weight) for x,y in zip(a,b))


class MultirowTest(unittest.TestCase):
    def test_actual_stock_clip_across_row_and_loop_boundaries(self):
        tree = ast.parse(Path(__file__).with_name('create_crowd_vat_v2.py').read_text(encoding='utf-8-sig'))
        master = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'build_master_v2')
        clip = next(n for n in master.body if isinstance(n, ast.FunctionDef) and n.name == 'clip')
        code = compile(ast.fix_missing_locations(ast.Module(body=[clip], type_ignores=[])), '<actual-clip>', 'exec')
        for frames, rows, width in itertools.product((72, 192), (1, 2, 3, 6, 11, 21), (3308, 4096)):
            g = Graph(width, rows, frames)
            env = dict(g=g, A='Add', M='Multiply', D='Divide', E=SimpleNamespace(
                MaterialExpressionFloor='Floor', MaterialExpressionFrac='Frac', MaterialExpressionAppendVector='AppendVector'))
            exec(code, env)
            for vertex in (0, width-1, width*rows-1, width*(rows//2)+17):
                if vertex >= rows*width: continue
                row, col = divmod(vertex, width)
                uv = (f32(f32(.5/width)+f32(col/width)),
                      f32(f32(.5/(frames*rows))+f32(row/(frames*rows))))
                for frame in (0, 1, frames//2, frames-1):
                    for alpha in (0., .25, .5, .75):
                        phase = f32((frame+alpha)/frames)
                        fr = f32(phase*frames); lo = math.floor(fr); weight = fr-lo
                        actual = env['clip'](phase, frames, uv, 'synthetic', None)
                        expected = (f32(lo+(((lo+1) % frames)-lo)*weight), row, col)
                        self.assertEqual(actual, expected, (frames, rows, vertex, phase))


if __name__ == '__main__':
    unittest.main()
