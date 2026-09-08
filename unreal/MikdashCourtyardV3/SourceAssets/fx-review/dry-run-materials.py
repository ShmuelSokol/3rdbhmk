"""Offline dry run of release_fx.py's material graph builders against a fake `unreal`.

    python SourceAssets/fx-review/dry-run-materials.py

Not a substitute for the editor, and it does not prove a material compiles. What it
does prove, in under a second instead of a ten-minute commandlet run, is the three
things that have actually gone wrong while writing this feature:

  1. every builder runs to completion without an exception;
  2. every connection asks for a pin name the expression really has (the PINS table
     below is the 5.8 pin list, including the ones that bite: Clamp's first input is
     "None", TextureSample's is "UVs", Noise's is "World Position"); and
  3. every master material ends up exposing all six parameters AMikdashFXDirector
     writes each frame - a material missing one is not an error anywhere, it just
     silently stops responding to the actor.

Run it after any edit to the build_*_material functions in Scripts/release_fx.py.
Deleting a line from PINS also exercises the optional-node fallback path: dropping
MaterialExpressionDepthFade should still come out green, because the smoke material
is required to ship without the softening rather than fail the run.
"""
import sys, types, importlib.util
from pathlib import Path

PINS = {
    'MaterialExpressionTextureCoordinate': [],
    'MaterialExpressionComponentMask': ['Input'],
    'MaterialExpressionOneMinus': [''],
    'MaterialExpressionLinearInterpolate': ['A', 'B', 'Alpha'],
    'MaterialExpressionAppendVector': ['A', 'B'],
    'MaterialExpressionTime': [],
    'MaterialExpressionScalarParameter': [],
    'MaterialExpressionVectorParameter': [],
    'MaterialExpressionMultiply': ['A', 'B'],
    'MaterialExpressionAdd': ['A', 'B'],
    'MaterialExpressionSubtract': ['A', 'B'],
    'MaterialExpressionDivide': ['A', 'B'],
    'MaterialExpressionMax': ['A', 'B'],
    'MaterialExpressionConstant': [],
    'MaterialExpressionConstant3Vector': [],
    'MaterialExpressionClamp': ['None', 'Min', 'Max'],
    'MaterialExpressionTextureSampleParameter2D': ['UVs', 'Tex', 'ApplyViewMipBias'],
    'MaterialExpressionAbs': [''],
    'MaterialExpressionPower': ['Base', 'Exponent'],
    'MaterialExpressionDotProduct': ['A', 'B'],
    'MaterialExpressionCameraVectorWS': [],
    'MaterialExpressionVertexNormalWS': [],
    'MaterialExpressionDepthFade': ['InOpacity', 'FadeDistance'],
}

created = []


class FakeClass(object):
    def __init__(self, name):
        self.name = name
        self.__name__ = name

    def get_name(self):
        return self.name


class Node(object):
    def __init__(self, cls):
        self._cls = cls
        self.props = {}

    def set_editor_property(self, k, v):
        self.props[k] = v

    def get_class(self):
        return FakeClass(self._cls)

    def get_path_name(self):
        return '/Fake/' + self._cls


class ML(object):
    @staticmethod
    def create_material_expression(material, cls, x=0, y=0):
        n = Node(cls.__name__)
        created.append(n)
        return n

    @staticmethod
    def get_material_expression_input_names(expr):
        if expr._cls not in PINS:
            raise AssertionError('mock has no pin list for ' + expr._cls)
        return PINS[expr._cls]

    @staticmethod
    def get_material_expression_output_names(expr):
        return ['', 'R', 'G', 'B', 'A']

    @staticmethod
    def connect_material_expressions(src, out, tgt, pin):
        if pin not in PINS[tgt._cls] and PINS[tgt._cls]:
            return False
        return True

    @staticmethod
    def connect_material_property(src, out, prop):
        return True


class LinearColor(object):
    def __init__(self, r, g, b, a=1.0):
        self.r, self.g, self.b, self.a = r, g, b, a


class MaterialProperty(object):
    MP_EMISSIVE_COLOR = 'MP_EMISSIVE_COLOR'
    MP_OPACITY = 'MP_OPACITY'
    MP_REFRACTION = 'MP_REFRACTION'


class MaterialSamplerType(object):
    SAMPLERTYPE_MASKS = 'SAMPLERTYPE_MASKS'
    SAMPLERTYPE_LINEAR_COLOR = 'SAMPLERTYPE_LINEAR_COLOR'


ue = types.SimpleNamespace(
    MaterialEditingLibrary=ML,
    LinearColor=LinearColor,
    MaterialProperty=MaterialProperty,
    MaterialSamplerType=MaterialSamplerType,
)
for name in PINS:
    setattr(ue, name, FakeClass(name))

spec = importlib.util.spec_from_file_location(
    'release_fx', r'C:\Mikdash\Working-5.8\MikdashCourtyardV3\Scripts\release_fx.py')
rfx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rfx)

TEXTURES = {n: object() for n in ('T_FX_Noise_fBm_512', 'T_FX_Smoke_Puff_512',
                                  'T_FX_Flame_Card_512', 'T_FX_Ember_64',
                                  'T_FX_DustMote_64', 'T_FX_LightShaft_256')}

failures = []
for name, builder in rfx.MATERIAL_BUILDERS.items():
    del created[:]
    record = {}
    graph = rfx.Graph(ue, object(), record)
    try:
        builder(ue, graph, TEXTURES)
    except Exception as exc:                                     # noqa: BLE001
        failures.append('%s raised %r' % (name, exc))
        continue
    scalars = sorted({n.props.get('parameter_name') for n in created
                      if n._cls == 'MaterialExpressionScalarParameter'})
    vectors = sorted({n.props.get('parameter_name') for n in created
                      if n._cls == 'MaterialExpressionVectorParameter'})
    missing = [p for p in rfx.SHARED_DYNAMIC if p not in scalars]
    dupes = sorted({p for p in scalars if [n.props.get('parameter_name') for n in created
                                           if n._cls == 'MaterialExpressionScalarParameter'].count(p) > 1})
    status = 'FAIL' if missing else 'ok'
    if missing:
        failures.append('%s missing director parameters %s' % (name, missing))
    print('%-14s %-5s nodes=%-4d conns=%-4d scalars=%s' % (name, status, len(created),
                                                           len(record['connections']), scalars))
    print('%-14s        vectors=%s duplicated=%s' % ('', vectors, dupes or 'none'))

print()
if failures:
    for f in failures:
        print('FAIL ' + f)
    sys.exit(1)
print('mock graph dry run: green')
