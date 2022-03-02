#!/usr/bin/env python
# coding: utf-8

# In[1]:


import json
from datetime import datetime
import os

import requests
import tabulate
from web3 import Web3
from web3.middleware import geth_poa_middleware

w3 = Web3(Web3.HTTPProvider('http://localhost:8545'))
w3.middleware_onion.inject(geth_poa_middleware, layer=0)

def get_abi(addy):
    home = os.path.expanduser("~")
    cache_dir = os.path.join(home, '.abicache')
    cache = os.path.join(cache_dir, f'{addy}.json')
    try:
        with open(cache) as inp:
            abi = json.loads(inp.read())
    except Exception as e:
        print(e)
        resp = requests.get(f'https://api.snowtrace.io/api?module=contract&action=getabi&address={addy}')
        abi = json.loads(resp.json()['result'])
        os.makedirs(cache_dir, exist_ok=True)
        with open(cache, 'w') as out:
            out.write(json.dumps(abi, indent=True))
    return abi


def get_contract(addy):
    return w3.eth.contract(address=addy, abi=get_abi(addy))


class Wallet:
    def __init__(self, addy, pkey):
        self.address, self.private_key = addy, pkey

    def _prep(self, function, **kwargs):
        block = w3.eth.get_block('latest')
        tx_params = dict(
            type=2,
            chainId=31337,
            maxFeePerGas=2 * block['baseFeePerGas'],
            maxPriorityFeePerGas=0,
            nonce=w3.eth.get_transaction_count(self.address),
            gas=8000000,
        )
        tx_params['from']=self.address
        tx_params.update(**kwargs)
        if 'gas' not in tx_params:
            gas = function.estimateGas(tx_params)
            tx_params.update(gas=2 * gas)
        return tx_params
        
    def transact(self, function, **kwargs):
        tx_params = self._prep(function, **kwargs)
        tx = function.buildTransaction(tx_params)
        signed = w3.eth.account.sign_transaction(tx, self.private_key)
        rcpt = w3.eth.wait_for_transaction_receipt(w3.eth.send_raw_transaction(signed.rawTransaction))
        print('success' if rcpt.status==1 else 'tx failed')
    
    def call(self, function, **kwargs):
        tx_params = self._prep(function, **kwargs)
        return function.call(tx_params)


def advance_time(seconds):
    headers = {'content-type': 'application/json'}
    data = {'jsonrpc': '2.0', 'id': 0, 'method': "evm_increaseTime", 'params': [seconds]}
    requests.post('http://localhost:8545', headers=headers, data=json.dumps(data))
    mine = {'jsonrpc': '2.0', 'id': 0, 'method': "evm_mine"}
    requests.post('http://localhost:8545', headers=headers, data=json.dumps(mine))
    

def load_abi(fn):
    with open(fn) as inp:
        js = json.load(inp)
    return js['abi']


# In[2]:


lava = '0x99bbA657f2BbC93c02D617f8bA121cB8Fc104Acf'
staking = '0x0E801D84Fa97b50751Dbf25036d067dCf18858bF'

lava_abi = load_abi('/Users/justn/lava-staking/artifacts/contracts/MockLAVA.sol/MockLAVA.json')
staking_abi = load_abi('/Users/justn/lava-staking/artifacts/contracts/LavaStaking.sol/LavaStaking.json')

contract_lava = w3.eth.contract(address=lava, abi=lava_abi)
contract_staking = w3.eth.contract(address=staking, abi=staking_abi)
wavax = get_contract(contract_staking.functions.wavax().call())

wallet = Wallet('0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266','0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80')

