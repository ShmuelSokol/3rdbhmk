"""Garment-only source construction; never calls full-character/head assembly."""
import sys
sys.dont_write_bytecode = True
import create_kohen_gadol_v1 as K
import measure_kohen_garment_clearance as M

def body_parts():
    M.LEG_PREFIXES = ('Shin', 'Foot')
    M.OUTER_TOP_CAP_CM = 80.0
    M.OUTER_ANGLE = None
    bones = K.C.skeleton()
    index = {b['name']: i for i, b in enumerate(bones)}
    parts = K.Parts()
    K.ketonet(parts)
    K.meil(parts)
    K.legs(parts)
    return bones, index, parts.parts, K.influence, 'Ketonet', K.KETONET_SEGMENTS, 'Meil', K.MEIL_SEGMENTS
