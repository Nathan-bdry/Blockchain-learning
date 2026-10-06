import json, hashlib, random


# The state of the ledger at a given time is essentially a dictionary of
# variable name -> value pairs

class State(dict):
	
	pass


# Generic Operation class providing a blueprint for specific instances

class Operation():

    def create(data):

        op_type = data.get("op_type") or data.get("type")

        match op_type:

            case "Init":
                return Init(data)

            case "Transfer":
                return Transfer(data)

            case "EnrolAdminKey":
                return EnrolAdminKey(data)

            case "Genesis":
                return Genesis(data)

    def sign(self, priv_key):

        message = json.dumps(self.content(), sort_keys=True)

        self.signature = Sign(priv_key, message)
        self.public_key = ExtractPublicKey(priv_key)

    def content(self):

        return {
            key: value
            for key, value in self.__dict__.items()
            if key not in ["signature", "public_key"]
        }

    def is_signature_valid(self):

        if self.signature is None or self.public_key is None:
            return False

        message = json.dumps(self.content(), sort_keys=True)

        return Verify(self.public_key, message, self.signature)

    def is_valid(self, state):

        return self.is_signature_valid() and self.is_key_authorized(state) and self.is_logic_valid(state)

    def is_key_authorized(self, state):

        return False

    def is_logic_valid(self, state):

        return True

    def apply(self, state):

        return state



# A ledger is just for now a list of Operations

class Ledger(list):
	
	# Constructor from raw data
	
	def __init__(self, data):
		
		for raw_op in data:
			
			self.append( Operation.create(raw_op) )
	
	# Computes the final state of the ledger starting from initial state
	
	def apply_ops(self, starting_state = State({}), bypass_checks = False):
		
		state = State(starting_state)
		
		for op in self:
			
			if bypass_checks or op.is_valid(state):
				state = op.apply(state)
				
		return state
		
	# Checks the validity of all operations
	
	def is_valid(self, starting_state = State({})):
		
		state = State(starting_state)
		
		for op in self:
			
			if not op.is_valid(state):
				return False
				
			state = op.apply(state)
			
		return True
			

# Transferring tokens from one integer variable to another
		
class Transfer(Operation):
	
	# Constructor taking a dictionary as raw data
	
	def __init__(self, data):
	
		self.type = data.get("op_type", data.get("type", "Transfer"))
		self.source = data["source"]
		self.target = data["target"]
		self.amount = data["amount"]
		self.signature = data.get("signature") #.get() Parce qu'avant qu'une opération soit signée les données n'ont pas de contenu
		self.public_key = data.get("public_key")

	def is_key_authorized(self, state):
		return self.public_key is not None and self.public_key == self.source
	
	# Source must be defined and contains enough tokens
	
	def is_logic_valid(self, state):
		
		return (self.source in state) and (state[self.source] >= self.amount)
	
	# Transfers tokens from source to target
	# Target variable is created is needed
	
	def apply(self, state):
		
		if self.target not in state:
			state[self.target] = 0
		
		state[self.source] -= self.amount
		state[self.target] += self.amount
		
		return state
	

	

	
		
		
# Initialization of a new integer (account) variable
		
class Init(Operation):
	
	# Constructor taking a dictionary as raw data
	
	def __init__(self, data):
		
		self.type = data.get("op_type", data.get("type", "Init"))
		self.name = data["name"]
		self.value = data["value"]
		self.signature = data.get("signature") #.get() Parce qu'avant qu'une opération soit signée les données n'ont pas de contenu
		self.public_key = data.get("public_key")
		
	# Only administrators of the chain can use Init operations

	def is_key_authorized(self, state):

		return "admin_keys" in state and self.public_key in state["admin_keys"]

	# Checks that the variable is not already defined
		
	def is_logic_valid(self, state):
		
		return self.name not in state

	# Adds variable with given value to state

	def apply(self, state):
	
		state[self.name] = self.value

		return state


# Enrolment of a new administrator key

