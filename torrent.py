from bcoding import bdecode, bencode
import hashlib
import os

### Torrent class to handle torrent file operations
### It reads the torrent file, extracts files and bootstrap nodes, and computes the info hash.

class Torrent(object):
    def __init__(self, path):
        self._torrent_path = path

        self._torrent_data = None
        self._torrent_files = []
        self._bootstrap_nodes = []
        self._info_hash = None

        self._extract_torrent_metadata()

    def _extract_torrent_metadata(self):
        if not os.path.exists(self._torrent_path):
            raise FileNotFoundError(f'Torrent file not found: {self._torrent_path}')
        
        if not os.path.isfile(self._torrent_path):
            raise ValueError(f'Torrent path is not a file: {self._torrent_path}')
        
        with open(self._torrent_path, 'rb') as f:
            self._torrent_data = bdecode(f.read())

        files = self._torrent_data.get('info', {}).get('files', [])
        if len(files) > 0:
            for file in files:
                path_list = file.get('path', [])
                if len(path_list) > 0:
                    file_name = path_list[0]
                    self._torrent_files.append(file_name)

        nodes = self._torrent_data.get('nodes', [])
        if len(nodes) > 0:
            for node in nodes:
                if len(node) == 2:
                    ip_addr = node[0]
                    port = node[1]
                    
                    self._bootstrap_nodes.append((ip_addr, port))
        
        torrent_info = self._torrent_data.get('info', {})
        if torrent_info:
            info_hash = hashlib.sha1(bencode(torrent_info)).digest()
            self._info_hash = info_hash.hex()

    @property
    def torrent_files(self):
        return self._torrent_files
    
    @property
    def bootstrap_nodes(self):
        return self._bootstrap_nodes
    
    @property
    def info_hash(self):   
        return self._info_hash
