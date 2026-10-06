# usage: python Node.py <port> <peers>

import socket, threading, sys, json
import JCrypto
import JChain
from JChain import State, Blockchain, Block, Ledger

def deserialize_chain(raw_chain_data): #We rebuild an instance of the blockchain from the received JSON
    blocks = []
    for b_data in raw_chain_data:
        operations = []
        for op_data in b_data["operations"]:
            op_type = op_data["content"]["op_type"]
            op_cls = getattr(JChain, op_type)
            op = op_cls(op_data["content"], op_data["public_key"], op_data["signature"])
            operations.append(op)
            
        ledger = Ledger(operations)
        block = Block(ledger, b_data["prev_hash"])
        blocks.append(block)
        
    return Blockchain(blocks)


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
			data = conn.recv(8192)
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
			
			if op not in self.pending_ops: #We add the operation to pending_ops if not already in
				self.pending_ops.append(op)
				print(f"[+] Received new pending operation: {op_type} from {msg['from']}")
	
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
			data = {
				"op_type": "Transfer",
				"source": node.pubkey,
				"target": target,
				"amount": int(amount)
			}
			node.create_and_broadcast_op(data) # broadcast the transfer operation

		elif cmd == "mykey": # Just print your pubkey for convinience
			print(f"My public key: {node.pubkey}")

		elif cmd.startswith("init "): # syntax -> init <account> <amount>
			_, name, val = cmd.split()
			data = {
				"op_type": "Init",
				"name": name,
				"value": int(val)
			}
			node.create_and_broadcast_op(data) # broadcast the init operation

		elif cmd.startswith("admin "): # syntax -> admin <key> (or 'admin me')
			key = cmd.split()[1]
			target_key = node.pubkey if key == "me" else key
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



	# ------------------------------------------------------------------------------------------------
