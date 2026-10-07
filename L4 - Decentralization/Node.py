# usage: python Node.py <port> <peers>

import socket, threading, sys, json, copy
import JCrypto
import JChain
from JChain import State, Blockchain, Block, Ledger #We rebuild an instance of the blockchain from the received JSON

def operation_eq(self, other): # Define equality on Operation so operations can be compared by value across serialization
    return (
        isinstance(other, JChain.Operation) and
        self.content == other.content and
        self.public_key == other.public_key and
        self.signature == other.signature
    )
JChain.Operation.__eq__ = operation_eq

# --------------------------------------- DESERIALIZATION ---------------------------------------
# We need to deserialize ops, blocks and blockchain because we transfer JSON on the network and JSON only transfer dict, list, int, str.. no class or methodes

def deserialize_operation(op_data): # rebuild an op instance from its JSON
    op_type = op_data["content"]["op_type"]
    op_cls = getattr(JChain, op_type)
    return op_cls(op_data["content"], op_data["public_key"], op_data["signature"])


def deserialize_block(b_data): # rebuild a block instance from its JSON
    operations = [deserialize_operation(op) for op in b_data["operations"]]
    return Block(Ledger(operations), b_data["prev_hash"])


def deserialize_chain(raw_chain_data): # rebuild a blockchain instance from its JSON
    blocks = [deserialize_block(b_data) for b_data in raw_chain_data]
    return Blockchain(blocks)

# ------------------------------------------------------------------------------------------------