class EnrolAdminKey(Operation):

	# Constructor taking a dictionary as raw data

	def __init__(self, data):

		self.type = data.get("op_type", data.get("type", "EnrolAdminKey"))
		self.key = data.get("key", data.get("admin_key"))
		self.signature = data.get("signature")
		self.public_key = data.get("public_key")

	@property
	def admin_key(self):
		return self.key

	# Only current administrators can enrol new administrators

	def is_key_authorized(self, state):

		return "admin_keys" in state and self.public_key in state["admin_keys"]

	# The key must not already be an administrator

	def is_logic_valid(self, state):

		return "admin_keys" in state and self.key not in state["admin_keys"]

	# Adds the key to the list of administrator keys

	def apply(self, state):

		if "admin_keys" not in state:
			state["admin_keys"] = []
		state["admin_keys"] = list(state["admin_keys"]) + [self.key]

		return state



# Takes a snapshot of the current state

class Snapshot(Operation):
	
	def __init__(self, state):
		
		self.type = "Snapshot"
		self.state = state
	
	# Valid in a list of operations if it describes the current state
	
	def is_logic_valid(self, current_state):
		
		return current_state == self.state
	
	# If checks are bypassed, this will restore the saved state
	
	def apply(self, current_state):
		
		return self.state


# Genesis operation setting up the initial state on an empty chain

class Genesis(Operation):

	# Constructor taking a dictionary as raw data

	def __init__(self, data):

		self.type = data.get("op_type", data.get("type", "Genesis"))
		if "state" in data and isinstance(data["state"], dict):
			self.state = dict(data["state"])
		else:
			self.state = {
				k: v for k, v in data.items()
				if k not in ["op_type", "type", "signature", "public_key"]
			}
		self.signature = data.get("signature")
		self.public_key = data.get("public_key")

	# Genesis does not require cryptographic signature
	def is_signature_valid(self):
		return True

	# Genesis bootstraps the chain authority
	def is_key_authorized(self, state):
		return True

	# Genesis is only logically valid on an initial empty state
	def is_logic_valid(self, state):
		return len(state) == 0

	# Sets up initial variables (e.g. admin keys, initial accounts) in the state
	def apply(self, state):
		for k, v in self.state.items():
			if isinstance(v, list):
				state[k] = list(v)
			else:
				state[k] = v
		return state


# Generic hashed block object

class Block():
	
	def __init__(self, content, prev_hashes):
		
		if isinstance(prev_hashes, (int, str)):
			prev_hashes = [prev_hashes]
		self.content = content
		self.prev_hashes = sorted(prev_hashes)
		
	def json(self):
		
		def default_serializer(obj):
			if hasattr(obj, "__dict__"):
				return obj.__dict__
			raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

		return json.dumps(self.__dict__, default=default_serializer, sort_keys=True, indent=2)
		
	def hash(self):
		
		return simple_hash(self.json())
		
	def __repr__(self):
		
		return " ".join(self.json().split())


# Blockchain object containing a list of blocks

class Blockchain(list):

	def __init__(self, blocks=None):
		super().__init__()
		if blocks:
			for b in blocks:
				self.append(b)

	@property
	def blocks(self):
		return self

	# Appends a block with correct previous hash link
	def add_block(self, content):
		prev_hash = [self[-1].hash()] if len(self) > 0 else []
		block = Block(content, prev_hash)
		self.append(block)
		return block

	# Computes the final state of the blockchain starting from an initial state
	def apply_ops(self, starting_state=None, bypass_checks=False):
		state = State(starting_state or {})
		for block in self:
			ops = block.content if isinstance(block.content, list) else [block.content]
			for raw_op in ops:
				op = raw_op if isinstance(raw_op, Operation) else Operation.create(raw_op)
				if bypass_checks or op.is_valid(state):
					state = op.apply(state)
		return state

	# Checks validity of block hashes chaining and all operations logic & signatures
	def is_valid(self, starting_state=None):
		state = State(starting_state or {})
		for i, block in enumerate(self):
			# 1. Check previous hashes
			if i == 0:
				if block.prev_hashes not in ([], [0]):
					return False
			else:
				expected_prev_hash = [self[i - 1].hash()]
				if block.prev_hashes != expected_prev_hash:
					return False

			# 2. Check each operation in the block
			ops = block.content if isinstance(block.content, list) else [block.content]
			for raw_op in ops:
				op = raw_op if isinstance(raw_op, Operation) else Operation.create(raw_op)
				if op is None or not op.is_valid(state):
					return False
				state = op.apply(state)

		return True



##### Crypto


# 32-bit custom hash function

