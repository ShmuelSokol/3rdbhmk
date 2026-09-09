"""Encode actual rendered frames. Explicit --frames and --output required; no overwrite.
No Unreal, source-frame mutation, audio, network or external service.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
from datetime import datetime,timezone

def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as stream:
  for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
 return h.hexdigest()
def run(args):
 frames=Path(args.frames).resolve();output=Path(args.output).resolve()
 if output.exists():raise RuntimeError('Output already exists; refusing overwrite')
 if output.suffix.lower()!='.mp4':raise RuntimeError('Output must be MP4')
 ffmpeg=shutil.which('ffmpeg');ffprobe=shutil.which('ffprobe')
 if not ffmpeg or not ffprobe:raise RuntimeError('Installed ffmpeg/ffprobe required')
 files=sorted(frames.glob('*.png'))
 if len(files)!=960:raise RuntimeError('Expected960PNGframes; got '+str(len(files)))
 matches=[re.fullmatch(r'(.*?)([0-9]+)\.png',p.name) for p in files]
 if any(m is None for m in matches):raise RuntimeError('Cannot resolve numbered PNG names')
 prefixes={m.group(1) for m in matches};widths={len(m.group(2)) for m in matches}
 if len(prefixes)!=1 or len(widths)!=1:raise RuntimeError('Mixed frame naming patterns')
 indices=sorted(int(m.group(2)) for m in matches)
 if indices!=list(range(indices[0],indices[0]+960)):raise RuntimeError('Frames are not960contiguous unique indices')
 import struct
 source_size=None
 for path in files:
  with path.open('rb') as stream:header=stream.read(24)
  if len(header)!=24 or header[:8]!=b'\x89PNG\r\n\x1a\n':raise RuntimeError('Unexpected PNG header '+path.name)
  dimensions=struct.unpack('>II',header[16:24])
  if dimensions not in ((1280,720),(896,504)):raise RuntimeError('Unexpected source dimensions '+path.name)
  if source_size is None:source_size=dimensions
  if dimensions!=source_size:raise RuntimeError('Mixed frame dimensions')
 font=Path('C:/Windows/Fonts/segoeui.ttf')
 if not font.is_file():raise RuntimeError('Segoe UI font missing')
 output.parent.mkdir(parents=True,exist_ok=True)
 receipt=output.with_suffix('.receipt.json')
 if receipt.exists():raise RuntimeError('Receipt exists; refusing overwrite')
 report={'status':'starting','stamp':datetime.now(timezone.utc).isoformat(),'frames':str(frames),'frameCount':960,
         'output':str(output),'audio':False,'errors':[],'sourceFramesRetained':True,'sourceResolution':source_size,'encodedResolution':[1280,720],'upscaled':source_size!=(1280,720)}
 def write():receipt.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
 write()
 try:
  # libavfilter quoting is independent of shell quoting; argument list avoids shell execution.
  font_filter=font.as_posix().replace(':',r'\:')
  filters=("scale=1280:720:flags=lanczos,drawtext=fontfile='"+font_filter+"':text='BEIS HAMIKDASH | WORK IN PROGRESS':"
           "fontcolor=white@0.86:fontsize=18:x=24:y=h-th-22:shadowcolor=black@0.7:shadowx=1:shadowy=1,"
           "fade=t=in:st=0:d=0.6,fade=t=out:st=39.3:d=0.7")
  pattern=str(frames/(next(iter(prefixes))+'%0'+str(next(iter(widths)))+'d.png'))
  command=[ffmpeg,'-hide_banner','-nostdin','-n','-framerate','24','-start_number',str(indices[0]),'-i',pattern,
           '-frames:v','960','-vf',filters,'-an','-c:v','libx264','-preset','medium','-crf','22',
           '-maxrate','2500k','-bufsize','5000k','-pix_fmt','yuv420p','-r','24','-movflags','+faststart',str(output)]
  report['command']=command;write()
  process=subprocess.run(command,capture_output=True,text=True,timeout=600)
  report['encoderReturnCode']=process.returncode;report['encoderTail']=process.stderr[-3000:]
  if process.returncode:raise RuntimeError('Encoder failed; preserve output for diagnosis')
  probe=subprocess.run([ffprobe,'-v','error','-count_frames','-show_streams','-show_format','-of','json',str(output)],capture_output=True,text=True,check=True,timeout=120)
  metadata=json.loads(probe.stdout);report['ffprobe']=metadata
  streams=metadata['streams'];video=[s for s in streams if s['codec_type']=='video']
  if len(video)!=1 or any(s['codec_type']=='audio' for s in streams):raise RuntimeError('Expected one video stream and no audio')
  v=video[0];duration=float(metadata['format']['duration'])
  if v.get('codec_name')!='h264' or v.get('pix_fmt')!='yuv420p' or (v['width'],v['height'])!=(1280,720):raise RuntimeError('Video format mismatch')
  if int(v['nb_read_frames'])!=960 or abs(duration-40)>0.05 or v['avg_frame_rate'] not in ('24/1','24'):raise RuntimeError('Frame count/rate/duration mismatch')
  decode=subprocess.run([ffmpeg,'-hide_banner','-nostdin','-v','error','-xerror','-i',str(output),'-f','null','-'],capture_output=True,text=True,timeout=300)
  report['decodeReturnCode']=decode.returncode;report['decodeErrors']=decode.stderr
  if decode.returncode:raise RuntimeError('Full decode failed')
  report['bytes']=output.stat().st_size;report['sha256']=sha(output)
  if report['bytes']>=16_000_000:raise RuntimeError('Phone target16MB exceeded')
  report['status']='encoded_verified_visual_review_pending'
 except Exception as error:
  report['status']='failed';report['errors'].append(repr(error));raise
 finally:write()
 return report
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--frames',required=True);parser.add_argument('--output',required=True)
 print(json.dumps(run(parser.parse_args()),indent=2))
