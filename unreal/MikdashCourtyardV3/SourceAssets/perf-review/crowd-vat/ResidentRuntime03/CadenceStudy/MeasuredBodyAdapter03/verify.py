"""Check frozen source and actual recorded MSVC source identities; no launch."""
from pathlib import Path
import hashlib,json,sys
B=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding="utf-8"))
def need(ok,why):
    if not ok:raise ValueError(why)
def verify():
    m=read(B/"manifest.json")
    for n,p in m["files"].items():need(sha(B/n)==p["sha256"],"changed: "+n)
    r=read(B/"standalone-msvc.json")
    for n,h in r["sourcePins"].items():need(sha(B/Path(n.replace("\\","/")))==h,"tested source differs: "+n)
    need(r["suite"]["checks"]==11040 and r["suite"]["failures"]==0,"suite failure")
    need(r["cleanupConfirmed"] and not r["slotBlocked"] and r["status"]=="source_fixture_exit_zero","job not clean")
    need(r["drain"][-1]["exitCode"]==0 and r["drain"][-1]["active"]==0 and r["elapsedSeconds"]<60,"job incomplete")
    if "--local-receipt" in sys.argv:need(sha(Path(r["localReceipt"]))==r["receiptSha256"],"local receipt differs")
    return {"sourceChecks":"pass","recordedCppChecks":11040,"geometry":"test doubles only","productionAdopted":False}
if __name__=="__main__":print(json.dumps(verify(),indent=2))
