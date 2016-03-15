import socket
import time
import os
import logging

from pgbt.torrent_metainfo import TorrentMetainfo
from pgbt.torrent import Torrent
from pgbt.config import CONFIG

log = logging.getLogger(__name__)


class PgbtClient():
    def __init__(self, outdir=None):
        self.active_torrents = []
        self.finished_torrents = []
        self.outdir = outdir

    def add_torrent(self, filename):
        with open(filename, 'rb') as f:
            contents = f.read()

        # TODO: handle errors
        metainfo = TorrentMetainfo(contents)
        torrent = Torrent(metainfo, self.handle_completed_torrent)
        self.active_torrents.append(torrent)

    def handle_completed_torrent(self, torrent, data):
        print('Torrent completed!')
        if torrent.metainfo.info['format'] == 'SINGLE_FILE':
            self.save_single_file(torrent, data)
        else:
            self.save_multiple_file(torrent, data)

    def save_single_file(self, torrent, data):
        (_, filename) = os.path.split(torrent.metainfo.name)
        filepath = (os.path.join(os.path.expanduser(self.outdir), filename)
                    if self.outdir else filename)
        with open(filepath, 'wb') as f:
            f.write(data)
        log.info('save_single_file: %s' % filepath)

    def save_multiple_file(self, torrent, data):
        raise NotImplementedError

    def run_torrent(self):
        """Download first torrent from first peer in a single thread."""
        # \/ this is a hack \/
        torrent = self.active_torrents[0]
        torrent.start_torrent()
        peer = torrent.other_peers[0]
        peer.start_peer()

        peer.receive_handshake()

        def _drain_msgs():
            try:
                while True:
                    peer.receive_message()
            except socket.timeout:
                pass
        _drain_msgs()
        peer.send_message('interested')
        _drain_msgs()

        def _request_all_pieces():
            num_pieces = len(torrent.metainfo.info['pieces'])
            for i in range(num_pieces):
                if torrent.complete_pieces[i] is not None:
                    continue
                piece_length = torrent.metainfo.get_piece_length(i)
                for begin in range(0, piece_length, CONFIG['block_length']):
                    block_length = min(piece_length, CONFIG['block_length'])

                    peer.send_message(
                        'request', index=i, begin=begin, length=block_length)
                    _drain_msgs()

            for _ in range(10):
                if not any(v is None for v in torrent.complete_pieces):
                    break
                time.sleep(1)
                _drain_msgs()
                print('Missing pieces: %s' % torrent.piece_blocks)

        while not torrent.is_complete:
            _request_all_pieces()
