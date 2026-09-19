"""Stock-node previous-frame WPO for the opt-in 26-float CrowdVATV3 contract.

Current WPO, normals, colours and simulation are unchanged. HISM's previous
instance basis is its current basis: compensate the rest vertex AND VAT delta,
not just root travel. The CPU captures history before every visited mutation.
Only previous-frame times preceding that visit use the snapshot; otherwise the
current state already describes the preceding rendered frame.
"""

CUSTOM_FLOATS = 26
HISTORY_LAYOUT = {
    11: 'oldMinusCurrentAnchorWorldX', 12: 'oldMinusCurrentAnchorWorldY',
    13: 'oldMinusCurrentAnchorWorldZ', 14: 'relativeYawCos', 15: 'relativeYawSin',
    16: 'oldWalkPhase', 17: 'oldAnchorTime', 18: 'oldWalkRate',
    19: 'oldWorldVelocityX', 20: 'oldWorldVelocityY', 21: 'oldWorldVelocityZ',
    22: 'oldIdle', 23: 'oldSwitchTime', 24: 'oldHorizon', 25: 'historyUpdateTime',
}


def previous_wpo(g, time, cd, current_wpo, clip, walk_frames, uvw,
                 defaults, walk_size, walk_min, idle_position, blend, negdt, to_world):
    e = g.ue
    add, sub, mul, div = (e.MaterialExpressionAdd, e.MaterialExpressionSubtract,
                          e.MaterialExpressionMultiply, e.MaterialExpressionDivide)
    data = {i: g.custom_data(i, 1.0 if i == 14 else -1000.0 if i == 23 else 0.0, 0, 0)
            for i in HISTORY_LAYOUT}
    vector = lambda x, y, z: g.op(e.MaterialExpressionAppendVector,
                                 g.op(e.MaterialExpressionAppendVector, x, y), z)
    old_dt = g.clamp(g.op(sub, time, data[17]), g.op(mul, negdt, g.const(-1)), data[24])
    old_phase = g.unary(e.MaterialExpressionFrac, g.op(add, data[16], g.op(mul, old_dt, data[18])))
    old_walk = g.op(add, g.op(mul, clip(old_phase, walk_frames, uvw,
                       'WalkPositionTexture', defaults['WalkPositionTexture']), walk_size), walk_min)
    weight = g.unary(e.MaterialExpressionSaturate, g.op(div, g.op(sub, time, data[23]), blend))
    idle_weight = g.lerp(g.unary(e.MaterialExpressionOneMinus, weight), weight, data[22])
    old_delta = g.lerp(old_walk, idle_position, idle_weight)
    rest = g.make(e.MaterialExpressionPreSkinnedPosition)
    old_local = g.op(add, rest, old_delta)
    x, y, z = (g.mask(old_local, c) for c in 'rgb')
    rotated = vector(g.op(sub, g.op(mul, data[14], x), g.op(mul, data[15], y)),
                     g.op(add, g.op(mul, data[15], x), g.op(mul, data[14], y)), z)
    # Rest is already positioned with the CURRENT instance matrix by the vertex
    # factory. Replace its orientation as part of WPO, preserving constant scale.
    correction = to_world(g.op(sub, rotated, rest))
    offset = vector(data[11], data[12], data[13])
    drift = g.op(mul, vector(data[19], data[20], data[21]), old_dt)
    history_wpo = g.op(add, g.op(add, offset, correction), drift)
    select = g.make(e.MaterialExpressionIf)
    select.set_editor_property('equals_threshold', 0.0)
    g.link(time, select, ['A'])
    g.link(data[25], select, ['B'])
    g.link(current_wpo, select, ['A > B', 'AGreaterThanB'])
    g.link(current_wpo, select, ['A == B', 'AEqualsB'])
    g.link(history_wpo, select, ['A < B', 'ALessThanB'])
    switch = g.make(e.MaterialExpressionPreviousFrameSwitch)
    g.link(current_wpo, switch, ['Current Frame', 'CurrentFrame'])
    g.link(select, switch, ['Previous Frame', 'PreviousFrame'])
    return switch
