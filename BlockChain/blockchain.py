import hashlib
import json
import time
from uuid import uuid4
from textwrap import dedent
import requests
from urllib.parse import urlparse
from flask import Flask, jsonify, request
import zerosms

class Blockchain(object):
    def __init__(self):
        self.chain = []
        self.current_transactions = []
        self.nodes = set()
        self.newBlock(previous_hash=1, proof=100) #genesis block

    def newBlock(self, proof, previous_hash=None):
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time.time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
        }
        self.current_transactions = []
        if (len(self.chain) != 0):
            if (self.last_block['transactions'] != block['transactions'] and block['transactions'] != []):
                self.chain.append(block)
        else:
            self.chain.append(block)
        #print (self.chain)
        return block

    def newTransaction(self, patientID, doctorID, dataCategory, operation):
        self.current_transactions.append({
            "patientID" : patientID,
            "doctorID"  : doctorID,
            "dataCategory" : dataCategory,
            "Operation" : operation,
            'timestamp': time.time()
        })
        return self.last_block['index'] + 1

    @property
    def last_block(self):
        return self.chain[-1]

    @staticmethod
    def hash(block):
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def proof_of_work(self, last_proof):
        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1
        return proof

    @staticmethod
    def valid_proof(last_proof, proof):
        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        if guess_hash[:4] == "0000":
            #print (guess_hash)
            return True
        else:
            return False
        #return guess_hash[:4] == "0000"

    def register_node(self, address):
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def valid_chain(self, chain):
        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print("\n-----------\n")
            # Check that the hash of the block is correct
            if block['previous_hash'] != self.hash(last_block):
                return False

            # Check that the Proof of Work is correct
            if not self.valid_proof(last_block['proof'], block['proof']):
                return False

            last_block = block
            current_index += 1
        return True

    def resolve_conflicts(self):
        neighbours = self.nodes
        new_chain = None

        # We're only looking for chains longer than ours
        max_length = len(self.chain)

        # Grab and verify the chains from all the nodes in our network
        for node in neighbours:
            response = requests.get(f'http://{node}:8000/chain')

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                # Check if the length is longer and the chain is valid
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        # Replace our chain if we discovered a new, valid chain longer than ours
        if new_chain:
            self.chain = new_chain
            return True
        return False


# Instantiate our Node
app = Flask(__name__)

# Generate a globally unique address for this node
node_identifier = str(uuid4()).replace('-', '')

# Instantiate the Blockchain
blockchain = Blockchain()

@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain[:],
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    #values = request.get_json()
    #print (values)
    # Create a new Transaction
    #index = blockchain.newTransaction(values['patientID'], values['doctorID'], values['dataCategory'], values['Operation'])
    operation = request.form['Operation']
    doctorID = request.form['doctorID']
    dataCategory = request.form['dataCategory']
    if (operation == 'Opened'):
        zerosms.sms(phno="7032830030",passwd="123456789",message=doctorID + ' Opened data of Category ' + dataCategory,receivernum="919176382108")
    index = blockchain.newTransaction(request.form['patientID'], doctorID, dataCategory, operation)
    response = {'message': f'Transaction will be added to Block {index}'}
    return jsonify(response), 201

@app.route('/mine', methods=['GET'])
def mine():
    # We run the proof of work algorithm to get the next proof...
    '''print (request.remote_addr)
    if (request.remote_addr not in blockchain.nodes):
        print ("Not present")
        response = {
            "message" : "Miner not register. Please register."
        }
    else:
    print ("Present")'''
    last_block = blockchain.last_block
    #print (last_block)
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    # We must receive a reward for finding the proof.
    # The sender is "0" to signify that this node has mined a new coin.
    '''blockchain.newTransaction(
        patientID="0",
        doctorID=node_identifier,
        dataLevel=1,
    )'''

    # Forge the new Block by adding it to the chain
    previous_hash = blockchain.hash(last_block)
    block = blockchain.newBlock(proof, previous_hash)

    response = {
        'message': "New Block Added",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }
    return jsonify(response), 200

@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()

    nodes = values.get('nodes')
    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201

@app.route('/nodes/list', methods=['GET'])
def list_of_nodes():
    response = {
        'message': 'List of all the nodes',
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201

@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()
    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockchain.chain
        }

    return jsonify(response), 200

@app.route('/data_access_history',methods=['GET'])
def dataAccess():
    patientID = request.args['pid']
    ret_List = []
    a = {}
    for block in blockchain.chain:
        for i in block['transactions']:
            a = {}
            if ( i['patientID'] == patientID ):
                a['doctorID'] = i['doctorID']
                a['dataCategory'] = i['dataCategory']
                a['Operation'] = i['Operation']
                a['Time'] = time.asctime( time.localtime(i['timestamp']))
            ret_List.append(a)
    return str(ret_List)

if (__name__ == "__main__"):
    app.run(host='0.0.0.0',port = 8000,debug=True)
