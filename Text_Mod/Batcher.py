import string

skip_window=2

f=open('./aesop10.txt','r')
l=list(f)
original_text=[]
for x in l:
    original_text=original_text+x.split(' ')
n_wordLine=len(original_text)
new_text=[]
# print original_text
pos=string.punctuation.find('.') # position of the period
punc_Period=string.punctuation[0:pos]+string.punctuation[pos+1:] # removes period from string.punctuation

for x in original_text:
    # apparently the best way to remove punctuations
    # https://stackoverflow.com/questions/265960/best-way-to-strip-punctuation-from-a-string-in-python
    # unpunctuated_str=string.translate(x,None,string.punctuation)
    perioded_str=string.translate(x,None,punc_Period) # removes all punctuations except period
    # noNewLine_str=string.replace(unpunctuated_str,'\n','')
    noNewLine_perioded_str=string.replace(perioded_str,'\n','') # replace newline with empty string
    noNewLine_perioded_str=string.replace(noNewLine_perioded_str,'\r','') 
    # new_text=new_text+[noNewLine_str]

    # new_text is a list of words where newline is replaced by '' and punctuations except '.' have been removed
    new_text=new_text+[noNewLine_perioded_str]


word_to_context=dict()
assert n_wordLine==len(new_text)
print new_text
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
            print "Buffer "+str(x)
            print buffer
            x=x+skip_window
        else:
            flag=True
    x=x+1
locations=word_to_context.keys() # locations to encrypt
# print word_to_context
# print "Length of word_to_context="+ str(len(word_to_context))
# print "Locations to encrypt: " +  str(locations)
