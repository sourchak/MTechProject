from __future__ import print_function
from os import path
import string


skip_window=2


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
        if x-skip_window>-1 and x+skip_window<n_wordLine and new_text[x]!='' and new_text[x][-1:]!='.':
            buffer=new_text[x-skip_window:x]+new_text[x+1:x+skip_window+1] #[m words][x][m words]
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
                x=x+skip_window
            else:
                flag=True
        x=x+1
    locations=word_to_context.keys() # locations to encrypt
    # print(word_to_context)
    # print("Length of word_to_context="+ str(len(word_to_context)))
    # print("Locations to encrypt: " +  str(locations))
    return cover_text, word_to_context


def cover_preprocessing():
    cover=None
    while not cover:
        cover_path=raw_input('Path to cover text: ')
        try:
            if path.exists(path.abspath(cover_path)):
                cover=open(path.abspath(cover_path),'r')
                #for x in list(cover):
                #    print(x)
                cover_text, loc_contexts=preprocessing(cover)
                for x in loc_contexts.keys():
                    print(str(x)+'->',end='')
                    print(loc_contexts[x])
                return cover_text,loc_contexts
            else:
                print('Cover text file does not exist, or you do not have required premissions on the file.')
        except IOError:
            print('An error occured while trying to read the cover file.')

def octalify(raw_message):
    # convert the message to its special octal form 
    return message

def read_message():
    message_file=raw_input('Path to message: ')
    if path.exists(path.abspath(message_file)):
        raw_message=open(path.abspath(message_file))
        message=octalify(raw_message)
        return message
    else:
        print('Message file does not exist, or you do not have required permissions on the file')

def embed(cover_text,loc_contexts,message):
    # TO DO: This will use word2vec to make the predictions and store them in
    # dictionary loc_words.
    loc_words=dict()
    msg_ptr=0
    for loc in sorted(loc_contexts) and msg_ptr<len(message):
        words=word2vec(log,eval)
        loc_words[loc]=words[int(message[msg_ptr])]
        msg_ptr=msg_ptr+1
    for loc in loc_words:
        cover_text[loc]=loc_words[loc]
    embedded_msg=' '.join(cover_text)
    with open('Encrypted_Message.txt','w') as steganogram:
        steganogram.write(embedded_msg)


cover_text, loc_contexts=cover_preprocessing()
message=read_message()
embed(cover_text,loc_contexts,message)
