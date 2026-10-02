import hashlib,json,sys,unittest
from pathlib import Path
import measurement as M
import test_replay
if sys.flags.optimize:raise SystemExit('Optimized Python unsupported')
manifest=M.read(M.HERE/'manifest.json')
M.check_pins({'inputs':manifest['files']})
suite=unittest.defaultTestLoader.loadTestsFromModule(test_replay)
result=unittest.TextTestRunner(verbosity=2).run(suite)
if not result.wasSuccessful():raise SystemExit(1)
M.run()
M.check_pins({'inputs':manifest['files']})
print('PASS portable exact recomputation; conditional source evidence only')
