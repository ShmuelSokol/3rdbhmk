"""Review port contract for Beauvoir; never installs/edits the shared controller.
HeadingDegrees / r_A.Yaw is the instance basis while a turn is live.
"""
from dataclasses import dataclass
import math
import struct

def f32(x):
    return struct.unpack('<f',struct.pack('<f',x))[0]

@dataclass(frozen=True)
class AngularState:
    TurnStartGameTime: float = 0.0
    TurnDeltaDegrees: float = 0.0

def channels(current, previous):
    values=(current.TurnStartGameTime,current.TurnDeltaDegrees,previous.TurnStartGameTime,previous.TurnDeltaDegrees)
    if not all(math.isfinite(v) for v in values) or abs(values[1])>180 or abs(values[3])>180:
        raise ValueError('Invalid angular contract')
    return dict(zip(range(26,30),map(f32,values)))

def completed(state, now):
    # Conservative positive float ceiling of end, then one extra ULP, so CPU
    # never grants translation just before the material reaches its endpoint.
    # Native HLSL float parity remains an explicit compile/render gate.
    if state.TurnDeltaDegrees==0:return True
    end=f32(state.TurnStartGameTime)+abs(f32(state.TurnDeltaDegrees))/90.0
    rounded=f32(end)
    if rounded<0 or not math.isfinite(rounded):raise ValueError('Expected finite nonnegative game clock')
    bits=struct.unpack('<I',struct.pack('<f',rounded))[0]
    if rounded<end:bits+=1
    safe=struct.unpack('<f',struct.pack('<I',bits+1))[0]
    return f32(now)>=safe

def translation_gate(state, now, *, linear_reservation_live, ground_gate, sweep_gate, can_reserve):
    """No reserve/move operation: caller must still commit successful Reserve.
    Deliberately short circuits all physical callbacks until turn/linear drain.
    """
    if linear_reservation_live or not completed(state,now):return False
    return bool(ground_gate() and sweep_gate() and can_reserve())
