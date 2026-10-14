# Lab 5 - Block Validation & Consensus Mechanisms

This module extends the custom blockchain engine with block-level validation, cryptographic block signatures, and consensus algorithms: **Proof-of-Authority (PoA)**, **Proof-of-Work (PoW)**, and **Proof-of-Stake (PoS)**.

---

## Architecture Overview

The system consists of two core modules:
- **`JCrypto.py`**: Cryptographic primitives providing 32-bit hashing, elliptic curve arithmetic, and Schnorr digital signatures.
- **`JChain.py`**: Core blockchain data structures (`State`, `Operation`, `Ledger`, `Block`, `Blockchain`) with integrated consensus rules and state transitions.

```
+--------------------------------------------------------------------------+
|                                Blockchain                                |
|                                                                          |
|  [ Genesis Block ] <--- [ Block 1 ] <--- [ Block 2 ] <--- ...            |
|       prev_hash: 0           prev_hash: H0      prev_hash: H1            |
|       fuzz: nonce            fuzz: nonce        fuzz: nonce              |
|       pubkey: V0             pubkey: V1         pubkey: V2               |
|       sig: Sign(V0)          sig: Sign(V1)      sig: Sign(V2)            |
+--------------------------------------------------------------------------+
                                     |
                                     v
+--------------------------------------------------------------------------+
|                              Consensus Engine                            |
|                                                                          |
|  * Proof-of-Authority (PoA):  pubkey in state["admin_keys"]              |
|  * Proof-of-Work (PoW):       Hash(block) < target                       |
|  * Proof-of-Stake (PoS):      Hash(block) < target * stake               |
+--------------------------------------------------------------------------+
                                     |
                                     v
+--------------------------------------------------------------------------+
|                           State & Operations                             |
|                                                                          |
|  * Transfer: Move tokens between accounts                                |
|  * Stake: Lock tokens into isolated variable 'stake_<pubkey>'            |
|  * Init / EnrolAdminKey / Snapshot                                       |
+--------------------------------------------------------------------------+
```

---

## 1. Cryptographic Engine (`JCrypto.py`)

### Hashing
- **`simple_hash(S)`**: A deterministic 32-bit hash function that takes a string $S$, computes its SHA-256 digest, and returns an integer in the range $[\![0, 2^{32}-1]\!]$.

### Elliptic Curve Arithmetic
- Custom Weierstrass curve: $y^2 \equiv x^3 + ax + b \pmod{p}$
  - Prime modulus: $p = 101239643$
  - Curve parameters: $a = 29717072$, $b = 16741874$
  - Base generator point $G = (22861771, 7928731)$, subgroup order $q = 101246273$
- **`EllipticCurve`**: Implements point addition (`add`) with vertical alignment and doubling cases, and scalar multiplication (`mul`) via Double-and-Add.
- **`EllipticPoint`**: Encapsulates homogeneous point representation $(x, y, z)$ with operator overloads (`+`, `-`, `*`).

### Schnorr Signature Scheme
- **`KeyGen()`**: Samples a private key $k \in [\![0, q-1]\!]$ and extracts the public key point $P = k \cdot G$ packed into a 64-bit integer.
- **`Sign(private_key, message)`**: Generates a signature pair $(s, e)$ where $e = \text{Hash}(r \cdot G \parallel \text{message})$ and $s = (r - k \cdot e) \bmod q$.
- **`Verify(public_key, message, signature)`**: Validates that $e = \text{Hash}((s \cdot G + e \cdot P) \parallel \text{message})$.

---

## 2. Blockchain Data Structures & Consensus (`JChain.py`)

### State (`State`)
A specialized dictionary storing the ledger state:
- Account balances: `<public_key> -> <integer_balance>`
- Administrator keys: `"admin_keys" -> [admin_pubkey_1, ...]`
- Validator stakes: `"stake_<public_key>" -> <staked_tokens>`

### Operations (`Operation`)
All operations are canonically serialized into JSON and signed by the initiator:
- **`is_valid(state)`**: Verifies cryptographic signature (`is_signature_valid()`), authorization permissions (`is_authorized(state)`), and business logic (`is_op_logic_valid(state)`).
- **`apply(state)`**: Mutates the current state dictionary.

#### Supported Operations:
| Operation | Authorization Rule | Logic Check | State Mutation |
|---|---|---|---|
| **`Transfer`** | `signer == content["source"]` | Source exists and has sufficient balance | `state[source] -= amount`, `state[target] += amount` |
| **`Stake`** | `signer == content["account"]` | Account exists, `amount > 0`, and balance $\ge$ amount | `state[account] -= amount`, `state["stake_" + account] += amount` |
| **`Init`** | `signer in state["admin_keys"]` | Variable not already defined | `state[name] = value` |
| **`EnrolAdminKey`** | `signer in state["admin_keys"]` (or uninitialized) | Key not already enrolled | Appends key to `state["admin_keys"]` |
| **`Snapshot`** | `signer in state["admin_keys"]` | Matches current state | Checkpoint verification |

