import socket
import threading
import time
import os
import sys

HOST = '0.0.0.0'
PORT = 5000
BUFFER_SIZE = 4096
LENGTH_HEADER_SIZE = 8 # Bytes to represent file size (e.g., up to 2^64 bytes)

class SocketServer:
    def __init__(self, host=HOST, port=PORT):
        self._host = host
        self._port = port
        self._server_socket = None
        self._is_running = False
        self._connected_clients = {} # Use a dict to store sockets, maybe by addr or a unique ID
        self._client_lock = threading.Lock() # Protect access to _connected_clients

    def start(self, torrent_file_path):
        if not torrent_file_path.endswith('.torrent'):
            raise ValueError(f"Error: The file {torrent_file_path} is not a torrent file.")
        
        if not os.path.isfile(torrent_file_path):
            raise FileNotFoundError(f"Error: The file {torrent_file_path} does not exist.")
        
        try:
            with open(torrent_file_path, 'rb') as f:
                self._torrent_file_data = f.read()
            self._torrent_file_path = torrent_file_path
            self._torrent_file_size = len(self._torrent_file_data)
        except FileNotFoundError:
            print(f"Error: The file {torrent_file_path} does not exist.")
            return False
        except Exception as e:
            print(f"Error reading file {torrent_file_path}: {e}")
            return False

        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.bind((self._host, self._port))
        self._server_socket.listen(5)
        self._server_socket.settimeout(1.0) # Set a timeout for accept()
        self._is_running = True
        print(f"Server started on {self._host}:{self._port}")

        # Start the thread to accept connections
        accept_thread = threading.Thread(target=self._accept_connections)
        accept_thread.daemon = True # Allows main program to exit when main thread ends
        accept_thread.start()
        

        print("Server is running. Press Ctrl+C to stop.")
        try:
            while self._is_running:
                time.sleep(1) # Keep main thread alive
        except KeyboardInterrupt:
            self._stop()
        
        return True

    def _accept_connections(self):
        while self._is_running:
            try:
                client_socket, addr = self._server_socket.accept()
                print(f"Accepted connection from {addr}")
                
                # Start a new thread for each client
                # This thread will handle receiving requests and sending data to THIS specific client.
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, addr)
                )
                client_thread.daemon = True
                client_thread.start()
                
                with self._client_lock:
                    self._connected_clients[addr] = client_socket # Store the socket
                    print(f"Total active clients: {len(self._connected_clients)}")

            except socket.timeout: # This is why we set a timeout on server_socket.accept()
                continue # No new connection, just check _is_running again
            except socket.error as e:
                if self._is_running: # Only print error if server is still supposed to be running
                    print(f"Socket error in accept_connections: {e}")
                break # Exit loop if server socket is closed or unrecoverable error
            except Exception as e:
                print(f"Unexpected error in accept_connections: {e}")
                break

    def _handle_client(self, client_socket, addr):
        try:
            client_socket.sendall(b"Welcome to the torrent server! Type 'GET_TORRENT' to receive the file.\n")

            # Simple protocol: wait for client to request the torrent
            while True:
                request = client_socket.recv(1024).decode('utf-8').strip().upper()
                if not request: # Client disconnected
                    print(f"Client {addr} disconnected during receive.")
                    break
                
                if request == "GET_TORRENT":
                    print(f"Client {addr} requested the torrent file.")
                    self._send_torrent_file_to_client(client_socket, addr)
                    break # Client is done after receiving the torrent
                else:
                    client_socket.sendall(b"Unknown command. Type 'GET_TORRENT'.\n")

        except ConnectionResetError:
            print(f"Client {addr} forcefully disconnected.")
        except BrokenPipeError: # Linux/macOS equivalent of ConnectionResetError sometimes
            print(f"Client {addr} pipe broken.")
        except Exception as e:
            print(f"Error handling client {addr}: {e}")
        finally:
            print(f"Closing client connection {addr}")
            with self._client_lock:
                if addr in self._connected_clients:
                    del self._connected_clients[addr] # Remove from tracking list
            client_socket.close()

    def _send_torrent_file_to_client(self, client_socket, addr):
        try:
            # Send file size first
            file_size_bytes = self._torrent_file_size.to_bytes(LENGTH_HEADER_SIZE, 'big')
            client_socket.sendall(file_size_bytes)
            print(f"Sent file size ({self._torrent_file_size} bytes) header to {addr}")

            # Send the torrent file data in chunks
            client_socket.sendall(self._torrent_file_data)
            print(f"Sent torrent file '{self._torrent_file_path}' to {addr}")

        except ConnectionResetError:
            print(f"Client {addr} disconnected during file transfer.")
        except BrokenPipeError:
            print(f"Client {addr} pipe broken during file transfer.")
        except Exception as e:
            print(f"Error sending torrent file to {addr}: {e}")

    def _stop(self):
        if self._is_running:
            self._is_running = False
            # Try to gracefully close client connections first
            with self._client_lock:
                for addr, client_socket in list(self._connected_clients.items()): # Iterate a copy
                    try:
                        client_socket.shutdown(socket.SHUT_RDWR) # Disable further sends/receives
                        client_socket.close()
                    except Exception as e:
                        print(f"Error closing client {addr}: {e}")
                self._connected_clients.clear()
            
            # Close the server socket last
            try:
                self._server_socket.shutdown(socket.SHUT_RDWR)
            except OSError as e: # Handle "not connected" or "socket is not connected" error
                print(f"Error shutting down server socket (might be already closed): {e}")
            finally:
                self._server_socket.close()
            print("Server stopped.")


def main():
    if len(sys.argv) < 2:
        print("Usage: python socket_server.py <torrent_file_path>")
        sys.exit(1)

    torrent_file_path = sys.argv[1]
    try:
        server = SocketServer(HOST, PORT)
        if server.start(torrent_file_path):
            print("Socket server started successfully.")
        else:
            print("Failed to start socket server.")
    except Exception as e:
        print(f"Error starting socket server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Server shutting down.")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        print("Exiting application.")
