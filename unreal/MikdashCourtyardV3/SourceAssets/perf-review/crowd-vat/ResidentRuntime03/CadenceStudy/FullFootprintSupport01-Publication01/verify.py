"""Portable frozen sources and recorded execution verifier. No subprocesses."""
from pathlib import Path
import hashlib,json,re
B=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding="utf-8"))
def need(ok,why):
    if not ok:raise ValueError(why)
def verify():
    m=read(B/"manifest.json")
    for n,h in m["files"].items():need(sha(B/n)==h,"file drift: "+n)
    ev=read(B/"execution-evidence.json")
    need(ev["checks"]==193 and ev["failures"]==0 and not ev["loadedWorldEquivalence"],"scope/results")
    for r in (ev["receipt"],ev["independentReceipt"]):
        need(r["status"]=="source_fixture_exit_zero" and r["cleanupConfirmed"] and not r["slotBlocked"],"execution")
        need(r["elapsedSeconds"]<60 and r["drain"][-1]["exitCode"]==0 and r["drain"][-1]["active"]==0,"cleanup/deadline")
        for n,h in r["sourcePins"].items():need(sha(B/n)==h,"executed source drift")
    text=(B/"MeasuredProfiles.h").read_text(encoding="utf-8")
    need(sha(B/"measured-results.json") in text,"measurement provenance")
    rows=re.findall(r'\{"([^"]+)", ([^,]+), ([^,]+), ([^,]+), ([^}]+)\}',text)
    actual=[(r[0],*(float(v) for v in r[1:])) for r in rows]
    expected=[(v,r["scale"],r["radiusCm"],r["minZCm"],r["maxZCm"]) for v,data in read(B/"measured-results.json")["study13"].items() for r in data["scales"]]
    need(actual==expected and len(actual)==6,"measured profiles")
    return {"status":"source-and-recorded-execution-verified","profiles":6,"cppChecksPerRun":193,"nativeWorldAccepted":False}
if __name__=="__main__":print(json.dumps(verify(),indent=2))
