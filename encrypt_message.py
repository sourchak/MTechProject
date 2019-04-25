from cryptography.fernet import Fernet
import argon2
import os
import base64

password=b''
mem_cost=204800 #200MiB
hash_len=32
p=8
time=1
salt=b'somesalt'

def request_password():
    password=raw_input('Enter password: ')
    hash_password=argon2.low_level.hash_secret_raw(str.encode(password),salt,time_cost=time,
                                                  memory_cost=mem_cost,
                                                   parallelism=p,
                                                   hash_len=hash_len,type=argon2.low_level.Type.I)
    return base64.urlsafe_b64encode(hash_password)

def encrypt_ckpt(model,key):
    with open('encrypted_model.eckpt','wb') as f:
        f.write(Fernet(key).encrypt(open(model,'rb').read()))

def decrypt_ckpt(emodel,key):
    with open('model.ckpt','wb') as f:
        f.write(Fernet(key).decrypt(open(emodel,'rb').read()))

hashed_password=request_password()
print hashed_password
encrypt_ckpt('Word2Vec/log/model.ckpt.meta',hashed_password)
decrypt_ckpt('encrypted_model.eckpt',hashed_password)
