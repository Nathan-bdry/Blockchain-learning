# Lab 7 - Networked Blockchain Application

This lab runs a peer-to-peer blockchain node. Each node keeps a signed chain, a mempool of pending operations, and a materialized account state. Nodes exchange JSON messages over TCP and can report their status to a monitor.

It relies on:
- `Node.py`: Networking, the interactive prompt, and chain synchronization.
- `JChain.py`: Blockchain data structures (`Blockchain`, `Block`, `Operation`, `State`) and the `Transfer`, `Init`, `EnrolAdminKey`, and `Snapshot` operations.
- `JCrypto.py`: Schnorr signatures, elliptic-curve arithmetic, and the 32-bit hash.
- `config.json`: Identity, listen address, monitor, peer limit, and genesis block.

---

## Architecture Overview

Each running node maintains:
1. **Cryptographic identity**: A Schnorr key pair loaded from `config.json`. The public key is derived with `JCrypto.ExtractPublicKey`.
2. **Local chain and state**: The chain starts from the genesis block. `Blockchain.state` applies every operation to build balances.
3. **Mempool**: Pending operations keyed by their hash, waiting to be included in a block.
4. **Peer list**: Known `host:port` addresses, capped by `max_peers`.
5. **Background listener**: A daemon thread accepts TCP connections and dispatches JSON messages.

```
+-----------------------------------------------------------+
|                          Node                             |
|                                                           |
|  Identity: (priv_key, pub_key)                            |
|  Mempool:  {op_hash: Operation, ...}                      |
|  Ledger:   Blockchain = [Genesis, Block 1, ...]           |
|  State:    {<pubkey>: <balance>, ...}                     |
|  Peers:    ["host:port", ...]                             |
+-----------------------------------------------------------+
            ^                                   |
            | JSON over TCP                     | JSON over TCP
            v                                   v
        +-------+                           +----------+
        | Peer  |                           | Monitor  |
        +-------+                           +----------+
```

---

## Getting Started

### Prerequisites
- Python 3.8+

### Configuration

`Node.py` loads a JSON file. Paths that contain spaces must be quoted in PowerShell.

| Field | Type | Role |
|---|---|---|
| `priv_key` | integer | Schnorr private key for this node. |
| `address` | `"host:port"` | Address advertised to peers. The node binds to this port on all interfaces. |
| `monitor` | `"host:port"` | Address that receives status logs. An empty value disables reporting. |
| `max_peers` | integer | Maximum number of stored peers. |
| `genesis` | object | Signed genesis block. See the shape below. |

The genesis block must match `Block.from_dict`: operations and `prev_hash` live under `content`, and the block signature sits next to `public_key`.

```json
{
  "priv_key": 1,
  "address": "127.0.0.1:8001",
  "monitor": "127.0.0.1:9000",
  "max_peers": 10,
  "genesis": {
    "content": {
      "operations": [
        {
          "content": {
            "amount": 1000000,
            "name": 13828789712027994,
            "op_type": "Init"
          },
          "public_key": 13828789712027994,
          "signature": 132430957655536018
        }
      ],
      "prev_hash": null
    },
    "public_key": 13828789712027994,
    "signature": 25547002671408163
  }
}
```

`Init` creates the account named by `name` and sets its balance to `amount`. In the sample genesis, that account is the public key `13828789712027994` with a balance of `1000000`.

### Launching a Node

From this directory:

```bash
python Node.py config.json
```

On startup the node prints `JChain v1.0 loaded`, binds its listen port, sends a `STATUS` message to the monitor, and opens the `>` prompt.

---

## Interactive Command Reference

### 1. Peer and network management

| Command | Description | Example |
|---|---|---|
| `add_peer <host:port>` | Store a peer and send `HELLO`. Ignored when the peer list is full, the peer is already known, or the address is this node. | `add_peer 10.224.1.20:8001` |
| `peers` | Print known peer addresses. | `peers` |
| `ask_peers` | Broadcast `PEER_REQUEST`. Each peer replies with `KNOWN_PEERS`. | `ask_peers` |
| `purge_peers` | Broadcast `PING`, then clear the local peer list. Peers that answer `HELLO` are added again. | `purge_peers` |
| `ask_stats` | Broadcast `STAT_REQUEST`. A peer with a longer chain is asked for `CHAIN_REQUEST` when its `NEW_STATS` arrives. | `ask_stats` |
| `req_chain <host:port>` | Ask one peer for its full chain. | `req_chain 10.224.1.20:8001` |
| `test` | Broadcast a `TEST` message. | `test` |
| `status` | Send the current public key, address, chain length, and chain hash to the monitor. | `status` |

