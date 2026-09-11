"""Contact sheet / crops from a -dumpmovie filmstrip (Scripts/capture_people_walk_movie.ps1).

Frame i of a -benchmark -fps=N run is i/N seconds of game time from world start, so every
tile is labelled with its frame index and game time.

  python Scripts/make_movie_sheet.py <movie-folder> <out.png> --fps 10 --frames 440 460 480 ...
        [--cols 3] [--tile 640] [--crop x0 y0 x1 y1] [--label-prefix cp14]
  python Scripts/make_movie_sheet.py <movie-folder> <out.png> --fps 10 --single 482 [--crop ...]
"""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw


def frame_path(folder, index):
    hits = sorted(Path(folder).glob('*-%04d.png' % index))
    if not hits:
        raise SystemExit('no frame %04d in %s' % (index, folder))
    return hits[0]


def tile(folder, index, fps, width, crop, prefix):
    im = Image.open(frame_path(folder, index)).convert('RGB')
    if crop:
        im = im.crop(tuple(crop))
    h = round(im.height * width / im.width)
    im = im.resize((width, h), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    text = '%sf%d t=%.1fs' % (prefix, index, index / float(fps))
    d.rectangle((0, 0, 8 + 7 * len(text), 16), fill=(0, 0, 0))
    d.text((4, 2), text, fill=(255, 255, 0))
    return im


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('folder')
    ap.add_argument('out')
    ap.add_argument('--fps', type=float, default=10.0)
    ap.add_argument('--frames', type=int, nargs='*')
    ap.add_argument('--single', type=int)
    ap.add_argument('--cols', type=int, default=3)
    ap.add_argument('--tile', type=int, default=640)
    ap.add_argument('--crop', type=int, nargs=4)
    ap.add_argument('--label-prefix', default='')
    a = ap.parse_args()
    if a.single is not None:
        im = Image.open(frame_path(a.folder, a.single)).convert('RGB')
        if a.crop:
            im = im.crop(tuple(a.crop))
        im.save(a.out)
        print(a.out, im.size)
        return
    tiles = [tile(a.folder, i, a.fps, a.tile, a.crop, a.label_prefix) for i in a.frames]
    rows = (len(tiles) + a.cols - 1) // a.cols
    th = max(t.height for t in tiles)
    sheet = Image.new('RGB', (a.cols * a.tile, rows * th), (0, 0, 0))
    for k, t in enumerate(tiles):
        sheet.paste(t, ((k % a.cols) * a.tile, (k // a.cols) * th))
    sheet.save(a.out)
    print(a.out, sheet.size)


if __name__ == '__main__':
    main()
