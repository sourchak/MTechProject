from __future__ import print_function


import os
from os import path
import string
import tensorflow as tf
import collections
import math
import sys
import numpy as np
import argparse
import zipfile
from tempfile import gettempdir
from six.moves import urllib
from six.moves import xrange
import argon2
from cryptography.fernet import Fernet
import base64
import shutil


bag_window=2
eom=4
alpha_offset=10
punc_offset=36
ch_width=2
tot_supprtd_char=63
embedding_size=128
base=8
password=b''
mem_cost=204800 #200MiB
hash_len=32
p=8
time=1
salt=b'somesalt'


def preprocessing(cover):
    l=list(cover)
    cover_text=[]
    for x in l:
        cover_text=cover_text+x.split(' ')
    n_wordLine=len(cover_text)
    new_text=[]
    # print(cover_text)
    pos=string.punctuation.find('.') # position of the period
    punc_Period=string.punctuation[0:pos]+string.punctuation[pos+1:] # removes period from string.punctuation

    for x in cover_text:
        # apparently the best way to remove punctuations
        # https://stackoverflow.com/questions/265960/best-way-to-strip-punctuation-from-a-string-in-python
        # unpunctuated_str=string.translate(x,None,string.punctuation)
        perioded_str=string.translate(x,None,punc_Period) # removes all punctuations except period
        # noNewLine_str=string.replace(unpunctuated_str,'\n','')
        noNewLine_perioded_str=string.replace(perioded_str,'\n','') # replace newline with empty string
        noNewLine_perioded_str=string.replace(noNewLine_perioded_str,'\r','')
        # new_text=new_text+[noNewLine_str]

        # new_text is a list of words where newline is replaced by '' and
        # punctuations, except '.' have been removed
        new_text=new_text+[noNewLine_perioded_str]


    word_to_context=dict()
    assert n_wordLine==len(new_text)
    # print(new_text)
    x=0
    while x < n_wordLine :
        if x-bag_window>-1 and x+bag_window<n_wordLine and new_text[x]!='' and new_text[x][-1:]!='.':
            buffer=new_text[x-bag_window:x]+new_text[x+1:x+bag_window+1] #[m words][x][m words]
            flag=True
            i=0
            while i<len(buffer) and flag==True:
                if i!=len(buffer)-1 and buffer[i][-1:]!='.' and buffer[i]!='':
                    i=i+1
                elif i==len(buffer)-1 and buffer[i]!='':
                    if buffer[i][-1:]=='.':
                        buffer[i]=buffer[i][:-1]
                    i=i+1
                else:
                    flag=False
            if flag==True:
                word_to_context[x]=buffer
                # print("Buffer "+str(x))
                # print(buffer)
                x=x+bag_window
            else:
                flag=True
        x=x+1
    locations=word_to_context.keys() # locations to encrypt
    # print(word_to_context)
    # print("Length of word_to_context="+ str(len(word_to_context)))
    # print("Locations to encrypt: " +  str(locations))
    return cover_text, word_to_context


def cover_preprocessing(option):
    cover=None
    strng='Path to %s text: '%option
    while not cover:
        cover_path=raw_input(strng)
        try:
            if path.exists(path.abspath(cover_path)):
                cover=open(path.abspath(cover_path),'r')
                #for x in list(cover):
                #    print(x)
                cover_text, loc_contexts=preprocessing(cover)
                #for x in loc_contexts.keys():
                #    print(str(x)+'->',end='')
                #    print(loc_contexts[x])
                return cover_text,loc_contexts
            else:
                print(option.capitalize() +' text file does not exist, or you do not have required premissions on the file.')
        except IOError:
            print('An error occured while trying to read the cover file.')

