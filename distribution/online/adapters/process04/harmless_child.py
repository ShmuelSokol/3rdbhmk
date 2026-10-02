"""STAGED ONLY. Execute solely during the later coordinated owned-process test.

No sockets, UE, descendants, logging, environment dumps or secret output. Modes
allow the real job/writer test to check reading, blocked writing and early exit.
Use a PUBLIC synthetic frame, never a real session key. Exit codes only.
"""
import os
import struct
import sys
import time


def main():
    if len(sys.argv)!=2 or sys.argv[1] not in ('read','ignore','exit'):
        return 2
    if sys.argv[1]=='exit':return 0
    if sys.argv[1]=='ignore':
        time.sleep(60)  # external owned deadline MUST kill well before this
        return 3
    def exact(n):
        data=bytearray()
        while len(data)<n:
            chunk=os.read(0,n-len(data))
            if not chunk:raise ValueError()
            data.extend(chunk)
        return bytes(data)
    try:
        size=struct.unpack('!I',exact(4))[0]
        if not 2<=size<=4092:return 4
        exact(size)  # deliberately do not print/decode/store private contents
        return 0
    except Exception:
        return 5


if __name__=='__main__':sys.exit(main())