class Node:

	# --------------------------------------- ALL METHODES --------------------------------------- 
	
	def __init__(self, host, port, peers):
		self.host = host
		self.port = port
		self.address = (host, port)
		self.peers = peers
		self.chain = Blockchain()
		self.state = State({})
		self.pending_ops = [] #waiting operations
		self.privkey, self.pubkey = JCrypto.KeyGen() #creating the identity of the node

	def start(self):
		threading.Thread(target=self.listen, daemon=True).start()
		self.broadcast({"type": "HELLO", "from": self.address})

	def listen(self):
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.bind(self.address)
		s.listen()

		print(f"[+] Node listening on {self.port}")

		while True:
			conn, _ = s.accept()
			data = b""
			while True:
				chunk = conn.recv(8192)
				if not chunk:
					break
				data += chunk
			if data:
				self.handle_message(json.loads(data.decode()))
			conn.close()

	def send(self, peer, message):
		try:
			s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			s.connect(peer)
			s.send(json.dumps(message, default=vars).encode()) # added "default=vars" to authorised the serialisation of the blockchain in json
			s.close()
			return True
		except:
			return False
			
	def broadcast(self, message):
		
		for peer in self.peers:
			self.send(peer, message)

	def create_and_broadcast_op(self, data):
		op = JChain.Operation.create(data, self.privkey)
		self.pending_ops.append(op)
		self.broadcast({
			"type": "NEW_OP",
			"from": self.address,
			"op": op.__dict__  
		})
		print(f"[+] Operation created and broadcasted: {data['op_type']}")
		return op
	
	def clean_pending_operations(self): # Verify the validity of ops in pending_ops
		valid_ops = []
		temp_state = copy.deepcopy(self.state)
		for op in self.pending_ops: # for each op in pending_ops
			if op.is_valid(temp_state): # We check if the op is valid 
				temp_state = op.apply(temp_state) # if valid we add it to temp_state 
				valid_ops.append(op) # and we add it to valid_ops
			else:
				print(f"[-] Invalid operation removed: {op.content['op_type']} (insufficient funds, bad signature or unauthorized)")

		removed_count = len(self.pending_ops) - len(valid_ops)
		self.pending_ops = valid_ops
		print(f"[+] Pending operations cleaned: {len(self.pending_ops)} valid remaining ({removed_count} removed)")
		return valid_ops


	def mine_block(self): # Validate pending_ops, build a new block and broadcast it
		
		self.clean_pending_operations() # We first make sure that all ops are valid

		if not self.pending_ops:
			print("[-] No pending operations to include in block")
			return None

		ledger = Ledger(self.pending_ops) # Here we creat the ledger and the new block linked to the last hash
		prev_hash = self.chain.hash()
		new_block = Block(ledger, prev_hash)

		self.chain.append(new_block) # Add the new block to our local chain 
		self.state = new_block.operations.apply_ops(self.state) # update state
		
		self.pending_ops = [] # pending_ops empty because they are all in the new block

		print(f"[+] Block created! Hash: {new_block.hash()} (Prev: {prev_hash})")

		self.broadcast({  # broadcast block to all peers
			"type": "NEW_BLOCK",
			"from": self.address,
			"block": new_block
		})
		return new_block



	# --------------------------------------------------------------------------------------------------


	# --------------------------------------- ALL MESSAGES TYPES --------------------------------------- 
	
	def handle_message(self, msg):
		t = msg["type"]

		if t == "HELLO":
			peer = tuple(msg["from"])
			print(f"[+] New node connected on {peer}")
			if peer != self.address and peer not in self.peers:
				self.peers.append(peer)

		if t == "BYE": # Here we add a BYE msg for the disconnect cmd
			peer = tuple(msg["from"])
			print(f"[-] Node disconnected on {peer}")
			if peer != self.address:
				self.peers.remove(peer)

		if t == "TEST":
			print(f"[+] Test message received: {msg}")

		if t == "GET_PEERS":
			sender = tuple(msg["from"])
			self.send(sender, {  # We send back our list to the asker
				"type": "PEERS",
				"from": self.address,
				"peers": self.peers
			})

		if t == "GET_CHAIN":
			sender = tuple(msg["from"])
			self.send(sender, {  # We send back our Blockchain to the asker
				"type": "CHAIN",
				"from": self.address,
				"Blockchain": self.chain
			})

		if t == "PEERS":
			received_peers = msg["peers"]
			for p in received_peers:
				peer = tuple(p)
				if peer != self.address and peer not in self.peers:
					self.peers.append(peer)
					print(f"[+] Discovered new peer: {peer}")
					self.send(peer, {"type": "HELLO", "from": self.address}) # We say hello to new finded nodes
		
		if t == "CHAIN":
			received_chain = deserialize_chain(msg["Blockchain"])
			if len(received_chain) > len(self.chain): #If the received chain has more informations our chain is outdated
				if received_chain.check_hashes() == True:  #if the received chain has correct hashes
					self.chain = received_chain  # we update it

					new_state = State({}) # We recompute state from updated chain
					for b in self.chain:
						new_state = b.operations.apply_ops(new_state)
					self.state = new_state

					mined_ops = [op for b in self.chain for op in b.operations] # We remove any operations that are now mined in the chain
					self.pending_ops = [op for op in self.pending_ops if op not in mined_ops]
					print(f"[+] Blockchain updated")
				else:
					print(f"[=] Blockchain kept (wrong hashes detected)")
			else:
				print(f"[=] Blockchain up to date")
			
		if t == "GET_HASH":
			sender = tuple(msg["from"])
			self.send(sender, {
					"type": "HASH",
					"from": self.address,
					"hash": self.chain.hash()  # We send the hash of the last block
			})

		if t == "HASH":
			sender = tuple(msg["from"])
			remote_hash = msg["hash"]
			local_hash = self.chain.hash()

			if remote_hash == local_hash:
				print(f"[=] Chain matches with peer {sender} (terminal hash: {local_hash})")
			else:
				print(f"[!] Chain DIFFERS from peer {sender} (local: {local_hash}, remote: {remote_hash})")

		if t == "NEW_OP":
			op_data = msg["op"]
			op_type = op_data["content"]["op_type"]
			op_cls = getattr(JChain, op_type)
			op = op_cls(op_data["content"], op_data["public_key"], op_data["signature"])
			
			if op not in self.pending_ops: # We add the operation to pending_ops if not already in
				self.pending_ops.append(op)
				print(f"[+] Received new pending operation: {op_type} from {msg['from']}")
	
		if t == "NEW_BLOCK":
			new_block = deserialize_block(msg["block"])
			sender = tuple(msg["from"])

			if new_block.prev_hash == self.chain.hash(): # If the new block feats with our last block
				if new_block.operations.is_valid(copy.deepcopy(self.state)): # We verify the validity of the ops int this block
					self.chain.append(new_block) # we add the new block
					self.state = new_block.operations.apply_ops(self.state) # update state
					self.pending_ops = [op for op in self.pending_ops if op not in new_block.operations] # We delete from our pending_ops ops in this block
					print(f"[+] New block accepted from {sender}! Hash: {new_block.hash()}")
				else:
					print(f"[-] Block rejected from {sender}: invalid operations")
			
			else: # if the new block doesn't feets with our last block
				print(f"[!] Block from {sender} does not link to our chain (fork or desync). Requesting full chain...")
				self.send(sender, {"type": "GET_CHAIN", "from": self.address})

	# ------------------------------------------------------------------------------------------ 



