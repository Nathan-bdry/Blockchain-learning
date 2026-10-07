# Lab 2 - Hashed Structures

This lab explores cryptographic hashing, canonical serialization, and hashed linked structures (Blockchains and Directed Acyclic Graphs).

## Overview

The lab builds foundational components for tamper-evident data structures:
- **Hashing**: Custom 32-bit hashing (`toy_hash`) and truncated SHA-256 hashing (`simple_hash`).
- **Canonical Serialization**: Normalized JSON representations with sorted keys to ensure deterministic hashes.
- **Linked Blocks**: Linking blocks via cryptographic hashes of their predecessors (`prev_hashes`).
- **DAG (Directed Acyclic Graph)**: Representing and validating dependency graphs linked by hashes (modeled from `DAG.jpg`).

## Code Structure

- **`JChain.py` (v0.1)**:
  - Defines core data structures: `State`, `Operation`, `Ledger`.
  - Specific operations: `Init`, `Transfer`, and `Snapshot`.
  - Logic checks: Validates transaction rules (e.g. source account existence, sufficient balance).

- **`test.py`**:
  - Tests `toy_hash` against known string test vectors.
  - Implements the `Block` class with deterministic JSON serialization (`json()`, `from_json()`) and `hash()`.
  - Assembles a 9-block Directed Acyclic Graph (DAG) and verifies overall cryptographic consistency:
    ```bash
    python test.py
    ```
