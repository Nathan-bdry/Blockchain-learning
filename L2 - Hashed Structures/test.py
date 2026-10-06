def toy_hash(S):
    h = 0

    for character in S:
        h += ord(character)
        h ^= 31 * h
        h %= 2**32

    return h

print(toy_hash("Hello World"))
print(toy_hash("JUNIA"))
print(toy_hash("Bitcoin"))
print(toy_hash("⍺βƔΔε"))

assert toy_hash("JUNIA") == 2268132318

assert toy_hash("Bitcoin") == 2028574072

assert toy_hash("⍺βƔΔε") == 3299468638

'All tests passed successfully!'


import hashlib
import json

def simple_hash(S):
    return int(hashlib.sha256(bytes(S, "utf8")).digest().hex()[:8], 16)



class Block:
    def __init__(self, content, prev_hashes=None):
        self.content = content
        self.prev_hashes = prev_hashes if prev_hashes is not None else []

    def json(self):
        """Returns a canonical (normalized) JSON string representation of the block."""
        return json.dumps({
            "content": self.content,
            "prev_hashes": self.prev_hashes
        }, sort_keys=True)

    @classmethod
    def from_json(cls, json_str):
        """Reconstructs a Block instance from its JSON representation."""
        data = json.loads(json_str)
        return cls(content=data["content"], prev_hashes=data.get("prev_hashes", []))

    def hash(self):
        """Returns the simple_hash value of its canonical JSON representation."""
        return simple_hash(self.json())

    def __eq__(self, other):
        if isinstance(other, Block):
            return self.json() == other.json()
        return False

    def __repr__(self):
        return f"Block(content={self.content!r}, prev_hashes={self.prev_hashes!r})"

block1 = Block(
    [{"from": "Alice", "to": "Bob", "amount": 5}],
    []
)

block2 = Block(
    [{"from": "Bob", "to": "Alice", "amount": 5}],
    [block1.hash()]
)

print(block1.json())
print(block1.hash())
print(block2.json())
print(block2.hash())


# Step 1 : Blocks without successors (prev_hashes = [])
carbon_seq = Block("Carbon Sequestration", [])
fire = Block("Fire", [])
# Step 2 : Blocks whose successors already have their hash calculated
forest_species = Block("Forest Species Abundance", [carbon_seq.hash()])
poaching = Block("Poaching", [forest_species.hash()])
logging = Block("Logging", [forest_species.hash(), carbon_seq.hash()])
protected_area = Block("Protected Area", [fire.hash(), poaching.hash(), logging.hash()])
# Step 3 : Source blocks
slope = Block("Slope", [protected_area.hash(), logging.hash()])
elevation = Block("Elevation", [protected_area.hash(), logging.hash()])
distance_roads = Block(
    "Distance to Roads and Cities", 
    [fire.hash(), protected_area.hash(), poaching.hash(), logging.hash(), forest_species.hash()]
)
# 4. Store in a dictionary {hash: block} and test for consistency
all_blocks = [
    carbon_seq, fire, forest_species, poaching,
    logging, protected_area, slope, elevation, distance_roads
]
dag = {b.hash(): b for b in all_blocks}
# Check for consistency as required by the subject
assert all(h == block.hash() for h, block in dag.items())
print("DAG consistency verified successfully! Number of blocks :", len(dag))