def octalify(raw_message):
    # convert the message to its special octal form
    message=''
    punc=string.punctuation.translate(None,'~#%<=>^')+' '+'\n'
    for x in raw_message:
        if x.isdigit():
            message=message+str(oct(ord(x)-ord('0')))[1:].rjust(2,'0') # 0,1,2,3,4,5,6,7,8,9 for digits
        elif x.isalpha():
            message=message+str(oct(ord(x.upper())-ord('A')+alpha_offset))[1:] # 10,11,12,... for alphabets
        elif x in punc:
            #print('Inside octalify: '+str(oct(punc.find(x)+36))[1:])
            message=message+str(oct(punc.find(x)+punc_offset))[1:]
        else:
            print(x+' is an unsupported character.')
    message=message+'7777' # boundary condition
    #print (message)
    return  message

def inv_octalify(octal_message):
    message=''
    x=0
    punc=string.punctuation.translate(None,'~#%<=>^')+' '+'\n'
    #print(len(octal_message))
    while x<len(octal_message):
        #print(octal_message[x:x+2])
        m=int(octal_message[x:x+2],8)
        if m<alpha_offset:
            message=message+chr(m+ord('0'))
        elif m<punc_offset:
            message=message+chr(m+ord('A')-alpha_offset)
        elif m<tot_supprtd_char:
            message=message+punc[m-punc_offset]
        x=x+2
    return message

def read_message():
    message_file=raw_input('Path to message: ')
    if path.exists(path.abspath(message_file)):
        raw_message=open(path.abspath(message_file),'r')
        message=octalify(raw_message.read())
        return message
    else:
        print('Message file does not exist, or you do not have required permissions on the file')

def word2vecEvaluator(log,contexts):
    all_words=list()
    words_codes=dict()
    if path.exists(path.join(log,'metadata.tsv')):
        all_words=list(open(path.join(log,'metadata.tsv')))
    for i in range(0,len(all_words)):
        all_words[i]=all_words[i].translate(None,'\n')
        words_codes[all_words[i]]=i
    coded_contexts=dict()
    for i in sorted(contexts):
        coded_contexts[i]=[ words_codes[x] if x in all_words else 0 for x in contexts[i] ]
    # print(coded_contexts)
    embeddings=tf.get_variable("embeddings/embeddings",shape=[len(all_words),embedding_size])
    weights=tf.get_variable("weights/weights",shape=[len(all_words),embedding_size])
    biases=tf.get_variable("biases/biases",shape=[len(all_words)])
    norm=tf.sqrt(tf.reduce_sum(tf.square(embeddings),1,keepdims=True))
    normalized_embeddings=embeddings/norm
    saver=tf.train.Saver()
    locs=sorted(coded_contexts)
    context_vecs=tf.placeholder(tf.float32,[len(locs),embedding_size])
    ids=tf.placeholder(tf.int32,[2*bag_window])
    req_embeddings=tf.nn.embedding_lookup(normalized_embeddings,ids)
    predictor=tf.nn.bias_add(tf.matmul(context_vecs,weights,transpose_b=True),biases)
    with tf.Session() as session:
        saver.restore(session,path.join(log,'model.ckpt'))
        context_sum=np.zeros((len(locs),embedding_size))
        #print(normalized_embeddings.eval()[:8,:10])
        for i in range(0,len(locs)):
            context_sum[i]=tf.reduce_sum(req_embeddings,0).eval(feed_dict={ids:coded_contexts[locs[i]]}) /(2*bag_window)
        giant_prediction=predictor.eval(feed_dict={context_vecs:context_sum})
        selected_words=dict()
        for i in range(0,len(locs)):
            selected_code_words=(-giant_prediction[i]).argsort()[:base+1]
            selected_words[locs[i]]=[all_words[x] for x in selected_code_words if all_words[x]!='UNK'] #this removes 'UNK' words from consideration
            selected_words[locs[i]]=selected_words[locs[i]][:base]
    return selected_words

