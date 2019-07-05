import random
from collections import Sized, Iterable

import numpy as np
import tensorflow as tf
import tensorflow_datasets.public_api as tfds
from keras_contrib.callbacks import CyclicLR
from tensorflow.python.data import Dataset, TextLineDataset
from tensorflow.python.keras import Input, Model, activations
from tensorflow.python.keras import backend as K
from tensorflow.python.keras.engine import Layer
from tensorflow.python.keras.layers import Embedding, Dropout, TimeDistributed, Dense, CuDNNLSTM, LSTM
from tensorflow.python.keras.losses import sparse_categorical_crossentropy
from tensorflow.python.keras.metrics import sparse_categorical_accuracy
from tensorflow.python.keras.optimizers import adam


class TiedEmbeddingsTransposed(Layer):
    """Layer for tying embeddings in an output layer.
    A regular embedding layer has the shape: V x H (V: size of the vocabulary. H: size of the projected space).
    In this layer, we'll go: H x V.
    With the same weights than the regular embedding.
    In addition, it may have an activation.
    # References
        - [ Using the Output Embedding to Improve Language Models](https://arxiv.org/abs/1608.05859)
    """

    def __init__(self, tied_to=None,
                 activation=None,
                 **kwargs):
        super(TiedEmbeddingsTransposed, self).__init__(**kwargs)
        self.tied_to = tied_to
        self.activation = activations.get(activation)

    def build(self, input_shape):
        self.transposed_weights = K.transpose(self.tied_to.weights[0])
        self.built = True

    def compute_mask(self, inputs, mask=None):
        return mask

    def compute_output_shape(self, input_shape):
        return input_shape[0], K.int_shape(self.tied_to.weights[0])[0]

    def call(self, inputs, mask=None):
        output = K.dot(inputs, self.transposed_weights)
        if self.activation is not None:
            output = self.activation(output)
        return output

    def get_config(self):
        config = {'activation': activations.serialize(self.activation)
                  }
        base_config = super(TiedEmbeddingsTransposed, self).get_config()
        return dict(list(base_config.items()) + list(config.items()))


def build_language_model(num_words, embedding_size=400, rnn_sizes=(1150, 1150),
                         dropout=0.1, dropouti=0.2, use_gpu=True, only_last=False, tie_weights=True):
    inp = Input(shape=(None,), name='input')
    emb = Embedding(num_words, embedding_size, name='embedding')
    emb_inp = emb(inp)
    emb_inp = Dropout(dropouti)(emb_inp)

    RnnUnit = CuDNNLSTM if use_gpu else LSTM
    rnn = RnnUnit(rnn_sizes[0], return_sequences=True, name='0_rnn_layer')(emb_inp)
    for i, rnn_size in enumerate(rnn_sizes[1:]):
        rnn = RnnUnit(rnn_size, return_sequences=True, name='{}_rnn_layer'.format(i + 1))(rnn)
    if only_last:
        rnn = RnnUnit(embedding_size, return_sequences=False, name='final_rnn_layer')(rnn)
    else:
        rnn = RnnUnit(embedding_size, return_sequences=True, name='final_rnn_layer')(rnn)

    if tie_weights:
        softmax_layer = TiedEmbeddingsTransposed(tied_to=emb, activation='softmax')
    else:
        softmax_layer = Dense(num_words, activation='softmax')

    if only_last:
        logits = softmax_layer(rnn)
    else:
        logits = TimeDistributed(softmax_layer)(rnn)

    out = Dropout(dropout)(logits)
    mdl = Model(inputs=inp, outputs=out)
    return mdl


def get_encoder(filename="nonnwiki-TokenTextEncoder"):
    enc = tfds.features.text.TokenTextEncoder.load_from_file(filename)
    return enc


def get_dataset(texts, bptt=64):
    if isinstance(texts, str):
        ds = TextLineDataset(texts)
    elif isinstance(texts, Sized):
        ds = Dataset.from_tensor_slices(texts)
    else:
        assert isinstance(texts, Iterable)
        ds = Dataset.from_generator(lambda: (encoder.encode(s) for s in texts), output_types=(tf.int64,))

    def encode(text_tensor):
        encoded_text = encoder.encode(text_tensor)
        return np.array(encoded_text[0:bptt], dtype=np.int64), np.reshape(
            np.array(encoded_text[1:bptt + 1], dtype=np.int64), (-1, 1))

    def encode_map_fn(text):
        return tf.numpy_function(encode, inp=[text], Tout=(tf.int64, tf.int64))

    ds = ds.filter(lambda x: tf.numpy_function(lambda a: len(a) > 2 * bptt, inp=[x], Tout=tf.bool))

    ds = ds.map(encode_map_fn)

    ds = ds.filter(lambda x, y: tf.numpy_function(lambda a, b: b.shape[-2] == bptt, inp=[x, y], Tout=tf.bool))
    return ds


def preprocess(fpath, bptt=80):
    f = open(fpath).read().split("(^|\n)\n[^\n]+\n")
    xy = []
    for s in f:
        e = encoder.encode(s)
        for i in range(bptt, len(e), bptt):
            xy.append((e[i - bptt:i], e[i - bptt + 1:i + 1]))
    del f
    random.shuffle(xy)
    x, y = zip(*xy)
    del xy
    x = np.array(x)
    y = np.array(y)
    y = y.reshape((-1, bptt, 1))
    return x, y


if __name__ == '__main__':
    encoder = get_encoder()

    x, y = preprocess("res/wiki/nowiki.txt")

    # import keras.backend as K

    # dtype='float16'
    # K.set_floatx(dtype)

    # # default is 1e-7 which is too small for float16.  Without adjusting the epsilon, we will get NaN predictions because of divide by zero problems
    # K.set_epsilon(1e-4)

    model = build_language_model(encoder.vocab_size + (8 - encoder.vocab_size % 8), use_gpu=False, tie_weights=False)
    model.summary()

    model.compile(adam(2e-3 / 25.), sparse_categorical_crossentropy, [sparse_categorical_accuracy])

    lrcb = CyclicLR(max_lr=2e-3, base_lr=2e-3 / 25., step_size=8900 * 8)
    model.fit(x, y, batch_size=128, epochs=128, callbacks=[lrcb])
