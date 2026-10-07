# Lab 4 - Decentralization: Interactive Blockchain Node

This lab implements a decentralized peer-to-peer (P2P) interactive node (`Node.py`) capable of discovering peers, storing and validating a blockchain, broadcasting and validating cryptographic operations, and mining/propagating new blocks across a local network.

It relies on:
- `JChain.py`: Blockchain data structures (`Blockchain`, `Block`, `Ledger`, `Operation`, `State`).
- `JCrypto.py`: Cryptographic primitives (Schnorr signatures, elliptic curve arithmetic, 32-bit hashing, key pair generation).

---

## Architecture Overview

Each running node maintains:
1. **Cryptographic Identity**: A Schnorr key pair (`privkey`, `pubkey`) generated on startup.
2. **Local Blockchain & State**: An instance of `Blockchain` and its materialized `State` (account balances, administrative permissions).
3. **Mempool (`pending_ops`)**: A list of pending operations received or created locally, awaiting validation and block inclusion.
4. **Peer Registry (`peers`)**: A dynamic list of known `(host, port)` peer addresses.
5. **Multi-threaded Networking**: A background listener socket accepting incoming TCP connections and a synchronous client sending JSON-serialized messages.

```
+-----------------------------------------------------------+
|                          Node                             |
|                                                           |
|  Identity: (privkey, pubkey)                              |
|  Mempool:  pending_ops = [op1, op2, ...]                  |
|  Ledger:   Blockchain = [Block 0, Block 1, ...]           |
|  State:    {'admin_keys': [...], <pubkey>: <balance>, ..} |
+-----------------------------------------------------------+
            ^                                   |
            | JSON over TCP                     | JSON over TCP
            v                                   v
        +-------+                           +-------+
        | Peer  |                           | Peer  |
        +-------+                           +-------+
```

---

## Getting Started

### Prerequisites
- Python 3.8+

### Launching a Node

```bash
python Node.py <port> [peer_port_1] [peer_port_2] ...
```

- `<port>`: Port number the node will bind to and listen on.
- `[peer_port_X]`: Optional initial peer ports on `localhost` to connect to upon startup.

#### Example (3-node network):
Open 3 separate terminal windows:

```bash
# Terminal 1: Node 1 listening on 8001
python Node.py 8001

# Terminal 2: Node 2 listening on 8002, connects to 8001
python Node.py 8002 8001

# Terminal 3: Node 3 listening on 8003, connects to 8002
python Node.py 8003 8002
```

---

## Interactive Command Reference

Once a node is running, an interactive prompt `> ` is available. The commands are grouped below by category:

### 1. Peer & Network Management

| Command | Description | Example |
|---|---|---|
| `peers` | Display the list of currently known peer addresses. | `peers` |
| `connect <port>` | Manually connect to a node at `('localhost', <port>)` and send a `HELLO` handshake. | `connect 8002` |
| `disconnect <port>` | Disconnect from a peer and notify it with a `BYE` message. | `disconnect 8002` |
| `discover <port>` | Request the peer list from a known node (`GET_PEERS`) and connect to any newly discovered peers. | `discover 8002` |
| `test` | Broadcast a test message (`TEST`) to all known peers. | `test` |

### 2. Blockchain & State Inspection

| Command | Description | Example |
|---|---|---|
| `Blockchain` | Print the full local blockchain and its blocks. | `Blockchain` |
| `state` | Display the current materialized ledger state (accounts, balances, admin keys). | `state` |
| `pending` | List all operations currently waiting in the mempool (`pending_ops`). | `pending` |
| `check` | Verify internal chain integrity (`check_hashes()`) and display the local terminal hash. | `check` |
| `compare <port>` | Request the peer's terminal block hash (`GET_HASH`) and compare it with the local chain. | `compare 8002` |
| `getchain <port>` | Fetch the full chain from a peer (`GET_CHAIN`) and replace the local chain if the remote chain is longer and valid. | `getchain 8002` |
| `mykey` | Print the node's own public key (used for receiving tokens or admin enrollment). | `mykey` |
| `exit` | Terminate the node. | `exit` |

### 3. Transactions & Block Mining

| Command | Description | Example |
|---|---|---|
| `admin <key \| me>` | Create and broadcast an `EnrolAdminKey` operation. Use `admin me` to enroll the current node. | `admin me` |
| `init <account \| me> <amount>` | Create and broadcast an `Init` operation setting initial balance for an account (requires admin authorization). | `init me 100` |
| `transfer <target> <amount>` | Create and broadcast a signed `Transfer` operation transferring tokens from the node's account to a target. | `transfer 268319290 25` |
| `snapshot` | Create and broadcast a `Snapshot` operation recording the current state. | `snapshot` |
| `validate` | Check all pending operations in the mempool for validity against current state, removing invalid ones. | `validate` |
| `mine` | Validate pending operations, package them into a new `Block`, append it locally, update state, and broadcast `NEW_BLOCK` to the network. | `mine` |

---

## Network Protocol & Message Types

Nodes exchange JSON messages over TCP connections:

| Message Type | Direction | Payload Fields | Purpose |
|---|---|---|---|
| `HELLO` | Sender -> Peer | `type`, `from` | Announces presence; the receiver adds the sender to its peer list. |
| `BYE` | Sender -> Peer | `type`, `from` | Graceful exit notification; receiver removes the sender from its peer list. |
| `GET_PEERS` | Node -> Peer | `type`, `from` | Requests the recipient's known peer list. |
| `PEERS` | Peer -> Node | `type`, `from`, `peers` | Returns known peers; receiver contacts newly discovered peers. |
| `GET_HASH` | Node -> Peer | `type`, `from` | Requests the hash of the latest block in the recipient's chain. |
| `HASH` | Peer -> Node | `type`, `from`, `hash` | Returns the latest block hash for consistency comparison. |
| `GET_CHAIN` | Node -> Peer | `type`, `from` | Requests the complete blockchain. |
| `CHAIN` | Peer -> Node | `type`, `from`, `Blockchain` | Sends the full chain; receiver validates and syncs if longer. |
| `NEW_OP` | Node -> All Peers | `type`, `from`, `op` | Propagates a newly created operation to all mempools. |
| `NEW_BLOCK` | Miner -> All Peers | `type`, `from`, `block` | Propagates a newly mined block; peers validate and append it. |

---