### 2. Chain and state inspection

| Command | Description | Example |
|---|---|---|
| `whoami` | Print this node's public key and listen address. | `whoami` |
| `balance` | Print this node's balance, or `0` if the public key is absent from the state. | `balance` |
| `state` | Print the full state dictionary. | `state` |
| `chain` | Print the chain length and the hash of the latest block. | `chain` |
| `full_chain` | Print every block as JSON. | `full_chain` |
| `block <num>` | Print the block at that index. Index `0` is the genesis block. | `block 0` |
| `mempool` | Print pending operations. | `mempool` |
| `help` | Print the built-in command list. | `help` |
| `exit` | Stop the process. | `exit` |

### 3. Transactions and blocks

| Command | Description | Example |
|---|---|---|
| `transfer <amount> <pub_key>` | Sign a `Transfer` from this node to `pub_key`, store it in the mempool, and broadcast `NEW_OP`. | `transfer 10 13828789712027994` |
| `create_block` | Append a block containing every mempool operation that passes `is_valid` and is not already in the chain. The mempool is then cleared. The block is signed with this node's private key, the local state is updated, and `NEW_STATS` is broadcast. | `create_block` |
| `purge_pool` | Drop every pending operation without creating a block. | `purge_pool` |

A `Transfer` is authorized only when the signer public key equals `source`, and only when `source` exists in the state with a balance greater than or equal to `amount`.

---

## Network Messages

All messages are JSON objects with a `type` field. The listener reads one chunk of up to 8192 bytes per connection.

| Type | Direction | Effect |
|---|---|---|
| `HELLO` | peer to peer | Add the sender to the peer list without sending another hello. |
| `PEER_REQUEST` | peer to peer | Reply with `KNOWN_PEERS`. |
| `KNOWN_PEERS` | peer to peer | Add each listed address, sending `HELLO` to new peers. |
| `PING` | peer to peer | Reply with `HELLO`. |
| `STAT_REQUEST` | peer to peer | Reply with `NEW_STATS` (length and hash of the local chain). |
| `NEW_STATS` | peer to peer | If the remote length is greater, send `CHAIN_REQUEST`. |
| `CHAIN_REQUEST` | peer to peer | Reply with `NEW_CHAIN` and the local chain JSON. |
| `NEW_CHAIN` | peer to peer | Replace the local chain when the received chain is longer and `check_hashes()` succeeds, then recompute state and report status. |
| `NEW_OP` | peer to peer | If the signature is valid and the hash is new, store the operation and relay it. |
| `TEST` | peer to peer | Print the sender address. |
| `STATUS` | node to monitor | Public key, address, chain length, and chain hash. |

`check_hashes()` only checks that each block's `prev_hash` equals the hash of the previous block. The genesis block must use `prev_hash: null`.

---

## Operations

| Operation | Authorization | Logic check | State change |
|---|---|---|---|
| `Transfer` | Signer public key equals `source` | `source` exists and its balance is at least `amount` | Debit `source`, credit `target` (created at `0` if missing) |
| `Init` | Signer is listed in `state["admin_keys"]` | `name` is not already in the state | `state[name] = amount` |
| `EnrolAdminKey` | No admin list yet, or the signer is already an admin | `key` is not already enrolled | Append `key` to `state["admin_keys"]` |
| `Snapshot` | Signer is an admin | `content["state"]` equals the current state | Returns `self.state` |

`create_block` keeps an operation only when `is_valid` succeeds. That method requires a valid signature, a passing authorization check, and a passing logic check. `NEW_OP` checks the signature before the operation enters the mempool. Rebuilding state from a received chain applies each operation directly.

---

## Files

| File | Role |
|---|---|
| `Node.py` | Process entry point, TCP server, prompt, and message handlers. |
| `JChain.py` | Blocks, chain hashing, state transitions, and operation classes. |
| `JCrypto.py` | Key derivation, Schnorr `Sign` / `Verify`, and `simple_hash`. |
| `config.json` | Local node settings and the genesis block. |
