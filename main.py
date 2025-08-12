import asyncio
import sys
from p2p_client import P2PClient

async def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <mode>")
        print("Modes: seeder, client")
        return

    mode = sys.argv[1].lower()
    match mode:
        case 'seeder':
            print("Starting in seeder mode.")
            seeder_torrent_path = 'seeder_files/my_torrent.torrent'
            seeder_seed_dir = 'seeder_files'
            seeder_node = P2PClient(
                kademlia_port=6881, 
                kademlia_host='0.0.0.0', 
                is_seeder=True, 
                torrent_file_path=seeder_torrent_path,
                seed_directory=seeder_seed_dir
            )
            
            if await seeder_node.connect_and_get_torrent():
                await asyncio.gather(
                    seeder_node.start_peer_server(), 
                    seeder_node.start_kademlia_and_find_peers()
                )
            else:
                print("Seeder setup failed.")
        case 'client':
            print("Starting in client mode.")
            client_torrent_path = 'downloads/downloaded.torrent'
            client_node = P2PClient(
                kademlia_port=6882,
                kademlia_host='0.0.0.0',
                is_seeder=False,
                torrent_file_path=client_torrent_path,
                server_host='127.0.0.1',
                server_port=5000
            )

            if await client_node.connect_and_get_torrent():
                await asyncio.gather(
                    client_node.start_peer_server(),
                    client_node.start_kademlia_and_find_peers()
                )
            else:
                print("Client setup failed.")
        case _:
            print("Invalid mode. Use 'seeder' or 'client'.")
            sys.exit(1)


def test_torrent():
    """
    Test the Torrent class functionality.
    This function reads a torrent file and prints its details.
    """
    from torrent import Torrent

    if len(sys.argv) < 3:
        print("Usage: python main.py test_torrent <torrent_file_path>")
        return
    
    torrent_file_path = sys.argv[2]
    if not torrent_file_path.endswith('.torrent'):
        print(f"Provided file is not a .torrent file: {torrent_file_path}")
        return
    
    try:
        t = Torrent(torrent_file_path)
        print(f"Torrent Files: {t.torrent_files}")
        print(f"Boostrap Nodes: {t.bootstrap_nodes}")
        print(f"Info Hash: {t.info_hash}")
    except Exception as e:
        print(f"Error reading torrent file. {e}")


def test_socket_server():
    """
    Test the socket server functionality.
    This function initializes a SocketServer instance and starts it with a sample torrent file.
    It assumes the torrent file exists at 'seeder_files/my_torrent.torrent'.
    """
    from socket_server import SocketServer
    
    server = SocketServer(port=5000)
    if server.start('seeder_files/test.torrent'):
        print("Socket server started successfully.")
    else:
        print("Failed to start socket server.")

def test_socket_client():
    """
    Test the socket client functionality.
    This function connects to the socket server and requests a file.
    """
    from socket_client import SocketClient
    host='127.0.0.1'
    port=5000
    client = SocketClient(server_host=host, server_port=port)
    try:
        if client.connect():
            client.request_and_get_torrent_file(save_as_filename='downloads/received_torrent.torrent')
            print("Torrent file received successfully.")
        else:
            print("Failed to connect to server.")
    except Exception as e:
        print(f"An error occurred: {e}")
    
async def test_p2p_client():
    """
    Test the P2PClient functionality.
    This function initializes a P2PClient instance and connects to a torrent.
    """
    from p2p_client import P2PClient

    if len(sys.argv) < 3:
        print("Usage: python main.py test_p2p_client <mode>")
        print("Modes: seeder, client")
        return
    
    mode = sys.argv[2].lower()
    match mode:
        case 'seeder':
            print("Starting in seeder mode.")
            seeder_torrent_path = 'seeder_files/test.torrent'
            seeder_seed_dir = 'seeder_files'
            seeder_node = P2PClient(
                kademlia_port=6881, 
                kademlia_host='0.0.0.0',
                is_seeder=True,
                torrent_file_path=seeder_torrent_path,
                seed_directory=seeder_seed_dir,
                server_host='0.0.0.0',
                server_port=5000,
            )
            
            if await seeder_node.connect_and_get_torrent():
                print("Seeder setup successful. Starting peer server and Kademlia.")
                await seeder_node.run()
            else:
                print("Seeder setup failed.")

        case 'another_seeder':
            print("Starting in seeder mode.")
            seeder_torrent_path = 'seeder_files/test.torrent'
            seeder_seed_dir = 'seeder_files'
            seeder_node = P2PClient(
                kademlia_port=6882, 
                kademlia_host='0.0.0.0',
                is_seeder=True,
                torrent_file_path=seeder_torrent_path,
                seed_directory=seeder_seed_dir,
                server_host='0.0.0.0',
                server_port=5000,
            )
            
            if await seeder_node.connect_and_get_torrent():
                print("Seeder setup successful. Starting peer server and Kademlia.")
                await seeder_node.run()
            else:
                print("Seeder setup failed.")

        case 'client':
            print("Starting in client mode.")
            client_torrent_path = 'downloads/downloaded.torrent'
            client_node = P2PClient(
                kademlia_port=6883,
                kademlia_host='0.0.0.0',
                is_seeder=False,
                torrent_file_path=client_torrent_path,
                server_host='127.0.0.1',
                server_port=5000,
            )

            if await client_node.connect_and_get_torrent():
                print("Client setup successful. Starting peer server and Kademlia.")
                await client_node.run()
            else:
                print("Client setup failed.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <mode> | <test_torrent> | <test_socket_server> | <test_socket_client>")
        sys.exit(1)

    mode = sys.argv[1].lower()

    match mode:
        case 'test_torrent':
            test_torrent()
        case 'test_socket_server':
            test_socket_server()
        case 'test_socket_client':
            test_socket_client()
        case 'test_p2p_client':
            try:
                asyncio.run(test_p2p_client())
            except KeyboardInterrupt:
                print("Test P2P Client interrupted.")
        case _:
            print("Invalid mode. Use 'test_torrent', 'test_socket_server', or 'test_socket_client'.")
            sys.exit(1)


# if __name__ == "__main__":
#     try:
#         asyncio.run(main())
#     except KeyboardInterrupt:
#         print("Application shutting down.")