if __name__ == "__main__":
	port = int(sys.argv[1])
	peers = [("localhost", int(p)) for p in sys.argv[2:]]

	node = Node("localhost", port, peers)
	node.start()

	# --------------------------------------- ALL INPUTS --------------------------------------- 

	while True:
		cmd = input("> ")

		if cmd == "peers":
			print(node.peers)
			
		elif cmd == "test":
			node.broadcast({"type": "TEST", "content": "Broadcast message to all peers"})

		elif cmd == "exit":
			exit()
		
		elif cmd.startswith("connect "):
			target_port = int(cmd.split()[1])
			target_peer = ("localhost", target_port)
			if target_peer != node.address and target_peer not in node.peers:
				success = node.send(target_peer, {"type": "HELLO", "from": node.address}) # We try to send the connection msg
				if success:
					node.peers.append(target_peer)
					print(f"[+] Connected to {target_peer}")
				else:
					print(f"[-] Failed to connect to {target_peer} (node offline)")
			else:
				print("[-] Peer already in list or cannot connect to self")
		
		
		elif cmd.startswith("disconnect "): # if the cmd start with "disconnect ..." 
			target_port = int(cmd.split()[1]) # We split the cmd in 2 parts and the 2nd part is our target port 
			target_peer = ("localhost", target_port)
			if target_peer in node.peers and target_peer != node.address:
				node.peers.remove(target_peer) # We remove it from peers
				node.send(target_peer, {"type": "BYE", "from": node.address})
			else : 
				print(f"Node not found")

		elif cmd.startswith("discover "): # if the cmd start with "discover ..." 
			target_port = int(cmd.split()[1]) # We split the cmd in 2 parts and the 2nd part is our target port 
			target_peer = ("localhost", target_port)
			if target_peer in node.peers and target_peer != node.address:
				node.send(target_peer, {"type": "GET_PEERS", "from": node.address})
			else:
				print(f"Node not found")

		elif cmd.startswith("getchain "): # if the cmd start with "getchain ..." 
			target_port = int(cmd.split()[1]) # We split the cmd in 2 parts and the 2nd part is our target port 
			target_peer = ("localhost", target_port)
			if target_peer in node.peers and target_peer != node.address:
				node.send(target_peer, {"type": "GET_CHAIN", "from": node.address})
			else:
				print(f"Node not found")

		elif cmd == "check": #here we check if our blockchain is valid
			is_valid = node.chain.check_hashes()
			print(f"[+] Local chain valid: {is_valid} | Terminal hash: {node.chain.hash()}")

		elif cmd.startswith("compare "): #here we compare last hashes of both chain to see if they have the same version or not
			target_port = int(cmd.split()[1])
			target_peer = ("localhost", target_port)
			if target_peer in node.peers and target_peer != node.address:
				node.send(target_peer, {"type": "GET_HASH", "from": node.address})
			else:
				print("Node not found in peers")

		elif cmd == "Blockchain": # if we type Blockchain" 
			print(node.chain) # We print the Blockchain stored by the node

		elif cmd == "pending": # if we type pending
			print(f"Pending operations ({len(node.pending_ops)}):")
			for op in node.pending_ops:
				print(op) # We get all the pending operations

		elif cmd.startswith("transfer "): # Here we need the syntax -> transfer <target> <amount>
			_, target, amount = cmd.split()
			target_acc = int(target) if target.isdigit() else target
			data = {
				"op_type": "Transfer",
				"source": node.pubkey,
				"target": target_acc,
				"amount": int(amount)
			}
			node.create_and_broadcast_op(data) # broadcast the transfer operation

		elif cmd == "mykey": # Just print your pubkey for convinience
			print(f"My public key: {node.pubkey}")

		elif cmd.startswith("init "): # syntax -> init <account> <amount>
			_, name, val = cmd.split()
			target_name = node.pubkey if name == "me" else (int(name) if name.isdigit() else name)
			data = {
				"op_type": "Init",
				"name": target_name,
				"value": int(val)
			}
			node.create_and_broadcast_op(data) # broadcast the init operation

		elif cmd.startswith("admin "): # syntax -> admin <key> (or 'admin me')
			key = cmd.split()[1]
			target_key = node.pubkey if key == "me" else (int(key) if key.isdigit() else key)
			data = {
				"op_type": "EnrolAdminKey",
				"key": target_key
			}
			node.create_and_broadcast_op(data) # broadcast the EnrolAdminKey operation

		elif cmd == "snapshot": # save actual state
			data = {
				"op_type": "Snapshot",
				"state": dict(node.state)
			}
			node.create_and_broadcast_op(data) # broadcast the snapshot operation

		elif cmd == "validate": # remove unvalid ops from pending_ops 
			node.clean_pending_operations()

		elif cmd == "mine": # mine a new block
			node.mine_block()

		elif cmd == "state": # display current state
			print(f"Current State: {node.state}")

	# ------------------------------------------------------------------------------------------------