def request_password():
    password=raw_input('Enter password: ')
    hash_password=argon2.low_level.hash_secret_raw(str.encode(password),salt,time_cost=time,
                                                  memory_cost=mem_cost,
                                                   parallelism=p,
                                                   hash_len=hash_len,type=argon2.low_level.Type.I)
    return base64.urlsafe_b64encode(hash_password)

def decrypt_ckpt(log,hashed_password):
    log_dir='temp_log'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    with open(os.path.join(log_dir,'model.ckpt.meta'),'wb') as f:
        f.write(Fernet(hashed_password).decrypt(open(os.path.join(log,'model.ckpt.meta'),'rb').read()))
    with open(os.path.join(log_dir,'model.ckpt.index'),'wb') as f:
        f.write(Fernet(hashed_password).decrypt(open(os.path.join(log,'model.ckpt.index'),'rb').read()))
    with open(os.path.join(log_dir,'metadata.tsv'),'wb') as f:
        f.write(Fernet(hashed_password).decrypt(open(os.path.join(log,'metadata.tsv'),'rb').read()))
    with open(os.path.join(log_dir,'model.ckpt.data-00000-of-00001'),'wb') as f:
        f.write(Fernet(hashed_password).decrypt(open(os.path.join(log,'model.ckpt.data-00000-of-00001'),'rb').read()))

    return log_dir


def embed(cover_text,loc_contexts,message):
    # TO DO: This will use word2vec to make the predictions and store them in
    # dictionary loc_words.
    loc_words=dict()
    msg_ptr=0
    end=0
    log=path.abspath(raw_input('Path to log_dir: '))
    hashed_password=request_password()
    log=decrypt_ckpt(log,hashed_password)
    words=word2vecEvaluator(log,loc_contexts)
    for loc in sorted(loc_contexts):
        if msg_ptr<len(message):
            # print('loc='+str(loc), msg_ptr, message_vec[msg_ptr])
            loc_words[loc]=words[loc][int(message[msg_ptr])]
            msg_ptr=msg_ptr+1
            end=loc
    #Octalify takes care of End of Message decided to be 7777 in octal
    if msg_ptr>=len(message):
        for loc in sorted(loc_words):
            # print('loc='+str(loc))
            cover_text[loc]=loc_words[loc]
            if loc==end:
                break
        embedded_msg=' '.join(cover_text)
        with open('Encrypted_Message.txt','w') as steganogram:
            steganogram.write(embedded_msg)
    else:
        print('Cover insufficient. Steganogram not created.')


def extractor(cover_text,loc_contexts):
    flag=True
    log=path.abspath(raw_input('Path to log_dir: '))
    hashed_password=request_password()
    log=decrypt_ckpt(log,hashed_password)
    consec_seven=0 #to keep track of consecutive 7s, 4 7s assumed to signal message end
    octal_message=''
    words=word2vecEvaluator(log,loc_contexts)
    for loc in sorted(loc_contexts):
        if flag:
            pos=words[loc].index(cover_text[loc])
            octal_message=octal_message+str(pos)
            if pos==7:
                if len(octal_message)%2==1 and consec_seven==0:
                    consec_seven=1
                elif consec_seven>0:
                    consec_seven=consec_seven+1
            elif pos!=7:
                consec_seven=0
            if consec_seven==4:
                    flag=False
    if not flag:
        octal_message=octal_message[:-4]
    message=inv_octalify(octal_message)
    with open('Extracted_Message.txt','w') as extrctd_msg:
        extrctd_msg.write(message)
    return message

def main():
    choice=raw_input('embed or extract: ')
    if choice=='embed':
        cover_text, loc_contexts=cover_preprocessing('cover')
        message=read_message()
        embed(cover_text,loc_contexts,message)
    elif choice=='extract':
        cover_text,loc_contexts=cover_preprocessing('stego')
        message=extractor(cover_text,loc_contexts)

    if os.path.exists('temp_log'):
        shutil.rmtree('temp_log')

if __name__=='__main__':
    main()
