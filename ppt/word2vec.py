# Copyright 2015 The TensorFlow Authors. All Rights Reserved.
#
# Modifications copyright (C) 2019 Sourit Chakraborty.
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


def word2vec_cbow(log_dir,choice):
    """Example of building, training and visualizing a word2vec model."""
    # Create the directory for TensorBoard variables if there is not.
    batch_size = 128
    embedding_size = 256  # Dimension of the embedding vector.
    bag_window = 4  # How many words to consider left and right.
    decay_rate=0.4
    num_sampled = 64  # Number of negative examples to sample. 
    vocabulary_size = 50000
    # We pick a random validation set to sample nearest neighbors. Here we limit
    # the validation samples to the words that have a low numeric ID, which by
    # construction are also the most frequent. These 3 variables are used only for
    # displaying model accuracy, they don't affect calculation.
    valid_size = 16  # Random set of words to evaluate similarity on.
    valid_window = 100  # Only pick dev samples in the head of the distribution.
    valid_examples = np.random.choice(valid_window, valid_size, replace=False)
    url = 'http://mattmahoney.net/dc/'
    # pylint: disable=redefined-outer-name

    # Step 1: Download the data.
    def maybe_download(filename, expected_bytes):
        """Download a file if not present, and make sure it's the right size."""
        local_filename = os.path.join(gettempdir(), filename)
        if not os.path.exists(local_filename):
            local_filename, _ = urllib.request.urlretrieve(url + filename,local_filename)
        print(local_filename+', decay_rate= '+str(decay_rate)+', embedding_size='+str(embedding_size)+', bag_window='+str(bag_window))
        statinfo = os.stat(local_filename)
        if statinfo.st_size == expected_bytes:
            print('Found and verified', filename)
        else:
            print(statinfo.st_size)
            raise Exception('Failed to verify ' + local_filename +
                      '. Can you get to it with a browser?')
        return local_filename


    # Read the data into a list of strings.
    def read_data(filename):
        """Extract the first file enclosed in a zip file as a list of words."""
        with zipfile.ZipFile(filename) as f:
            data = tf.compat.as_str(f.read(f.namelist()[0])).split()
        return data

    # Step 2: Build the dictionary and replace rare words with UNK token.
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

    # Step 3: Function to generate a training batch for the continuous bag of
    # words  model.
    def generate_batch(batch_size, bag_window):
        global data_index
        batch = np.ndarray(shape=(batch_size,2*bag_window), dtype=np.int32)
        labels = np.ndarray(shape=(batch_size, 1), dtype=np.int32)
        span = 2 * bag_window + 1  # [ bag_window target bag_window ]
        buffer = collections.deque(maxlen=span)  # pylint: disable=redefined-builtin
        if data_index + span > len(data):
          data_index = 0
        buffer.extend(data[data_index:data_index + span])
        data_index += span
        for i in range(batch_size):
          context_words = [buffer[w] for w in range(span) if w != bag_window]
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


    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    filename = maybe_download('text8.zip', 31344016)
    vocabulary = read_data(filename)
    print('Data size', len(vocabulary))
    # Filling 4 global variables:
    # data - list of codes (integers from 0 to vocabulary_size-1).
    #   This is the original text but words are replaced by their codes
    # count - map of words(strings) to count of occurrences
    # dictionary - map of words(strings) to their codes(integers)
    # reverse_dictionary - maps codes(integers) to words(strings)
    data, count, unused_dictionary, reverse_dictionary = build_dataset(vocabulary, vocabulary_size)
    del vocabulary  # reduces memory.
    print('Most common words (+UNK)', count[:5])
    print('Sample data', data[:10], [reverse_dictionary[i] for i in data[:10]])
    batch, labels = generate_batch(batch_size=8, bag_window=2)
    for i in range(8):
        print(batch[i], [reverse_dictionary[batch[i][x]] for x in range(4)], '->', labels[i, 0],
          reverse_dictionary[labels[i, 0]])

    # Step 4: Build and train a cbow model.
    graph = tf.Graph()

    with graph.as_default():
        # Input data.
        with tf.name_scope('inputs'):
          train_inputs = tf.placeholder(tf.int32, shape=[batch_size,bag_window*2])
          train_labels = tf.placeholder(tf.int32, shape=[batch_size, 1])
          valid_dataset = tf.constant(valid_examples, dtype=tf.int32)
        # Ops and variables pinned to the CPU because of missing GPU implementation
        with tf.device('/cpu:0'):
            # Look up embeddings for inputs.
            with tf.name_scope('embeddings'):
                embeddings = tf.Variable(tf.random_uniform([vocabulary_size,embedding_size],-1.0,1.0),name='embeddings')
                embed=tf.Variable(tf.zeros([batch_size,embedding_size]))
            for j in range(bag_window*2):
                embed =embed + tf.nn.embedding_lookup(embeddings, train_inputs[:,j])
            embed=embed/(2*bag_window)
        # Construct the variables for the NCE loss
        with tf.name_scope('weights'):
            center_vectors = tf.Variable(tf.truncated_normal([vocabulary_size,embedding_size],stddev=1.0/math.sqrt(embedding_size)),name='weights') # These are the target word vectors.
        with tf.name_scope('biases'):
            nce_biases = tf.Variable(tf.zeros([vocabulary_size]),name='biases')
        # Compute the average NCE loss for the batch.
        # tf.nce_loss automatically draws a new sample of the negative labels each
        # time we evaluate the loss.
        with tf.name_scope('loss'):
            loss =tf.reduce_mean(tf.nn.nce_loss(weights=center_vectors,biases=nce_biases,labels=train_labels,inputs=embed,num_sampled=num_sampled,num_classes=vocabulary_size,partition_strategy='div'))
        # Add the loss value as a scalar to summary.
        tf.summary.scalar('loss', loss)
        with tf.name_scope('learning_rate'):
            strt_learning_rate=1.0
            global_step=tf.Variable(0)
            learning_rate=tf.train.exponential_decay(strt_learning_rate,global_step,20000,decay_rate,staircase=True)
        # Construct the SGD optimizer using a decaying learning rate
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
                # in the list of returned values for session.run())
                # Also, evaluate the merged op to get all summaries from the returned
                # "summary" variable. Feed metadata variable to session for visualizing
                # the graph in TensorBoard.
                _, summary, loss_val = session.run([optimizer, merged, loss],feed_dict=feed_dict,run_metadata=run_metadata)
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
                if step % 100000 == 0 and step>0 :
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
        export_encrypted(log_dir)

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
    word2vec_cbow(flags.log_dir,flags.choice)

if __name__ == '__main__':
  tf.app.run()
