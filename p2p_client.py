import asyncio
import logging
import os
from torrent import Torrent
from socket_client import SocketClient
from socket_server import SocketServer
from kademlia.network import Server

# --- Kademlia Logging ---
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
log = logging.getLogger("kademlia")
log.addHandler(handler)
log.setLevel(logging.INFO)

# --- Network Constants  ---
SERVER_HOST = '0.0.0.0'
SERVER_PORT = 5000
KADEMLIA_PORT = 6881
KADEMLIA_HOST = '0.0.0.0'
BUFFER_SIZE = 4096
LENGTH_HEADER_SIZE = 8

class P2PClient:
    def __init__(self, kademlia_port, kademlia_host, is_seeder=False, torrent_file_path=None, seed_directory=None, server_host=None, server_port=None):
        self._kademlia_port = kademlia_port
        self._kademlia_host = kademlia_host

        self._kademlia_server = None
        self._torrent = None
        
        # State for file management
        self._is_seeder = is_seeder
        self._torrent_file_path = torrent_file_path
        self._seed_directory = seed_directory
        self._download_directory = 'downloads'
        self._file_statuses = {}  # Dictionary to track which files are complete
        self._file_data = {}      # Dictionary to hold file content
        
        # Initialize the asyncio lock for thread safety
        self._download_lock = asyncio.Lock()
        
        # Socket server details for clients to download torrent metadata
        self._server_host = server_host
        self._server_port = server_port

    async def connect_and_get_torrent(self):
        if self._is_seeder:
            # Seeder: Load the torrent file directly from the local path
            if not self._torrent_file_path or not os.path.exists(self._torrent_file_path):
                print(f"Error: Seeder torrent file not found at {self._torrent_file_path}")
                return False      
            
            self._torrent = Torrent(self._torrent_file_path)
            
            # The seeder loads all file content from the directory and marks as complete
            if not os.path.isdir(self._seed_directory):
                print(f"Error: Seeder directory '{self._seed_directory}' not found.")
                return False

            for file in self._torrent.torrent_files:
                file_path = os.path.join(self._seed_directory, file)
                if os.path.exists(file_path):
                    with open(file_path, 'rb') as f:
                        self._file_data[file] = f.read()
                    self._file_statuses[file] = True # Mark as complete
                else:
                    print(f"Error: Seeder file not found at {file_path}. Cannot seed.")
                    return False
            print(f"File Data: {self._file_data}")
            print(f"File Statuses: {self._file_statuses}")
            
            print(f"Seeder initialized with torrent from {self._torrent_file_path}")
            return True
        else:
            # Regular client: Download torrent file from the socket server
            if not self._server_host or not self._server_port:
                print("Error: Client requires a server host and port to download torrent metadata.")
                return False
            
            client = SocketClient(self._server_host, self._server_port)
            torrent_filename = self._torrent_file_path if self._torrent_file_path else "downloads/downloaded.torrent"
            if client.connect():
                if client.request_and_get_torrent_file(torrent_filename):
                    self._torrent = Torrent(torrent_filename)
                    if not os.path.exists(self._download_directory):
                        os.makedirs(self._download_directory)
                    for file in self._torrent.torrent_files:
                        self._file_statuses[file] = False # Client starts with no files
                        self._file_data[file] = b''      # Initialize with empty data
                    
                    print(f"File Data: {self._file_data}")
                    print(f"File Statuses: {self._file_statuses}")

                    return True
            return False

    async def run(self):
        # Initialize Kademlia server
        self._kademlia_server = Server()
        await self._kademlia_server.listen(self._kademlia_port, self._kademlia_host)
        print(f"Kademlia DHT client listening on {self._kademlia_host}:{self._kademlia_port}")
        
        # Bootstrap into the Kademlia DHT
        if self._torrent.bootstrap_nodes:
            decoded_nodes = [(host, port) for host, port in self._torrent.bootstrap_nodes]
            await self._kademlia_server.bootstrap(decoded_nodes)
            print("Kademlia bootstrap successful.")
        else:
            print("No DHT bootstrap nodes provided.")

        # Run the P2P server and the peer discovery loop concurrently
        peer_server_task = asyncio.create_task(self.start_peer_server())
        peer_discovery_task = asyncio.create_task(self.start_kademlia_peer_discovery())
        
        await asyncio.gather(peer_server_task, peer_discovery_task)

    async def start_peer_server(self):
        # Start the P2P server to handle incoming peer connections
        self._peer_server = await asyncio.start_server(
            self._handle_peer_server_connection,
            self._kademlia_host,
            self._kademlia_port
        )
        addr = self._peer_server.sockets[0].getsockname()
        print(f"Peer server started and listening on {addr}")
        
        async with self._peer_server:
            await self._peer_server.serve_forever()

    async def start_kademlia_peer_discovery(self):
        while True:
            # Check if all files are downloaded (for a client)
            is_download_complete = all(self._file_statuses.values())

            # ANNOUNCE OURSELVES TO THE DHT (the "set" call)
            if self._is_seeder or is_download_complete:
                info_hash_bytes = self._torrent.info_hash.encode('utf-8')
                await self._kademlia_server.set(
                    info_hash_bytes, 
                    f"{self._kademlia_host}:{self._kademlia_port}".encode('utf-8')
                )
                print(f"Announced availability for info_hash: {self._torrent.info_hash}")

            # FIND PEERS TO DOWNLOAD FROM (the "get" call)
            if not self._is_seeder and not is_download_complete:
                info_hash_bytes = self._torrent.info_hash.encode('utf-8')
                found_peer = await self._kademlia_server.get(info_hash_bytes)
                if found_peer:
                    print(f"Found peer: {found_peer}")
                    peer_info_str = found_peer.decode('utf-8')
                    peer_ip, peer_port_str = peer_info_str.split(':')
                    peer_port = int(peer_port_str)
                    # Don't try to connect to ourselves
                    if not (peer_ip == self._kademlia_host and peer_port == self._kademlia_port):
                        print(f"Connecting to peer {peer_ip}:{peer_port} to download files...")
                        asyncio.create_task(self._handle_peer_client_connection(peer_ip, peer_port))
                       
                # found_peers = await self._kademlia_server.get(info_hash_bytes)
                # if found_peers:
                #     print(f"Found peers: {found_peers}")
                #     for peer_info in found_peers:
                #         peer_info_str = peer_info.decode('utf-8')
                #         peer_ip, peer_port_str = peer_info_str.split(':')
                #         peer_port = int(peer_port_str)
                #         # Don't try to connect to ourselves
                #         if peer_ip != self._kademlia_host and peer_port != self._kademlia_port:
                #             asyncio.create_task(self._handle_peer_client_connection(peer_ip, peer_port))
                else:
                    print("No peers found yet. Will try again.")
            
            await asyncio.sleep(30) # Wait before trying again
    
    async def _handle_peer_server_connection(self, reader, writer):
        print("New incoming connection to peer server...")
        addr = writer.get_extra_info('peername')
        print(f"Accepted incoming connection from peer: {addr}")

        try:
            greeting = await reader.readuntil(b'\n')
            greeting_str = greeting.decode('utf-8').strip()
            if not greeting_str.startswith("HELLO:"):
                print(f"Invalid greeting from {addr}. Disconnecting.")
                return

            request = await reader.readuntil(b'\n')
            request_str = request.decode('utf-8').strip()
            
            if request_str.startswith("GET_FILE:"):
                requested_filename = request_str.split(":", 1)[1]
                
                async with self._download_lock:
                    if self._file_statuses.get(requested_filename, False) and self._file_data.get(requested_filename):
                        print(f"Peer {addr} is requesting file '{requested_filename}'. Sending...")
                        
                        file_data = self._file_data[requested_filename]
                        file_size = len(file_data)
                        
                        file_size_bytes = file_size.to_bytes(LENGTH_HEADER_SIZE, 'big')
                        writer.write(file_size_bytes)
                        writer.write(file_data)
                        await writer.drain()
                        print(f"Sent file '{requested_filename}' of size {file_size} to peer {addr}.")
                    else:
                        print(f"Peer {addr} requested file '{requested_filename}', but we do not have it yet. Disconnecting.")
            else:
                print(f"Peer {addr} sent an unknown request. Disconnecting.")

        except asyncio.IncompleteReadError:
            print(f"Peer {addr} disconnected unexpectedly.")
        except Exception as e:
            print(f"Error handling server connection from {addr}: {e}")
        finally:
            print(f"Closing server connection with {addr}")
            writer.close()
            await writer.wait_closed()
            
    async def _handle_peer_client_connection(self, peer_ip, peer_port):
        if self._is_seeder:
            return

        print(f"Attempting to connect to peer {peer_ip}:{peer_port} to download files...")
        
        try:
            reader, writer = await asyncio.open_connection(peer_ip, peer_port)
            addr = writer.get_extra_info('peername')
            print(f"Successfully connected to peer {addr}")

            our_greeting_message = f"HELLO:{self._torrent.info_hash}\n"
            writer.write(our_greeting_message.encode('utf-8'))
            await writer.drain()

            files_to_download = [file for file in self._torrent.torrent_files if not self._file_statuses.get(file)]
            
            for filename in files_to_download:
                request_message = f"GET_FILE:{filename}\n"
                writer.write(request_message.encode('utf-8'))
                await writer.drain()

                received_data = await self._receive_file_data(reader)

                if received_data:
                    async with self._download_lock:
                        file_path = os.path.join(self._download_directory, filename)
                        with open(file_path, 'wb') as f:
                            f.write(received_data)
                        self._file_statuses[filename] = True
                        self._file_data[filename] = received_data
                        print(f"Successfully downloaded and saved file '{filename}' from peer {addr}")
                else:
                    print(f"Failed to download file '{filename}' from peer {addr}")
                    break 
        except asyncio.IncompleteReadError:
            print(f"Peer {peer_ip}:{peer_port} disconnected unexpectedly.")
        except Exception as e:
            print(f"Error communicating with peer {peer_ip}:{peer_port}: {e}")
        finally:
            if writer:
                writer.close()
                await writer.wait_closed()

    async def _receive_file_data(self, reader):
        try:
            header_bytes = await reader.readexactly(LENGTH_HEADER_SIZE)
            total_data_size = int.from_bytes(header_bytes, 'big')
            print(f"Expecting to receive {total_data_size} bytes of data.")

            received_data = await reader.readexactly(total_data_size)
            return received_data
        except asyncio.IncompleteReadError:
            print("Peer disconnected while receiving file data.")
            return None
        except Exception as e:
            print(f"Error receiving file data: {e}")
            return None