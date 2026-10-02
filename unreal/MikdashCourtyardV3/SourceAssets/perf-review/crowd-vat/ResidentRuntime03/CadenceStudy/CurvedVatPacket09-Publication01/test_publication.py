import unittest,tempfile,shutil,json
from pathlib import Path
import replay
class Faults(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix='curve09-pub-fault-');self.root=Path(self.temp.name)/'capsule';shutil.copytree(replay.ROOT,self.root)
 def tearDown(self):self.temp.cleanup()
 def test_source_tamper(self):
  p=self.root/'author/CurvePacket.h';p.write_bytes(p.read_bytes()+b'\n');self.assertRaises(RuntimeError,replay.audit,self.root)
 def test_extra_binary(self):
  (self.root/'bad.exe').write_bytes(b'not exported');self.assertRaises(RuntimeError,replay.audit,self.root)
 def test_missing_source(self):
  (self.root/'author/CurvePacket.h').unlink();self.assertRaises(RuntimeError,replay.audit,self.root)
 def test_escape_path(self):self.assertRaises(RuntimeError,replay.safe,self.root,'../escape')
 def test_wrong_public_blob(self):
  row={'commit':'0'*40,'path':'missing','blob':'0'*40,'sha256':'0'*64};self.assertRaises(Exception,replay.dependency,self.root,row)
 def test_original_non_users_projectdir_even_repinned(self):
  # Reconstruct the exact finding as test input, not exported metadata.
  f=self.root/'author/spec.json';d=json.loads(f.read_text())
  d['projectDir']='C:'+chr(92)+chr(92).join(['Mikdash','Working-5.8','MikdashCourtyardV3']);f.write_text(json.dumps(d))
  h=replay.sha(f.read_bytes());c=self.root/'closure.json';v=json.loads(c.read_text());v['files']['spec.json']['sha256']=h;c.write_text(json.dumps(v))
  m=self.root/'publication-manifest.json';v=json.loads(m.read_text());v['files']['author/spec.json']=h;v['files']['closure.json']=replay.sha(c.read_bytes());m.write_text(json.dumps(v))
  with self.assertRaisesRegex(RuntimeError,'absolute host path'):replay.audit(self.root)
 def test_host_path_forms(self):
  for value in ['D:/workspace/project',chr(92)*2+'host'+chr(92)+'share','//host/share','file:///var/project','/opt/project']:
   with self.subTest(value=value):
    with self.assertRaisesRegex(RuntimeError,'absolute host path'):replay.metadata_paths({'projectDir':value})
 def test_preserve_urls_and_unreal_assets(self):
  d={'repository':'https://github.com/owner/repo.git','namespace':'/Game/MikdashV3/Runtime/CrowdVATV1','mesh':'/Game/Characters/Body.Body','map':'/Engine/Maps/Entry','projectDir':'<external-project-root>','receiptFolder':'SourceAssets/runtime-review'}
  before=json.dumps(d);replay.metadata_paths(d);self.assertEqual(json.dumps(d),before)
 def test_placeholder_required(self):
  f=self.root/'author/spec.json';d=json.loads(f.read_text());d['projectDir']='relative-but-unapproved';f.write_text(json.dumps(d))
  m=self.root/'publication-manifest.json';v=json.loads(m.read_text());v['files']['author/spec.json']=replay.sha(f.read_bytes());m.write_text(json.dumps(v))
  with self.assertRaisesRegex(RuntimeError,'external placeholder'):replay.audit(self.root)
if __name__=='__main__':unittest.main()
