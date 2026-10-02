import unittest,tempfile,shutil,json
from pathlib import Path
import replay
class Faults(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix='host11-pub-fault-');self.root=Path(self.temp.name)/'capsule';shutil.copytree(replay.ROOT,self.root)
 def tearDown(self):self.temp.cleanup()
 def repin(self,name):
  m=self.root/'publication-manifest.json';d=json.loads(m.read_text());d['files'][name]=replay.sha((self.root/name).read_bytes());m.write_text(json.dumps(d))
 def test_source_tamper(self):
  p=self.root/'author/Host11/ProtocolTest.cpp';p.write_bytes(p.read_bytes()+b'\n');self.assertRaises(RuntimeError,replay.audit,self.root)
 def test_extra_binary(self):
  (self.root/'bad.exe').write_bytes(b'unlisted');self.assertRaises(RuntimeError,replay.audit,self.root)
 def test_missing_source(self):
  (self.root/'author/Host11/ProtocolTest.cpp').unlink();self.assertRaises(RuntimeError,replay.audit,self.root)
 def test_escape_path(self):self.assertRaises(RuntimeError,replay.safe,self.root,'../escape')
 def test_repinned_non_users_hostpath(self):
  f=self.root/'native-prerequisites.json';d=json.loads(f.read_text());d['projectDir']='C:'+chr(92)+chr(92).join(['Mikdash','Working-5.8','MikdashCourtyardV3']);f.write_text(json.dumps(d));self.repin('native-prerequisites.json')
  with self.assertRaisesRegex(RuntimeError,'absolute host path'):replay.audit(self.root)
 def test_hostpath_forms(self):
  for value in ['D:/project',chr(92)*2+'server'+chr(92)+'share','//server/share','file:///var/project','/opt/project']:
   with self.subTest(value=value):
    with self.assertRaisesRegex(RuntimeError,'absolute host path'):replay.metadata_paths({'projectDir':value})
 def test_urls_assets_and_api_references_unchanged(self):
  d={'url':'https://github.com/owner/repo.git','asset':'/Game/Actors/A.A','map':'/Engine/Maps/Entry','path':'Engine/Source/Runtime/Engine/Classes/Engine/InstancedStaticMesh.h','line':435,'sha256':'a'*64};old=json.dumps(d);replay.metadata_paths(d);self.assertEqual(json.dumps(d),old)
 def test_repinned_dependency_origin_mismatch(self):
  f=self.root/'closure.json';d=json.loads(f.read_text());row=next(v for v in d['files'].values() if v['kind']=='git');row['sha256']='0'*64;f.write_text(json.dumps(d));self.repin('closure.json')
  with self.assertRaisesRegex(RuntimeError,'original hash mismatch'):replay.audit(self.root)
if __name__=='__main__':unittest.main()
