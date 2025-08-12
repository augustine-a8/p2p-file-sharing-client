import socket
import os
import time

SERVER_HOST = '127.0.0.1' # Or your server's LAN IP (e.g., '192.168.1.10') or public IP
SERVER_PORT = 5000
BUFFER_SIZE = 4096
LENGTH_HEADER_SIZE = 8 # Must match server's LENGTH_HEADER_SIZE

class SocketClient:
    def __init__(self, server_host=SERVER_HOST, server_port=SERVER_PORT):
        self._server_host = server_host
        self._server_port = server_port
        self._client_socket = None

    def connect(self):
        try:
            self._client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._client_socket.connect((self._server_host, self._server_port))
            print(f"Connected to server at {self._server_host}:{self._server_port}")
            return True
        except ConnectionRefusedError:
            print(f"Error: Connection refused. Is the server running on {self._server_host}:{self._server_port}?")
            return False
        except socket.timeout:
            print(f"Error: Connection timed out when connecting to {self._server_host}:{self._server_port}.")
            return False
        except Exception as e:
            print(f"An unexpected error occurred during connection: {e}")
            return False

    def receive_data_with_header(self, expected_size=None):
        # This function handles receiving data where the first LENGTH_HEADER_SIZE
        # bytes indicate the total size of the data to follow.
        
        # Receive the length header
        header_bytes = b''
        while len(header_bytes) < LENGTH_HEADER_SIZE:
            chunk = self._client_socket.recv(LENGTH_HEADER_SIZE - len(header_bytes))
            if not chunk:
                print("Server disconnected while receiving header.")
                return None
            header_bytes += chunk
        
        try:
            total_data_size = int.from_bytes(header_bytes, 'big')
            print(f"Expecting to receive {total_data_size} bytes of data.")
        except ValueError:
            print("Received invalid length header from server.")
            return None

        # Receive the actual data
        received_data = b''
        bytes_received = 0
        
        while bytes_received < total_data_size:
            # Calculate how much more data we need
            bytes_to_receive = min(BUFFER_SIZE, total_data_size - bytes_received)
            chunk = self._client_socket.recv(bytes_to_receive)
            
            if not chunk:
                print(f"Server disconnected unexpectedly before receiving all data. Received {bytes_received}/{total_data_size} bytes.")
                return None
            
            received_data += chunk
            bytes_received += len(chunk)
            
            
        return received_data

    def request_and_get_torrent_file(self, save_as_filename="received_torrent.torrent"):
        if not self._client_socket:
            print("Not connected to server.")
            return False

        try:
            welcome_message = self._client_socket.recv(1024).decode('utf-8')
            print(f"Server says: {welcome_message.strip()}")
            if "GET_TORRENT" not in welcome_message:
                print("Server did not send expected welcome message. Protocol mismatch?")
                return False

            self._client_socket.sendall(b"GET_TORRENT\n") # Send with newline as server might expect
            print("Sent 'GET_TORRENT' request.")

            torrent_data = self.receive_data_with_header()

            if torrent_data is None:
                print("Failed to receive torrent data.")
                return False

            try:
                with open(save_as_filename, 'wb') as f:
                    f.write(torrent_data)
                print(f"Successfully received and saved torrent file to {save_as_filename}")
                return True
            except Exception as e:
                print(f"Error saving torrent file: {e}")
                return False

        except socket.error as e:
            print(f"Socket error during torrent file transfer: {e}")
            return False
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return False
        finally:
            self.disconnect()

    def disconnect(self):
        if self._client_socket:
            print("Disconnecting from server.")
            self._client_socket.close()
            self._client_socket = None