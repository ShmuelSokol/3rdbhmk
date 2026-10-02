"""Pure path/argument contract. Does not launch, create directories, or assert UE state."""
import re

_PART = re.compile(r"[A-Za-z0-9_. -]{1,100}\Z")
_SLOT = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")
_DEVICE = re.compile(r"(?:CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])\Z", re.I)

def component(value):
    return bool(isinstance(value, str) and _PART.fullmatch(value)
                and value not in ('.', '..') and not value.endswith(('.', ' '))
                and not _DEVICE.fullmatch(value.split('.')[0]))

def canonical(value):
    if not isinstance(value, str):
        raise ValueError('path must be text')
    p = value.replace('\\', '/')
    if len(p) > 240 or not re.match(r'^[A-Za-z]:/', p):
        raise ValueError('local absolute DOS path required')
    if p.endswith('/'):
        p = p[:-1]
    if not all(component(x) for x in p[3:].split('/')):
        raise ValueError('unsafe path component')
    return p

def same(a, b):
    return canonical(a).casefold() == canonical(b).casefold()

def below(path, root):
    return canonical(path).casefold().startswith(canonical(root).casefold() + '/')

def launch_inputs(root, settings_slot, save_prefix):
    """Returned fixed tokens must be appended ONCE to a separately audited launcher.

    Never merge user args/config overrides. No shell execution is provided.
    Root comes from trusted session allocation, not attach/browser payload.
    """
    root = canonical(root)
    for value in (settings_slot, save_prefix):
        if not isinstance(value, str) or not _SLOT.fullmatch(value) or not component(value):
            raise ValueError('unsafe slot identity')
    if settings_slot.casefold() in {f'{save_prefix}_{i:02d}'.casefold() for i in range(64)} | {f'{save_prefix}_auto'.casefold()}:
        raise ValueError('settings/manual/autosave collision')
    user = root + '/User'
    tokens = [f'-UserDir={user}',
              f'-ini:Game:[/Script/MikdashRuntime.MikdashSettingsSubsystem]:SaveSlot={settings_slot}',
              '-ini:Game:[/Script/MikdashRuntime.MikdashSettingsSubsystem]:SaveUserIndex=0',
              f'-ini:Game:[/Script/MikdashRuntime.MikdashSaveSystem]:SlotNamePrefix={save_prefix}',
              '-ini:Game:[/Script/MikdashRuntime.MikdashSaveSystem]:UserIndex=0']
    # Quote the VALUE for UserDir, as UE parses it with FParse::Value.
    line = f'-UserDir="{user}" ' + ' '.join(tokens[1:])
    return {'tokens': tokens, 'exact_suffix': line, 'root': root,
            'precreate_directories': [user, user+'/Saved', user+'/Saved/Config',
                                     user+'/Saved/Config/Windows', user+'/Saved/SaveGames'],
            'game_ini': user+'/Saved/Config/Windows/Game.ini',
            'game_user_settings_ini': user+'/Saved/Config/Windows/GameUserSettings.ini',
            'save_directory': user+'/Saved/SaveGames'}

def check_path_readbacks(contract, readbacks):
    """Offline lexical helper, NOT runtime SettingsOwned or filesystem isolation."""
    expected = {'user': contract['root']+'/User', 'saved': contract['root']+'/User/Saved',
                'game_ini': contract['game_ini'],
                'game_user_settings_ini': contract['game_user_settings_ini'],
                'save_directory': contract['save_directory']}
    return all(same(readbacks[k], v) for k, v in expected.items())
