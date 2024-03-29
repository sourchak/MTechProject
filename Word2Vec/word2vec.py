# Copyright 2015 The TensorFlow Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
"""Basic word2vec example."""


from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import collections
import math
import os
import random
import sys
from tempfile import gettempdir
import zipfile

import numpy as np
from six.moves import urllib
from six.moves import xrange  # pylint: disable=redefined-builtin
import tensorflow as tf
import string

from cryptography.fernet import Fernet
import argon2
import base64

from tensorflow.contrib.tensorboard.plugins import projector


data_index = 0
password=b''
mem_cost=204800
hash_len=32
p=8
time=1
salt=b'somesalt'

def cover_context_generator():
    bag_window=2
    skip_window=bag_window
    
    f=open(os.path.abspath('aesop10.txt'),'r')
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
    # print new_text
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
                print("Buffer "+str(x))
                print(buffer)
                x=x+skip_window
            else:
                flag=True
        x=x+1
    locations=word_to_context.keys() # locations to encrypt
    # print word_to_context
    # print "Length of word_to_context="+ str(len(word_to_context))
    # print "Locations to encrypt: " +  str(locations)
    return word_to_context


def request_password():
    password=raw_input('Enter password: ')
    hash_password=argon2.low_level.hash_secret_raw(str.encode(password),salt,time_cost=time,
                                                  memory_cost=mem_cost,
                                                   parallelism=p,
                                                   hash_len=hash_len,type=argon2.low_level.Type.I)
    return base64.urlsafe_b64encode(hash_password)

def encrypt_ckpt(log_dir,filename,hashed_password):
    dir_name='encrypted_log'
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)
    with open(os.path.join(dir_name,filename),'wb') as f:
        f.write(Fernet(hashed_password).encrypt(open(os.path.join(log_dir,filename),'rb').read()))

def export_encrypted(log_dir):
    hashed_password=request_password()
    encrypt_ckpt(log_dir,'metadata.tsv',hashed_password)
    encrypt_ckpt(log_dir,'model.ckpt.meta',hashed_password)
    encrypt_ckpt(log_dir,'model.ckpt.index',hashed_password)
    encrypt_ckpt(log_dir,'model.ckpt.data-00000-of-00001',hashed_password)
    print('Encrypted Logs saved at: '+os.path.abspath('encrypted_log'))