---

### Block Structure & Validation (`Block`)

A block encapsulates:
- `content`: Block payload (raw string or a `Ledger` of operations).
- `prev_hash`: 32-bit hash of the preceding block.
- `fuzz`: Nonce integer used for partial collision mining.
- `public_key`: Identity of the validator node.
- `signature`: Schnorr signature over the block's canonical JSON representation (excluding the signature field).

#### Validation Methods:
- **`is_signature_valid()`**: Verifies that the block header was signed by the holder of `public_key`.
- **`is_authorized(state)`**: Verifies whether `public_key` belongs to `state["admin_keys"]` (Proof-of-Authority).
- **`get_stake(state)`**: Returns the validator's locked stake from `state["stake_<public_key>"]`.
- **`is_pos_valid(state, target)`**: Verifies that the validator has staked tokens (`stake > 0`) and satisfies the PoS challenge:
  $$\text{Hash}(\text{block}) < \text{target} \times \text{stake}$$
- **`is_valid(state, target=None)`**: Adapts validation automatically:
  - If `target` is provided: runs PoS validation.
  - If `target` is `None`: runs PoA signature and authorization checks.

---

### Blockchain Structure (`Blockchain`)

A sequential list of `Block` objects with chain-level verification:
- **`check_hashes()`**: Asserts that each block correctly references the hash of the preceding block (`b.prev_hash == prev_block.hash()`).
- **`hash()`**: Returns the terminal hash of the latest block in the chain.
- **`is_valid(starting_state, target=None)`**: Recursively checks:
  1. Hash pointer continuity across all blocks.
  2. Block-level validity (PoA or PoS depending on `target`).
  3. Payload validity (if the payload is a `Ledger`, validates each operation).
  4. Progressive state execution (`apply_ops`) to track balances and stakes block-by-block.

---

## 3. Consensus Algorithms & Mathematics

### Proof-of-Authority (PoA)
Block creation rights are restricted to an explicit set of authorized validator keys listed in `state["admin_keys"]`. Every block must contain a valid signature from one of these keys.

### Proof-of-Work (PoW) Difficulty Tuning
Mining consists of finding a nonce `fuzz` such that:
$$\text{Hash}(\text{block}) < \text{target}$$

Given that `simple_hash` outputs integers uniformly distributed over $[\![0, 2^{32}-1]\!]$:
- Probability of success per trial:
  $$p = \frac{\text{target}}{2^{32}}$$
- Expected trials until success (Geometric Distribution):
  $$\mathbb{E}[\text{trials}] = \frac{1}{p} = \frac{2^{32}}{\text{target}}$$
- Given a computer with hashrate $H$ (hashes/second), the expected mining time $T$ is:
  $$T = \frac{\mathbb{E}[\text{trials}]}{H} = \frac{2^{32}}{H \times \text{target}}$$
- To target an average block time of $T = 60\text{ seconds}$:
  $$\text{target} = \left\lfloor \frac{2^{32}}{60 \times H} \right\rfloor$$

### Proof-of-Stake (PoS)
To reduce computational waste, the difficulty threshold scales linearly with the validator's stake:
$$\text{Hash}(\text{block}) < \text{target} \times \text{stake}$$

- **Nodes without stake (`stake = 0`)** cannot validate any blocks.
- **High-stake nodes (`stake = 100`)** have a threshold 100 times larger than a node with `stake = 1`, making finding a valid nonce on average 100 times faster.

---

## 4. Usage Example

```python
import JChain, JCrypto, random

# 1. Setup Validator Identities
val1_priv, val1_pub = JCrypto.KeyGen()
val2_priv, val2_pub = JCrypto.KeyGen()

# 2. Initialize State with Balances
state = JChain.State({
    val1_pub: 10,
    val2_pub: 500
})

# 3. Stake Tokens
op1 = JChain.Operation.create({"op_type": "Stake", "amount": 1}, val1_priv)
op2 = JChain.Operation.create({"op_type": "Stake", "amount": 100}, val2_priv)

state = op1.apply(state)
state = op2.apply(state)

# 4. Mine Blocks under PoS (target = 2^24)
target = 2**24

def mine(content, priv_key, prev_hash, state, target):
    b = JChain.Block.create(content, priv_key, prev_hash=prev_hash)
    threshold = target * b.get_stake(state)
    while True:
        b.fuzz = random.randrange(2**32)
        b.signature = JCrypto.Sign(priv_key, b.json(include_signature=False))
        if b.hash() < threshold:
            break
    return b

# Block 1 mined by Validator 1 (stake = 1)
b1 = mine("Genesis Block", val1_priv, None, state, target)

# Block 2 mined by Validator 2 (stake = 100)
b2 = mine("Second Block", val2_priv, b1.hash(), state, target)

# 5. Verify Blockchain
chain = JChain.Blockchain([b1, b2])
print("Is blockchain valid?", chain.is_valid(state, target=target))  # True
```