whales = """0x70997970c51812dc3a010c7d01b50e0d17dc79c8
0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d
0x3c44cdddb6a900fa2b585dd299e03d12fa4293bc
0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a
0x90f79bf6eb2c4f870365e785982e1f101e93b906
0x7c852118294e51e653712a81e05800f419141751be58f605c371e15141b007a6
0x15d34aaf54267db7d7c367839aaf71a00a2c6a65
0x47e179ec197488593b187f80a00eb0da91f1b9d0b13f8733639f19c30a34926a"""
whale_data = whales.split('\n')
user = [Wallet(w3.toChecksumAddress(whale_data[2*i]),whale_data[2*i+1]) for i in range(len(whale_data)//2)]


# In[3]:


def get_state(users):
    state = {}
    for u in users:
        state[u.address] = dict()
        for name, contract in [("stake",contract_staking), ("wavax",wavax), ("lava", contract_lava)]:
            state[u.address][name] = contract.functions.balanceOf(u.address).call()
        state[u.address]["pending"] = contract_staking.functions.pendingRewards(u.address).call()
    return state

def print_state(users):
    state = get_state(users)
    def pp(val):
        return round(val/1e18,1)
    rows=[]
    for u in users:
        s = state[u.address]
        rows.append((u.address,pp(s["pending"]),pp(s["stake"]),pp(s["wavax"]),pp(s["lava"])))
    print(tabulate.tabulate(rows, headers=["address", "pending", "stake", "wavax", "lava"]))
    

def checked_distribute(amount):
    before = get_state(user)
    wallet.transact(contract_staking.functions.distribute(amount))
    after = get_state(user)
    assert set(before.keys()) == set(after.keys())
    new_funds = []
    stake= []
    for u in before:
        if after[u]['stake'] != before[u]['stake']:
            raise ValueError("before and after stakes are incompatible")
        new_funds.append(after[u]['pending'] - before[u]['pending'])
        stake.append(after[u]['stake'])
    snf = sum(new_funds)
    sst = sum(stake)
    for nf,s in zip(new_funds,stake):
        residual = (nf * sst - snf * s)/sst
        assert -1 <= residual <= 1, f"additional funds not distributed proportionally to stake {residual=}, {s=}, {nf=}, {mean=}"
        

def checked_deposit(u, amount):
    state_before = get_state(user)
    u.transact(contract_staking.functions.deposit(amount))
    state_after = get_state(user)
    assert state_after[u.address]['pending'] == 0, "did not claim all pending rewards"
    assert state_after[u.address]['wavax'] == state_before[u.address]['wavax'] + state_before[u.address]['pending'], "leaking wavax"
    assert state_after[u.address]['stake'] >= state_before[u.address]['stake'], "stake should not decrease with each claim"


def checked_all_claim():
    for u in user:
         checked_deposit(u, 0)
    wavax_in_contract = wavax.functions.balanceOf(contract_staking.address).call()
    assert wavax_in_contract <= 100, "more than 100 wei left in the contract after everyone claiming"    
    assert contract_staking.functions.totalSupply().call() == sum([contract_staking.functions.balanceOf(u.address).call() for u in user]), "total supply should be the sum of all depositors stake"
    
        
def checked_withdrawal(u):
    state_before = get_state(user)
    u.transact(contract_staking.functions.withdrawAll())
    state_after = get_state(user)
    for uu in user:
        if uu.address == u.address: continue
        assert all(state_after[uu.address][k] == state_before[uu.address][k] for k in state_before[uu.address]), "my withdrawal should not affect others"
    assert state_after[u.address]['pending'] == 0, "pending should be 0"
    assert state_after[u.address]['stake'] == 0, "stake should be 0"
    assert state_after[u.address]['wavax'] == state_before[u.address]['wavax'] + state_before[u.address]['pending'], "wavax balance does not add up"
    assert state_after[u.address]['lava'] >= state_before[u.address]['lava'], "lava balance can't decrease"
    assert state_after[u.address]['lava'] <= state_before[u.address]['lava'] + state_before[u.address]['stake'], "lava balance can't increase more than the stake"   


def checked_advance_time(sec):
    state_before = get_state(user)
    advance_time(sec)
    state_after = get_state(user)
    for u in user:
        assert state_after[u.address]['pending'] == state_before[u.address]['pending'], "pending should not change with time"
        assert state_after[u.address]['stake'] == state_before[u.address]['stake'], "stake should not change without deposits/withdrawals"
        

def checked_time_invariance():
    state_0 = get_state(user)
    advance_time(365*24*3600)
    checked_all_claim()
    state_1 = get_state(user)
    advance_time(365*24*3600)
    checked_all_claim()
    state_2 = get_state(user)
    advance_time(182*24*3600)
    checked_all_claim()
    advance_time(183*24*3600)
    checked_all_claim()
    state_3 = get_state(user)
    for u in user:
        apr = state_1[u.address]['stake'] - state_0[u.address]['stake'] 
        assert abs(state_2[u.address]['stake'] - state_1[u.address]['stake'] - apr) <= 1e-3*apr, "apr not 100%"
        assert abs(state_3[u.address]['stake'] - state_2[u.address]['stake'] - apr) <= 1e-3*apr, "not invariant in time"


def checked_distribute_invariance():
    state0 = get_state(user)
    checked_distribute(w3.toWei(6, 'ether'))
    state1 = get_state(user)
    checked_distribute(w3.toWei(4, 'ether'))
    checked_distribute(w3.toWei(2, 'ether'))
    state2 = get_state(user)
    for u in user:
        batch = state1[u.address]['pending'] - state0[u.address]['pending']
        incremental = state2[u.address]['pending'] - state1[u.address]['pending']
        assert abs(incremental - batch) <= 1e-3*batch, "rewards are not invariant to splitting of payments"
        

def checked_setup():
    assert contract_staking.functions.asset().call() == lava, "wrong asset in staking contract"
    state0 = get_state(user)
    for u in state0:
        for k in state0[u]:
            if state0[u][k] != 0:
                raise ValueError(f"setup should only run on a clean state: state[{u}][{k}]={state[u][k]}")
    wallet.transact(wavax.functions.deposit(), value=w3.toWei(1000, 'ether'))
    wallet.transact(wavax.functions.approve(staking, 2**256-1))
    amount = w3.toWei(100000, 'ether')
    for u in user:
        wallet.transact(contract_lava.functions.transfer(u.address, amount))
        assert contract_lava.functions.balanceOf(u.address).call() == amount, "users do not have 100000 lava"
        u.transact(contract_lava.functions.approve(staking, 2**256-1))


# In[4]:


checked_setup()
print_state(user)


# In[5]:


for i,u in enumerate(user):
    checked_deposit(u, w3.toWei(10000*i, 'ether'))
print_state(user)


# In[6]:


for i,u in enumerate(user):
    stake = contract_staking.functions.balanceOf(u.address).call()
    lavabal = contract_lava.functions.balanceOf(u.address).call()
    assert w3.toWei(10000*i, 'ether') == stake, "users do not have the right stake"
    assert w3.toWei(100000, 'ether') == stake+lavabal, "tokens where lost"
print_state(user)


# In[7]:


checked_advance_time(365*24*60*60)


# In[8]:


checked_all_claim()
print_state(user)


# In[9]:


checked_distribute_invariance()
print_state(user)
for u in user:
    checked_withdrawal(u)
    assert contract_lava.functions.balanceOf(u.address).call() == w3.toWei(100000, 'ether'), "users do not have 100000 lava"
print_state(user)


# In[10]:


for u in user[:2]:
    checked_deposit(u,w3.toWei(10000, 'ether'))
print_state(user)


# In[11]:


checked_distribute(w3.toWei(10, 'ether'))
print_state(user)


# In[12]:


checked_all_claim()
print_state(user)


# In[13]:


advance_time(365*24*60*60)
print_state(user)


# In[14]:


checked_deposit(user[1],0)
print_state(user)


# In[15]:


checked_distribute(w3.toWei(3, 'ether'))
print_state(user)


# In[16]:


checked_deposit(user[0],0)
print_state(user)


# In[17]:


checked_deposit(user[1],0)
print_state(user)


# In[18]:


checked_withdrawal(user[0]) 
print_state(user)  


# In[19]:


checked_deposit(user[3],w3.toWei(40000, 'ether'))
print_state(user)  


# In[20]:


checked_all_claim()
print_state(user)  


# In[21]:


checked_distribute(w3.toWei(6, 'ether'))
print_state(user)


# In[22]:


checked_all_claim()
print_state(user)  


# In[23]:


checked_advance_time(365*24*60*60)
print_state(user)  
checked_all_claim()
print_state(user)


# In[24]:


checked_distribute(w3.toWei(11, 'ether'))
print_state(user)


# In[25]:


checked_deposit(user[1],w3.toWei(10000, 'ether'))
print_state(user)


# In[26]:


checked_advance_time(365*24*60*60)
print_state(user)


# In[27]:


checked_distribute(w3.toWei(12, 'ether'))
print_state(user)
checked_distribute(w3.toWei(12, 'ether'))
print_state(user)


# In[28]:


checked_deposit(user[1],0)
print_state(user)


# In[29]:


checked_all_claim()
print_state(user)


# In[30]:


checked_distribute(w3.toWei(18, 'ether'))
print_state(user)


# In[31]:


checked_all_claim()
print_state(user)


# In[32]:


for u in user:
    checked_withdrawal(u)
print_state(user)


# In[33]:


for i,u in enumerate(user):
    checked_deposit(u,w3.toWei(10000*i, 'ether'))
print_state(user)


# In[34]:


checked_advance_time(2*365*24*3600)
checked_all_claim()
print_state(user)


# In[35]:


checked_distribute(w3.toWei(36, 'ether'))
print_state(user)


# In[36]:


checked_advance_time(2*365*24*3600)
checked_distribute(w3.toWei(36, 'ether'))
print_state(user)


# In[37]:


checked_all_claim()
print_state(user)    


# In[38]:


checked_time_invariance()
print_state(user)


# In[40]:


wavax_in_contract = wavax.functions.balanceOf(contract_staking.address).call()
print('WAVAX wei left in contract:', wavax_in_contract)


# In[ ]:




