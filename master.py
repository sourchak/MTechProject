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
    punc=string.punctuation.translate(None,'~#%<=>^')+' '
    for x in raw_message:
        if x.isdigit():
            message=message+str(oct(ord(x)-ord('0')))[1:].rjust(2,'0') # 0,1,2,3,4,5,6,7,8,9 for digits
        elif x.isalpha():
            message=message+str(oct(ord(x.upper())-ord('A')+10))[1:] # 10,11,12,... for alphabets
        elif x in punc:
            #print('Inside octalify: '+str(oct(punc.find(x)+36))[1:])
            message=message+str(oct(punc.find(x)+36))[1:]
        else:
            print(x+' is an unsupported character.')
    message=message+'7777' # boundary condition
    #print (message)
    return  message

def inv_octalify(octal_message):
    message=''
    x=0
    punc=string.punctuation.translate(None,'~#%<=>^')+' '
    #print(len(octal_message))
    while x<len(octal_message):
        #print(octal_message[x:x+2])
        m=int(octal_message[x:x+2],8)
        if m<10:
            message=message+chr(m+ord('0'))
        elif m<36:
            message=message+chr(m+ord('A')-10)
        elif m<62:
            message=message+punc[m-36]
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

def word2vecEvaluator(log,context):
    return ['0','1','2','3','4','5','6','7']

def embed(cover_text,loc_contexts,message):
    # TO DO: This will use word2vec to make the predictions and store them in
    # dictionary loc_words.
    loc_words=dict()
    msg_ptr=0
    end=0
    log='' # this will be changed once word2vec is mereged with this.
    for loc in sorted(loc_contexts):
        if msg_ptr<len(message):
            words=word2vecEvaluator(log,loc_contexts[loc])
            # print('loc='+str(loc), msg_ptr, message_vec[msg_ptr])
            loc_words[loc]=words[int(message[msg_ptr])]
            msg_ptr=msg_ptr+1
            end=loc
    #TO DO: Take care of End of Message decided to be 7777 in octal
    for loc in sorted(loc_words):
        # print('loc='+str(loc))
        cover_text[loc]=loc_words[loc]
        if loc==end:
            break
    embedded_msg=' '.join(cover_text)
    with open('Encrypted_Message.txt','w') as steganogram:
        steganogram.write(embedded_msg)


def extractor(cover_text,loc_contexts):
    flag=True
    log='' # like embed, this too will be changed once word2vec is merged 
    consec_seven=0 #to keep track of consecutive 7s, 4 7s assumed to signal message end
    octal_message=''
    for loc in sorted(loc_contexts):
        if flag:
            words=word2vecEvaluator(log,loc_contexts[loc])
            pos=words.index(cover_text[loc])
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


choice=raw_input('embed or extract: ')
if choice=='embed':
    cover_text, loc_contexts=cover_preprocessing('cover')
    message=read_message()
    embed(cover_text,loc_contexts,message)
elif choice=='extract':
    cover_text,loc_contexts=cover_preprocessing('stego')
    message=extractor(cover_text,loc_contexts)