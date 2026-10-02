"""Additive derived-path validation; frozen01 remains unchanged."""
import hashlib
import importlib.util
from pathlib import Path

def _lex():
    p=Path(__file__).resolve().parent.parent/'runtime_settings01/launcher_contract.py'
    if hashlib.sha256(p.read_bytes()).hexdigest()!='67e00824d9279f219b0d137fdda19c328c4b0c9d9e5c63c4b81e2dde57c7efff':
        raise ValueError('Frozen launcher source changed')
    spec=importlib.util.spec_from_file_location('settings03_lex',p)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m

def launch_inputs(root,settings_slot,save_prefix,slot_count):
    """Slot count is explicit deployment allocation data, never guessed from a CDO.

    Emit that count in the session-only INI argument so manual names are known.
    Actual native slot readbacks remain necessary before accepting remote input.
    """
    if type(slot_count) is not int or not 1<=slot_count<=64:raise ValueError('Slot count 1..64 required')
    lex=_lex();out=lex.launch_inputs(root,settings_slot,save_prefix)
    if any(c.isspace() for c in out['root']):raise ValueError('03 owned Job root cannot contain whitespace')
    out['precreate_directories'].append(out['root']+'/User/Temp')
    slots=[settings_slot]+[f'{save_prefix}_{i:02d}' for i in range(slot_count)]+[save_prefix+'_Auto']
    if len({s.casefold() for s in slots})!=len(slots):raise ValueError('Colliding actual slots')
    out['save_files']=[out['save_directory']+'/'+s+'.sav' for s in slots]
    paths=out['precreate_directories']+[out['game_ini'],out['game_user_settings_ini'],out['save_directory']]+out['save_files']
    for path in paths:lex.canonical(path) # reject before ANY argument return or child acquisition
    out['longest_save_file']=max(out['save_files'],key=len)
    out['slot_count']=slot_count
    token=f'-ini:Game:[/Script/MikdashRuntime.MikdashSaveSystem]:SlotCount={slot_count}'
    out['tokens'].append(token);out['exact_suffix']+=' '+token
    return out
