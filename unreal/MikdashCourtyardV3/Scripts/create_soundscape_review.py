"""Offline source/signal review only. Never imports Unreal or mutates Content.

python Scripts/create_soundscape_review.py --fetch
python Scripts/create_soundscape_review.py
Requires numpy. Fetch is opt-in; source bytes and license pages remain unchanged.
"""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request
import wave
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'SourceAssets/soundscape-review'
WIND = 'https://opengameart.org/sites/default/files/park_ambience_wind.wav'
PAGES = {
    'park-ambiences.html': 'https://opengameart.org/content/park-ambiences',
    'fantozzi-footsteps.html': 'https://opengameart.org/content/fantozzis-footsteps-grasssand-stone',
}


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''):
            h.update(b)
    return h.hexdigest()


def pcm(raw, width):
    if width == 2:
        return np.frombuffer(raw, dtype='<i2').astype(np.float64) / 32768
    if width == 3:
        b = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3).astype(np.int32)
        n = b[:, 0] | b[:, 1] << 8 | b[:, 2] << 16
        n = (n ^ 0x800000) - 0x800000
        return n.astype(np.float64) / 8388608
    raise ValueError('Unsupported PCM width: %s' % width)


def db(value):
    return round(20 * np.log10(max(float(value), 1e-12)), 3)


def inspect(path):
    count = 0
    sum_sq = total = peak = clipped = 0
    windows = []
    first = last = None
    with wave.open(str(path), 'rb') as w:
        rate, channels, width, frames = w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()
        while True:
            raw = w.readframes(rate)
            if not raw:
                break
            x = pcm(raw, width)
            if first is None:
                first = x[:channels].copy()
            last = x[-channels:].copy()
            count += x.size
            sum_sq += float(np.dot(x, x))
            total += float(x.sum())
            peak = max(peak, float(np.abs(x).max()))
            clipped += int(np.count_nonzero((x <= -1) | (x >= 1 - 1 / 2 ** (width * 8 - 1))))
            windows.append(db(np.sqrt(np.mean(x * x))))
    if count == 0:
        raise ValueError('Empty audio: %s' % path)
    return dict(path=path.relative_to(ROOT).as_posix(), sha256=digest(path),
                sample_rate=rate, channels=channels, bits=width * 8,
                duration_seconds=round(frames / rate, 6), peak_dbfs=db(peak),
                rms_dbfs=db(np.sqrt(sum_sq / count)), dc_offset=total / count,
                full_scale_samples=clipped, one_second_rms_dbfs=windows,
                raw_loop_seam_max_delta=float(np.abs(last - first).max()),
                audition='PENDING: PCM metrics cannot detect unwanted birds, voices, traffic, or microphone wind')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fetch', action='store_true')
    args = parser.parse_args()
    for sub in ('sources', 'evidence', 'mono-footsteps'):
        (OUT / sub).mkdir(parents=True, exist_ok=True)
    if args.fetch:
        for name, url in list(PAGES.items()) + [('park_ambience_wind.wav', WIND)]:
            folder = 'sources' if name.endswith('.wav') else 'evidence'
            dest = OUT / folder / name
            if not dest.exists():
                temporary = dest.with_suffix(dest.suffix + '.part')
                with urllib.request.urlopen(url, timeout=60) as src, temporary.open('wb') as dst:
                    while True:
                        chunk = src.read(1048576)
                        if not chunk:
                            break
                        dst.write(chunk)
                temporary.replace(dest)
    wind = OUT / 'sources/park_ambience_wind.wav'
    if not wind.exists():
        raise SystemExit('Missing wind candidate; use --fetch once.')
    existing = sorted((ROOT / 'SourceAssets/audio-review/Fantozzi/Wav').glob('*.wav'))
    if len(existing) != 12:
        raise ValueError('Expected twelve preserved Fantozzi source WAVs')
    derived = []
    for source in existing:
        with wave.open(str(source), 'rb') as w:
            assert w.getsampwidth() == 2 and w.getnchannels() == 2
            rate = w.getframerate()
            stereo = np.frombuffer(w.readframes(w.getnframes()), dtype='<i2').reshape(-1, 2).astype(np.int32)
        # Original recordings, arithmetic stereo downmix only. No synthesized layers.
        mono = np.rint(stereo.mean(axis=1)).astype('<i2')
        dest = OUT / 'mono-footsteps' / (source.stem + '-mono.wav')
        with wave.open(str(dest), 'wb') as w:
            w.setparams((1, 2, rate, 0, 'NONE', 'not compressed'))
            w.writeframes(mono.tobytes())
        derived.append(dict(output=dest.relative_to(ROOT).as_posix(), source=source.relative_to(ROOT).as_posix(),
                            source_sha256=digest(source), operation='round((L+R)/2), PCM16, original sample rate'))
    report = dict(status='offline signal inventory; native audition and integration pending',
                  wind=inspect(wind), existing=[inspect(p) for p in existing],
                  derived=[inspect(OUT / 'mono-footsteps' / (p.stem + '-mono.wav')) for p in existing],
                  derivations=derived,
                  evidence=[dict(path=p.relative_to(ROOT).as_posix(), sha256=digest(p), url=PAGES[p.name])
                            for p in sorted((OUT / 'evidence').glob('*.html'))],
                  limits=['No subjective audio-quality acceptance', 'No seamless-loop claim',
                          'No Jerusalem ecology or Temple acoustic authenticity claim', 'No Unreal runtime executed'])
    (OUT / 'signal-review.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(wind=report['wind'], mono_steps=len(derived)), indent=2))


if __name__ == '__main__':
    main()
