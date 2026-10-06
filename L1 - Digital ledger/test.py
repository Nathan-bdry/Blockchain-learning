from collections import abc
import json

with open("ledger2.json") as file:
    ops = json.load(file)

state = {}

def apply_op(state,op):
    if op["op_type"] == "Transfer":
        state[op["source"]] -= op["amount"]
        if op["target"] in state:
            state[op["target"]] += op["amount"]
        else:
            state[op["target"]] = op["amount"]

    else:
        state[op["name"]] = op["value"]

    return state

def apply_ops(state,ops):
    for op in ops:
        state = apply_op(state,op)
    return state

print(apply_ops(state,ops))