def word2vec_basic(log_dir,choice):
    """Example of building, training and visualizing a word2vec model."""
    # Create the directory for TensorBoard variables if there is not.
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Step 1: Download the data.
    url = 'http://mattmahoney.net/dc/'

    # pylint: disable=redefined-outer-name
    def maybe_download(filename, expected_bytes):
        """Download a file if not present, and make sure it's the right size."""
        local_filename = os.path.join(gettempdir(), filename)
        if not os.path.exists(local_filename):
            local_filename, _ = urllib.request.urlretrieve(url + filename,
                                                     local_filename)
        print(local_filename)
        statinfo = os.stat(local_filename)
        if statinfo.st_size == expected_bytes:
            print('Found and verified', filename)
        else:
            print(statinfo.st_size)
            raise Exception('Failed to verify ' + local_filename +
                      '. Can you get to it with a browser?')
        return local_filename

    filename = maybe_download('text8.zip', 31344016)

    # Read the data into a list of strings.
    def read_data(filename):
        """Extract the first file enclosed in a zip file as a list of words."""
        with zipfile.ZipFile(filename) as f:
            data = tf.compat.as_str(f.read(f.namelist()[0])).split()
        return data

    vocabulary = read_data(filename)
    print('Data size', len(vocabulary))

    # Step 2: Build the dictionary and replace rare words with UNK token.
    vocabulary_size = 50000

    def build_dataset(words, n_words):
        """Process raw inputs into a dataset."""
        count = [['UNK', -1]]
        count.extend(collections.Counter(words).most_common(n_words - 1))
        dictionary = dict()
        for word, _ in count:
          dictionary[word] = len(dictionary)
        data = list()
        unk_count = 0
        for word in words:
          index = dictionary.get(word, 0)
          if index == 0:  # dictionary['UNK']
            unk_count += 1
          data.append(index)
        count[0][1] = unk_count
        reversed_dictionary = dict(zip(dictionary.values(), dictionary.keys()))
        return data, count, dictionary, reversed_dictionary

    # Filling 4 global variables:
    # data - list of codes (integers from 0 to vocabulary_size-1).
    #   This is the original text but words are replaced by their codes
    # count - map of words(strings) to count of occurrences
    # dictionary - map of words(strings) to their codes(integers)
    # reverse_dictionary - maps codes(integers) to words(strings)
    data, count, unused_dictionary, reverse_dictionary = build_dataset(
      vocabulary, vocabulary_size)
    del vocabulary  # Hint to reduce memory.
    print('Most common words (+UNK)', count[:5])
    print('Sample data', data[:10], [reverse_dictionary[i] for i in data[:10]])

    # Step 3: Function to generate a training batch for the skip-gram model.
    def generate_batch(batch_size, bag_window):
        global data_index
        # assert batch_size % num_skips == 0
        # assert num_skips <= 2 * skip_window
        batch = np.ndarray(shape=(batch_size,2*bag_window), dtype=np.int32)
        labels = np.ndarray(shape=(batch_size, 1), dtype=np.int32)
        span = 2 * bag_window + 1  # [ skip_window target skip_window ]
        buffer = collections.deque(maxlen=span)  # pylint: disable=redefined-builtin
        if data_index + span > len(data):
          data_index = 0
        buffer.extend(data[data_index:data_index + span])
        data_index += span
        for i in range(batch_size):
          context_words = [buffer[w] for w in range(span) if w != bag_window]
          # words_to_use = random.sample(context_words, num_skips)
          # for j, context_word in enumerate(words_to_use):
          #   batch[i * num_skips + j] = buffer[skip_window]
          #   labels[i * num_skips + j, 0] = buffer[context_word]
          batch[i]=context_words
          labels[i,0]=buffer[bag_window]
          if data_index == len(data):
            buffer.extend(data[0:span])
            data_index = span
          else:
            buffer.append(data[data_index])
            data_index += 1
        # Backtrack a little bit to avoid skipping words in the end of a batch
        data_index = (data_index + len(data) - span) % len(data)
        return batch, labels

    batch, labels = generate_batch(batch_size=8, bag_window=2)
    for i in range(8):
        print(batch[i], [reverse_dictionary[batch[i][x]] for x in range(4)], '->', labels[i, 0],
          reverse_dictionary[labels[i, 0]])

    # Step 4: Build and train a cbow model.

    batch_size = 128
    embedding_size = 128  # Dimension of the embedding vector.
    bag_window = 2  # How many words to consider left and right.
    # num_skips = 2  # How many times to reuse an input to generate a label.
    num_sampled = 64  # Number of negative examples to sample.

    # We pick a random validation set to sample nearest neighbors. Here we limit
    # the validation samples to the words that have a low numeric ID, which by
    # construction are also the most frequent. These 3 variables are used only for
    # displaying model accuracy, they don't affect calculation.
    valid_size = 16  # Random set of words to evaluate similarity on.
    valid_window = 100  # Only pick dev samples in the head of the distribution.
    valid_examples = np.random.choice(valid_window, valid_size, replace=False)

    graph = tf.Graph()

    with graph.as_default():
        # Input data.
        with tf.name_scope('inputs'):
          train_inputs = tf.placeholder(tf.int32, shape=[batch_size,bag_window*2])
          train_labels = tf.placeholder(tf.int32, shape=[batch_size, 1])
          valid_dataset = tf.constant(valid_examples, dtype=tf.int32)
          encrypt_batch=tf.placeholder(tf.int32,shape=[None,bag_window*2]) #cover_size is the number of encryption positions found in the cover

        # Ops and variables pinned to the CPU because of missing GPU implementation
        with tf.device('/cpu:0'):
            # Look up embeddings for inputs.
            with tf.name_scope('embeddings'):
                embeddings = tf.Variable(tf.random_uniform([vocabulary_size,
                                                            embedding_size],
                                                           -1.0,
                                                           1.0),name='embeddings')
                embed=tf.Variable(tf.zeros([batch_size,embedding_size]))
            for j in range(bag_window*2):
                embed =embed + tf.nn.embedding_lookup(embeddings, train_inputs[:,j])
            #cbow_norm=tf.sqrt(tf.reduce_sum(tf.square(embed),1,keepdims=True))
            #embed=embed/(cbow_norm) #normalizations is fruitless
            embed=embed/(2*bag_window)
            encrpt_embed=tf.Variable(tf.zeros([batch_size,embedding_size]))
            for j in range(bag_window*2):
                encrpt_embed=encrpt_embed+tf.nn.embedding_lookup(embeddings,encrypt_batch[:,j])
            encrpt_embed=encrpt_embed/(2*bag_window)
            #cbow_norm_encrpt=tf.sqrt(tf.reduce_sum(tf.square(encrpt_embed),1,keepdims=True))
            #encrpt_embed=encrpt_embed/cbow_norm_encrpt #normalization is fruitless

        # Construct the variables for the NCE loss
        with tf.name_scope('weights'):
            nce_weights = tf.Variable(tf.truncated_normal([vocabulary_size,
                                                           embedding_size],stddev=1.0
                                                          /
                                                          math.sqrt(embedding_size)),name='weights') # These are the target word vectors.
        with tf.name_scope('biases'):
            nce_biases = tf.Variable(tf.zeros([vocabulary_size]),name='biases')

        # Compute the average NCE loss for the batch.
        # tf.nce_loss automatically draws a new sample of the negative labels each
        # time we evaluate the loss.
        # Explanation of the meaning of NCE loss:
        #   http://mccormickml.com/2016/04/19/word2vec-tutorial-the-skip-gram-model/
        with tf.name_scope('loss'):
            loss =tf.reduce_mean(tf.nn.nce_loss(weights=nce_weights,biases=nce_biases,labels=train_labels,inputs=embed,num_sampled=num_sampled,num_classes=vocabulary_size,partition_strategy='div'))
        # Add the loss value as a scalar to summary.
        tf.summary.scalar('loss', loss)

        with tf.name_scope('learning_rate'):
            strt_learning_rate=1.0
            global_step=tf.Variable(0)
            learning_rate=tf.train.exponential_decay(strt_learning_rate,global_step,20000,0.7,staircase=True)
        # Construct the SGD optimizer using a learning rate of 1.0.
        with tf.name_scope('optimizer'):
            optimizer =tf.train.GradientDescentOptimizer(learning_rate).minimize(loss,global_step=global_step)

        # Compute the cosine similarity between minibatch examples and all
        # embeddings.
        norm = tf.sqrt(tf.reduce_sum(tf.square(embeddings), 1, keepdims=True))
        normalized_embeddings = embeddings / norm
        valid_embeddings = tf.nn.embedding_lookup(normalized_embeddings,
                                              valid_dataset)

        # here to predictor (294) is testing
        similarity = tf.matmul(valid_embeddings, normalized_embeddings, transpose_b=True)
        #predictor=-tf.sigmoid(tf.matmul(encrpt_embed,normalized_embeddings,transpose_b=True))
        predictor=tf.nn.bias_add(tf.matmul(encrpt_embed,nce_weights,transpose_b=True),nce_biases)
        # Merge all summaries.
        merged = tf.summary.merge_all()

        # Add variable initializer.
        init = tf.global_variables_initializer()

        # Create a saver.
        saver = tf.train.Saver()

    # Step 5: Begin training.
    num_steps = 100001 #100001
    if choice == 'train':
        with tf.Session(graph=graph) as session:
            # Open a writer to write summaries.
            writer = tf.summary.FileWriter(log_dir, session.graph)

            # We must initialize all variables before we use them.
            init.run()
            print('Initialized')

            average_loss = 0
            for step in xrange(num_steps):
                batch_inputs, batch_labels = generate_batch(batch_size, bag_window)
                feed_dict = {train_inputs: batch_inputs, train_labels: batch_labels}

                # Define metadata variable.
                run_metadata = tf.RunMetadata()

                # We perform one update step by evaluating the optimizer op (including it
                # in the list of returned values for session.run()
                # Also, evaluate the merged op to get all summaries from the returned
                # "summary" variable. Feed metadata variable to session for visualizing
                # the graph in TensorBoard.
                _, summary, loss_val = session.run([optimizer, merged, loss],
                                                 feed_dict=feed_dict,
                                                 run_metadata=run_metadata)
                average_loss += loss_val

                # Add returned summaries to writer in each step.
                writer.add_summary(summary, step)
                # Add metadata to visualize the graph for the last run.
                if step == (num_steps - 1):
                    writer.add_run_metadata(run_metadata, 'step%d' % step)

                if step % 2000 == 0:
                    if step > 0:
                        average_loss /= 2000
                    # The average loss is an estimate of the loss over the last 2000
                    # batches.
                    print('Average loss at step ', step, ': ', average_loss)
                    average_loss = 0

                # Note that this is expensive (~20% slowdown if computed every 500 steps)
                if step % 100000 == 0:
                    sim = similarity.eval()
                    for i in xrange(valid_size):
                        valid_word = reverse_dictionary[valid_examples[i]]
                        top_k = 8  # number of nearest neighbors
                        nearest = (-sim[i, :]).argsort()[1:top_k + 1]
                        log_str = 'Nearest to %s:' % valid_word
                        for k in xrange(top_k):
                            close_word = reverse_dictionary[nearest[k]]
                            log_str = '%s %s,' % (log_str, close_word)
                        print(log_str)
            final_embeddings = normalized_embeddings.eval()
            print(final_embeddings[:8,:10])
            # Write corresponding labels for the embeddings.
            with open(log_dir + '/metadata.tsv', 'w') as f:
                for i in xrange(vocabulary_size):
                    f.write(reverse_dictionary[i] + '\n')

            # Save the model for checkpoints.
            saver.save(session, os.path.join(log_dir, 'model.ckpt'))

            # Create a configuration for visualizing embeddings with the labels in
            # TensorBoard.
            config = projector.ProjectorConfig()
            embedding_conf = config.embeddings.add()
            embedding_conf.tensor_name = embeddings.name
            embedding_conf.metadata_path = os.path.join(log_dir, 'metadata.tsv')
            projector.visualize_embeddings(writer, config)
        writer.close()
            # Step 6: Visualize the embeddings.
        export_encrypted(log_dir)
        # pylint: disable=missing-docstring
        # Function to draw visualization of distance between embeddings.
        def plot_with_labels(low_dim_embs, labels, filename):
            assert low_dim_embs.shape[0] >= len(labels), 'More labels than embeddings'
            plt.figure(figsize=(18, 18))  # in inches
            for i, label in enumerate(labels):
                x, y = low_dim_embs[i, :]
                plt.scatter(x, y)
                plt.annotate(label,xy=(x, y),xytext=(5, 2),textcoords='offset points',ha='right',va='bottom')
            plt.savefig(filename)

        try:
            # pylint: disable=g-import-not-at-top
            from sklearn.manifold import TSNE
            import matplotlib.pyplot as plt

            tsne = TSNE(
                perplexity=30, n_components=2, init='pca', n_iter=5000, method='exact')
            plot_only = 500
            low_dim_embs = tsne.fit_transform(final_embeddings[:plot_only, :])
            labels = [reverse_dictionary[i] for i in xrange(plot_only)]
            plot_with_labels(low_dim_embs, labels,os.path.join('DistributionInVectorSpace.png'))

        except ImportError as ex:
            print('Please install sklearn, matplotlib, and scipy to show embeddings.')
            print(ex)
    else:
        # TO DO: Take the encryption stream.
        # convert the stream into octal.
        # embed the choices in the cover.
        # Store the cover.
        # Perform inverse operation.
        with tf.Session(graph=graph) as session:
            saver.restore(session,os.path.join(log_dir,'model.ckpt'))
            print(normalized_embeddings.eval()[:8,0:10])
            encrpt_batch=cover_context_generator()
            locs=list()
            locs_context=list()
            locs=sorted(encrpt_batch)
            for x in locs:
                locs_context=locs_context+[[unused_dictionary[y] if unused_dictionary.has_key(y) else 0 for y in encrpt_batch[x]]]
            x=0
            for i in range(1,len(locs)//128):
                feed_dict={encrypt_batch:locs_context[(i-1)*128:i*128]}
                predictions=predictor.eval(feed_dict=feed_dict)
                #print('Predictions', predictions)
                for j in range(128):
                    top_candidates=(-predictions[j,:]).argsort()[0:8] #this is the value to be returned
                    log_str = 'Nearest to %s ->[%s, %s, %s,%s]'%(str(locs[x]),reverse_dictionary[locs_context[x][0]],reverse_dictionary[locs_context[x][1]],reverse_dictionary[locs_context[x][2]],reverse_dictionary[locs_context[x][3]])
                    for k in range(8):
                        close_word = reverse_dictionary[top_candidates[k]]
                        log_str = '%s %s,' % (log_str, close_word)
                    x=x+1
                print(log_str)


# All functionality is run after tf.app.run() (b/122547914). This could be split
# up but the methods are laid sequentially with their usage for clarity.
def main(unused_argv):
    # Give a folder path as an argument with '--log_dir' to save
    # TensorBoard summaries. Default is a log folder in current directory.
    current_path = os.path.dirname(os.path.realpath(sys.argv[0]))
    parser = argparse.ArgumentParser()
    parser.add_argument(
            '--log_dir',
            type=str,
            default=os.path.join(current_path, 'log'),
            help='The log directory for TensorBoard summaries.')
    parser.add_argument(
            '--choice',
            type=str,
            default='train',
            help='Mode of operation.')
    flags, unused_flags = parser.parse_known_args()
    word2vec_basic(flags.log_dir,flags.choice)
    #testing
    #word2vec_basic(flags.log_dir,'eval')

if __name__ == '__main__':
  tf.app.run()
