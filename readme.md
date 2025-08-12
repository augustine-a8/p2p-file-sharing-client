# P2P-File-Sharing-Client

A simplified peer-to-peer (P2P) file-sharing client demonstrating the fundamental concepts of a decentralized network. The project implements a custom protocol for file transfer and uses a Kademlia Distributed Hash Table (DHT) for peer discovery, all built on Python's `asyncio` framework for high-performance concurrency.

The goal of this project is to provide a clear, functional example of how P2P systems work, highlighting the roles of different nodes and the lifecycle of a shared file.

### Table of Contents

- [Features](#features)
- [How It Works](#how-it-works)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Running the Project](#running-the-project)
- [Dependencies](#dependencies)
- [License](#license)

### Features

- **Dual-Role Nodes:** Each instance of `P2PClient` can function as both a **seeder** (a node that provides files to others) and a **client** (a node that downloads files from others).
- **Decentralized Peer Discovery:** Utilizes a Kademlia DHT to find peers who are seeding a specific file, identified by a unique `info_hash` from the torrent metadata.
- **Multi-file Support:** Capable of handling torrents that contain a single file or a collection of files within a directory.
- **Simple Custom Protocol:** Implements a basic TCP-based protocol for exchanging messages and transferring files with a length-prefixed header.
- **`asyncio` Concurrency:** Leverages Python's `asyncio` for non-blocking I/O, allowing the client to manage multiple simultaneous connections and tasks efficiently.

### How It Works

The network lifecycle for a file transfer is as follows:

1.  **Metadata Acquisition:** A new client first connects to a centralized `SocketServer` to download the `.torrent` metadata file. The seeder node, having created this file, does not need this step.
2.  **Kademlia Bootstrap:** Using bootstrap nodes defined in the `.torrent` file, the `P2PClient` joins the Kademlia DHT. A seeder also joins to announce its availability.
3.  **Peer Discovery:** The client uses the `info_hash` from the torrent file to query the DHT, which returns a list of peers (seeders) that have the file content.
4.  **File Download:** The client connects directly to a discovered peer and requests a specific file by name. The seeder responds by sending the file data using the custom protocol.
5.  **Transition to Seeder:** Once a client has successfully downloaded a file, it can immediately start serving that file to other peers. Upon completing all downloads, the client announces its new status as a full seeder to the Kademlia DHT.

### Project Structure

- `src\main.py`: The entry point for the application. This script contains the `main()` function, where you can configure and start different P2P nodes (seeder or client).
- `src\p2p_client.py`: The core of the project. This file contains the `P2PClient` class definition, which encapsulates all the logic for a P2P node.
- `src\socket_server.py`: A simple server that acts as the initial entry point for clients, serving the `.torrent` metadata file.
- `src\socket_client.py`: A utility class for the `P2PClient` to communicate with the `socket_server` to get the initial torrent file.
- `src\torrent.py`: A class responsible for parsing the `.torrent` file, extracting its file list, `info_hash`, and Kademlia bootstrap nodes.
- `src\node.py`: A simple data class to represent a node (IP, port) in the Kademlia DHT.

### Getting Started

#### Prerequisites

- Python 3.7+

#### Installation

1.  Clone this repository to your local machine.

    ```bash
    git clone [https://github.com/augustine-a8/p2p-file-sharing-client.git](https://github.com/augustine-a8/p2p-file-sharing-client.git)
    cd p2p-file-sharing-client
    ```

2.  Install the necessary Python dependencies from the `requirements.txt` file:
    ```bash
    pip install -r requirements.txt
    ```

#### Running the Project

To simulate the network, you will need to run two separate terminal instances: one for the seeder node, and one for the client node.

**1. Seeder Node Setup:**

- Before you begin, use a tool like `py3createtorrent` to create a `.torrent` file for the directory containing the files you want to share.
- Run the `main.py` as a seeder. This node will start seeding immediately.
  ```bash
  python main.py seeder
  ```

**2. Client Node Setup:**

- Run the `main.py` as a client. This node will connect to the `socket_server`, download the `.torrent` file, find the seeder, and begin downloading the files.
  ```bash
  python main.py client
  ```

### Dependencies

- `bcoding`
- `bencode.py`
- `kademlia`
- `py3createtorrent`
- `rpcudp`
- `u-msgpack-python`

### License

This project is licensed under the MIT License.
