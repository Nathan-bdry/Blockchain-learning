# Lab 3 - Digital Signatures & Cryptographic Authority

This lab integrates asymmetric cryptography and digital signatures into the blockchain framework to provide authentication, non-repudiation, and access control.

## Overview

Transactions and governance operations are signed using a Schnorr signature scheme over an elliptic curve. The blockchain verifies both hash chain integrity and cryptographic validity of every operation.

## Key Components

### 1. Cryptographic Primitives
- **Elliptic Curve Arithmetic**: `EllipticCurve` and `EllipticPoint` implementing point addition, point doubling, and scalar multiplication over a finite field.
- **Schnorr Signatures**:
  - `KeyGen()`: Generates private/public key pairs (`privkey`, `pubkey`).
  - `Sign(private_key, message)`: Produces a cryptographic Schnorr signature `(s, e)`.
  - `Verify(public_key, message, signature)`: Validates the signature against the sender's public key.

### 2. Operations with Cryptographic Permissions
- **`Transfer`**: Requires a valid signature and verifies that `public_key == source` with sufficient balance.
- **`EnrolAdminKey`**: Enrolls a new administrator public key; restricted to existing administrator keys.
- **`Init`**: Initializes account tokens; restricted to administrator keys.
- **`Genesis`**: Unsigned bootstrap operation defining root authority and initial state on an empty chain.
- **`Snapshot`**: Records a validated checkpoint of the current state.

### 3. Blockchain & Validation
- **`Block`**: Encapsulates operations and previous block hashes with deterministic canonical JSON serialization.
- **`Blockchain`**:
  - `add_block(content)`: Appends a new block linked to the preceding block hash.
  - `apply_ops(starting_state)`: Computes the updated state across all blocks.
  - `is_valid()`: Recursively verifies block hash linkage, cryptographic signatures, authorization permissions, and business logic.
