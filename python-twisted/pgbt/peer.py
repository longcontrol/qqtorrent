import struct
import socket
import requests
import bencodepy
import bitarray

from pgbt.config import CONFIG


class TorrentPeer():
    def __init__(self, torrent, ip, port, peer_id=None):
        self.torrent = torrent
        self.peer_id = peer_id
        self.ip = ip
        self.port = port
        self.sock = None

        self.is_started = False
        self.am_choking = True
        self.am_interested = False
        self.peer_choking = True
        self.peer_interested = False

    def __del__(self):
        if self.sock:
            self.sock.close()

    def __repr__(self):
        return ('TorrentPeer(ip={ip}, port={port})'
                .format(**self.__dict__))

    def start_peer(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(10)
        self.sock.connect((self.ip, self.port))
        print('Sending peer handshake: %s:%s' % (self.ip, self.port))
        self.send_handshake()
        self.receive_handshake()

    def send_handshake(self):
        msg = self.build_handshake(
            self.torrent.metainfo.info_hash, CONFIG['peer_id'])
        self.sock.send(msg)

    def receive_handshake(self):
        pstrlen = int(self.sock.recv(1)[0])
        data = self.sock.recv(49 - 1 + pstrlen)
        handshake = self.decode_handshake(pstrlen, data)
        if handshake['pstr'] != 'BitTorrent protocol':
            raise PeerProtocolError('Protocol not recognized')
        print('%s received handshake' % self)

    def receive_message(self):
        data = self.sock.recv(4)
        length_prefix = struct.unpack('!L', data)[0]
        if length_prefix == 0:
            print('%s received keep-alive' % self)
            return
        data = self.sock.recv(length_prefix)
        # TODO: check data length == length_prefix
        msg_dict = self.decode_message(data)
        self.handle_message(msg_dict)

    def handle_keepalive(self):
        # TODO
        pass

    def handle_message(self, msg_dict):
        msg_id = msg_dict['msg_id']
        payload = msg_dict['payload']

        # TODO: implement all
        if msg_id == 0:
            msg_type = 'choke'
        elif msg_id == 1:
            msg_type = 'unchoke'
        elif msg_id == 2:
            msg_type = 'interested'
        elif msg_id == 3:
            msg_type = 'not_interested'
        elif msg_id == 4:
            msg_type = 'have'
        elif msg_id == 5:
            msg_type = 'bitfield'
            bitfield = payload
            ba = bitarray.bitarray(endian='big')
            ba.frombytes(bitfield)
            for i in range(len(self.torrent.metainfo.info['pieces'])):
                if not ba.pop():
                    print('Missing piece: %x' % i)
        elif msg_id == 6:
            msg_type = 'request'
        elif msg_id == 7:
            msg_type = 'piece'
        elif msg_id == 8:
            msg_type = 'cancel'
        elif msg_id == 9:
            msg_type = 'port'
        else:
            raise PeerProtocolMessageTypeError(
                'Unrecognized message id: %s' % msg_id)

        print('%s received msg: id=%s type=%s payload=%s' %
              (self, msg_id, msg_type,
               ''.join('%02X' % v for v in payload)))


    @staticmethod
    def build_handshake(info_hash, peer_id):
        """<pstrlen><pstr><reserved><info_hash><peer_id>"""
        pstr = b'BitTorrent protocol'
        fmt = '!B%ds8x20s20s' % len(pstr)
        msg = struct.pack(fmt, len(pstr), pstr, info_hash, peer_id)
        return msg

    @staticmethod
    def decode_handshake(pstrlen, data):
        fmt = '!%ds8x20s20s' % pstrlen
        fields = struct.unpack(fmt, data)

        return {
            'pstr': fields[0].decode('utf-8'),
            'info_hash': fields[1],
            'peer_id': fields[2].decode('utf-8')
        }

    @staticmethod
    def decode_message(data):
        msg_id = int(data[0])
        payload = data[1:]

        return {
            'msg_id': msg_id,
            'payload': payload
        }


class AnnounceFailureError(Exception):
    pass


class AnnounceDecodeError(Exception):
    pass


class PeerProtocolError(Exception):
    pass


class PeerProtocolMessageTypeError(PeerProtocolError):
    pass