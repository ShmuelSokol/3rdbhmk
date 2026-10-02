"""Harmless owned test child: no sockets, descendants, config, permissions or UE."""
import os
from pathlib import Path
import struct
import sys
import time

def main():
    mode=sys.argv[1]
    if mode not in ('readexit','hold','ignore'):return 2
    user=[a[len('-UserDir='):] for a in sys.argv[2:] if a.startswith('-UserDir=')]
    if len(user)!=1:return 3
    root=Path(user[0])
    if 'runtime_settings04' not in root.parts or 'runs' not in root.parts:return 4
    if mode=='ignore':
        time.sleep(10) # owned Job/watchdog kills earlier; no stdin reads
        return 5
    def exact(n):
        data=b''
        while len(data)<n:
            more=os.read(0,n-len(data))
            if not more:raise ValueError('short frame')
            data+=more
        return data
    size=struct.unpack('!I',exact(4))[0]
    if not 2<=size<=4092:return 6
    exact(size) # never print, decode, or persist the public synthetic key/frame
    if os.read(0,1):return 7
    with (root/'ready').open('xb') as f:f.write(b'read-and-eof\n')
    time.sleep(.3 if mode=='readexit' else 10)
    return 0

if __name__=='__main__':raise SystemExit(main())
