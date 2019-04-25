from cryptography.fernet import Fernet
import os


password=''

def request_password():
    p=raw_input('Enter password: ')
    return p

def key_gen():
    with open('key.txt','wb') as f:
        f.write(Fernet.generate_key())

def encrypt_ckpt(model,key):
    if os.path.exists(key):
        with open('encrypted_model.eckpt','wb') as f:
            f.write(Fernet(open(key,'rb').read()).encrypt(open(model,'rb').read()))

def decrypt_ckpt(emodel,key):
    if os.path.exists(key):
        with open('model.ckpt','wb') as f:
            f.write(Fernet(open(key,'rb').read()).decrypt(open(emodel,'rb').read()))

key_gen()
p=request_password()
print p
encrypt_ckpt('Word2Vec/log/model.ckpt.meta','key.txt')
decrypt_ckpt('encrypted_model.eckpt','key.txt')
