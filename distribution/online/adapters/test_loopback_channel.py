import json
import struct
import unittest
from unittest.mock import patch
from dataclasses import asdict
from session_core import Ownership, SessionError
from adapters.loopback_channel import LoopbackChannel, encode_frame, decode_frame


class SocketDouble:
    def __init__(self, response):
        self.response=response;self.sent=None;self.address=None;self.closed=False
    def __enter__(self):return self
    def __exit__(self,*_):self.closed=True
    def settimeout(self,t):assert 0<t<=1
    def connect(self,address):self.address=address
    def sendall(self,frame):self.sent=frame
    def recv(self,size):
        n=min(size,7);result=self.response[:n];self.response=self.response[n:];return result


class LoopbackTests(unittest.TestCase):
    def setUp(self):
        self.owner=Ownership('s','p','stream','save','settings',110)
        self.key=b'k'*32  # test-only fixture; no capability generation or receipt storage
        self.packet=dict(owner=asdict(self.owner),sequence=1,operation='input')
        self.ack=dict(self.packet,status='applied')
        self.response=encode_frame(self.ack,self.key,b'mikdash-response-v1\0')
        self.channel=LoopbackChannel(self.owner,34567,self.key,clock=lambda:100)

    def test_actual_exchange_code_partial_reads_loopback_and_close(self):
        peer=SocketDouble(self.response)
        with patch('adapters.loopback_channel.socket.socket',return_value=peer):
            self.assertEqual(self.channel.exchange(self.owner,self.packet,1),self.ack)
        self.assertEqual(peer.address,('127.0.0.1',34567));self.assertTrue(peer.closed)
        size=struct.unpack('!I',peer.sent[:4])[0]
        self.assertEqual(decode_frame(peer.sent[4:4+size],peer.sent[4+size:],self.key,b'mikdash-request-v1\0'),self.packet)

    def test_response_auth_direction_tamper_and_oversize(self):
        frames=[self.response[:-1]+bytes([self.response[-1]^1]),
            encode_frame(self.ack,self.key,b'mikdash-request-v1\0'),struct.pack('!I',4097),b'']
        for frame in frames:
            c=LoopbackChannel(self.owner,34567,self.key,clock=lambda:100)
            with patch('adapters.loopback_channel.socket.socket',return_value=SocketDouble(frame)):
                with self.assertRaises(SessionError):c.exchange(self.owner,self.packet,1)

    def test_absolute_timeout_not_renewed_by_partial_reads(self):
        values=iter([100,100.1,100.2,100.3,101])
        c=LoopbackChannel(self.owner,34567,self.key,clock=lambda:next(values))
        peer=SocketDouble(self.response)
        with patch('adapters.loopback_channel.socket.socket',return_value=peer):
            with self.assertRaises(SessionError):c.exchange(self.owner,self.packet,1)
        self.assertTrue(peer.closed)

    def test_no_retry_or_socket_on_replayed_sequence(self):
        with patch('adapters.loopback_channel.socket.socket',return_value=SocketDouble(self.response)) as factory:
            self.channel.exchange(self.owner,self.packet,1)
            with self.assertRaises(SessionError):self.channel.exchange(self.owner,self.packet,1)
            self.assertEqual(factory.call_count,1)

if __name__=='__main__':unittest.main()
