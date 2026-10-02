"""Executes the real additive host preflight, not a native/pipe simulation."""
import dataclasses
import json
from pathlib import Path
import struct
import sys
import unittest
ROOT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT),str(ROOT.parent)]
from bootstrap_record import inspect_private_record, make_private_record
from session_core import Ownership, SessionError


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.owner=Ownership('session','process','stream','save','settings',110)
        self.frame=make_private_record(self.owner,49152,bytes(32),clock=lambda:100,qpc=lambda:100)
        self.data=json.loads(self.frame[4:])
    def encode(self, value):
        body=json.dumps(value,separators=(',',':')).encode('ascii')
        return struct.pack('!I',len(body))+body
    def reject(self, frame, owner=None, now=100):
        with self.assertRaises(SessionError) as caught:
            inspect_private_record(frame,self.owner if owner is None else owner,now)
        self.assertEqual(str(caught.exception),'Private bootstrap record refused')
    def test_real_builder_contract(self):
        value=inspect_private_record(self.frame,self.owner,100)
        self.assertEqual(value.owner,self.owner)
        self.assertEqual(value.port,49152)
        self.assertLess(value.deadline,self.owner.expires_at)
        self.assertFalse(hasattr(value,'key'))
        self.assertFalse(hasattr(value,'authenticated'))
    def test_frame_truncation_and_trailing(self):
        for f in (self.frame[:-1],self.frame+b'x',self.frame+self.frame,b'',b'\0'*4097):self.reject(f)
    def test_duplicate_root_key(self):
        body=self.frame[4:-1]+b',"port":49152}'
        self.reject(struct.pack('!I',len(body))+body)
    def test_duplicate_owner_key(self):
        body=self.frame[4:].replace(b'"session_id":"session"',b'"session_id":"session","session_id":"session"')
        self.reject(struct.pack('!I',len(body))+body)
    def test_cross_allocation_refused(self):
        for field in ('session_id','process_key','stream_id','save_prefix','settings_slot'):
            self.reject(self.frame,dataclasses.replace(self.owner,**{field:'other'}))
    def test_exact_expiry_and_stale_queue(self):
        self.reject(self.frame,now=self.data['qpc_deadline'])
        self.reject(self.frame,now=111)
    def test_lifetime_extension(self):
        self.data['qpc_deadline']=111;self.reject(self.encode(self.data))
    def test_wrong_clock_domain(self):
        self.data['clock_domain']='python-monotonic';self.reject(self.encode(self.data))
    def test_huge_and_nonfinite_numbers(self):
        for bad in (10**400,float('inf'),float('nan'),-1,True):
            self.reject(self.frame,now=bad)
            value=dict(self.data,qpc_deadline=bad);self.reject(self.encode(value))
    def test_hostile_types(self):
        for bad in ([],{},None,'100'):
            self.reject(self.frame,owner=bad if bad is not None else [],now=100)
        for field in ('owner','port','key_hex','version'):
            value=dict(self.data);value[field]=[];self.reject(self.encode(value))
        self.reject(self.frame,owner=dataclasses.replace(self.owner,session_id=[]))
        self.reject(self.frame,owner=dataclasses.replace(self.owner,expires_at=True))
    def test_identity_length_and_character(self):
        for value in ('x'*129,'','../other'):
            data=dict(self.data,owner=dict(self.data['owner'],session_id=value));self.reject(self.encode(data))
    def test_secret_syntax_and_no_exception_leak(self):
        for value in ('sensitive-do-not-echo','AA'*32,'00'*31):
            self.reject(self.encode(dict(self.data,key_hex=value)))
    def test_extra_fields_and_arrays(self):
        self.reject(self.encode(dict(self.data,authenticated=True)))
        self.reject(self.encode([self.data]))
    def test_writer_clock_failure_scrubbed(self):
        def fail():raise RuntimeError('sensitive-do-not-echo')
        with self.assertRaises(SessionError) as caught:make_private_record(self.owner,49152,bytes(32),qpc=fail)
        self.assertEqual(str(caught.exception),'Private bootstrap record refused')
    def test_writer_post_creation_expiry(self):
        times=iter((100,100,111))
        with self.assertRaises(SessionError):make_private_record(self.owner,49152,bytes(32),clock=lambda:100,qpc=lambda:next(times))

if __name__=='__main__':unittest.main()