def simple_hash(S):
	return int(hashlib.sha256(bytes(S, "utf8")).digest().hex()[:8], 16)


# minimalistic elliptic curve support

def div_mod(a, b, p):
	
	return a * pow(b,-1,p) % p


# courbe elliptique mod p sous forme de Weierstrass

class EllipticCurve:
	
	def __init__(self, p, a, b):
			
		self.p = p
		self.a = a % p
		self.b = b % p
		
	def __repr__(self):
		
		return "Elliptic curve y^2 = x^3 + %sx + %s mod %s" % (self.a, self.b, self.p)
		
	def homog_def_equation(self, x, y, z = 1):
		
		return (y**2*z - x**3 - self.a*x*z**2 - self.b*z**3) % self.p
		
	def point(self, x, y, z = 1, trust = False):
	
		return EllipticPoint(self, x, y, z, trust)
		
	def zero(self):
		
		return EllipticPoint(self, 0, 1, 0, True)
		
	def add(self, P, Q):
		
		if P.E != self or Q.E != self:
			
			raise ValueError("Points must be on same curve")
			
		if P == self.zero():
			
			return Q
			
		if Q == self.zero():
			
			return P
		
		if P.x == Q.x:
			
			if P != Q:  # vertically aligned
				
				return self.zero()
				
			# doubling
			
			if P.y == 0:
				
				return self.zero()
			
			l = div_mod(3*P.x**2 + self.a, 2*P.y, self.p)
			
		else:  # generic case
			
			l = div_mod(Q.y - P.y, Q.x - P.x, self.p)
		
		x = l**2 - (P.x + Q.x)
		y = l * (x - P.x) + P.y
			
		return EllipticPoint(self, x, -y, True)
		
	def mul(self, m, P):
		
		res = self.zero()
		
		if m < 0:
			
			P = P.opp()
			m = -m
		
		for b in bin(m)[2:]:
			
			res = res + res
			if int(b):
				res = res + P
				
		return res


# point on a curve
		
class EllipticPoint:
	
	def __init__(self, E, x, y, z = 1, trust = True):

		if not trust:
			
			if E.homog_def_equation(x,y,z) != 0:
			
				raise ValueError("Point not on curve")
			
			if z % E.p != 0:
				
				x = div_mod(x, z, E.p)
				y = div_mod(y, z, E.p)
				z = 1
				
			else:
				
				x = 0
				y = 1
			
		self.E = E
		self.x = x % E.p
		self.y = y % E.p
		self.z = z % E.p  # assumed 0 or 1
		
	def __eq__(self, other):
	
		return (self.x, self.y, self.z) == (other.x, other.y, other.z)
		
	def __repr__(self):
		
		if self.z == 0:
			return "0"
		return "(%s,%s)" % (self.x, self.y)
			
	def __add__(self, other):
		
		return self.E.add(self, other)
		
	def __sub__(self, other):
		
		return self + other.opp()
		
	def opp(self):
		
		return EllipticPoint(self.E, self.x, -self.y, self.z, True)
		
	def __rmul__(self, m):
		
		return self.E.mul(m, self)
		

# fixed parameters (!INSECURE! for pedagogical purposes only)

EE = EllipticCurve(101239643, 29717072, 16741874)
GG = EllipticPoint(EE, 22861771, 7928731)
qq = 101246273


# packing/unpacking

def pack(x,y):
	
	return 2**32 * x + y

def point_to_int(point):
	
	return pack(point.x, point.y)
	
def unpack(n):
	
	return (n // 2**32, n % 2**32)
	
def int_to_point(n):
	
	(x,y) = unpack(n)
	return EllipticPoint(EE, x, y)


# signature scheme

def ExtractPublicKey(private_key):
	
	return point_to_int(private_key * GG)


def KeyGen():
	
	private_key = random.randrange(qq)
	public_key = ExtractPublicKey(private_key)
	return (private_key, public_key)
	

def Sign(private_key, message):
	
	r = random.randrange(qq)
	e = simple_hash(str(r * GG) + message)
	s = (r - private_key * e) % qq
	return pack(s,e)


def Verify(public_key, message, signature):
	
	(s,e) = unpack(signature)
	return simple_hash(str(s * GG + e * int_to_point(public_key)) + message) == e

print("JChain v0.3 loaded - now with basic signature support!")
