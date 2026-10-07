# Lab 1 - Digital Ledger

This lab introduces the fundamental concepts of an append-only digital ledger and state transition functions.

## Overview

A ledger is represented as an ordered sequence of operations applied sequentially to compute a final state dictionary (`account -> balance`):
- **`Init`**: Initializes a new account with a given balance.
- **`Transfer`**: Debits an amount from a source account and credits it to a target account.

## Code Structure

- **`test.py`**:
  - Defines `apply_op(state, op)` and `apply_ops(state, ops)` to sequentially process ledger transactions from JSON.
  - Computes and displays the resulting account state.

- **`part_c_last_question.py`**:
  - Evaluates two approaches to determine the final balance of a target variable:
    1. **Full-state evaluation**: Tracks and updates every account in the ledger.
    2. **Single-variable evaluation**: Filters and processes only transactions involving the target account (`source` or `target`).
  - Benchmarks execution time and demonstrates the speedup factor achieved by single-variable filtering.
