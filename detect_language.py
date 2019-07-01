import os
import re
from argparse import ArgumentParser

import numpy as np
from tensorflow.python.data import Dataset
from tensorflow.python.keras import Input, Model
from tensorflow.python.keras.activations import softmax
from tensorflow.python.keras.backend import _get_available_gpus
from tensorflow.python.keras.layers import Embedding, LSTM, Dense, Dropout, CuDNNLSTM, Bidirectional
from tensorflow.python.keras.losses import categorical_crossentropy
from tensorflow.python.keras.metrics import categorical_accuracy
from tensorflow.python.keras.optimizers import adam
from tensorflow.python.keras.preprocessing.sequence import pad_sequences
from tensorflow.python.keras.preprocessing.text import Tokenizer

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '4'

LATIN_ALPHABET = "abcdefghijklmnopqrstuvwxyz"
NORWEGIAN_ALPHABET = LATIN_ALPHABET + "æøå"
NUMBERS = "0123456789"

alphabet = " " + NORWEGIAN_ALPHABET.upper() + NORWEGIAN_ALPHABET.lower() + NUMBERS

tokenizer = Tokenizer(len(alphabet) + 2, char_level=True, lower=False, oov_token="\u0000")
tokenizer.fit_on_texts(alphabet)


def split_and_clean(txt, min_len=8, max_len=256):
    txt = re.sub(r"\s+", " ", txt)
    txt = re.sub(r"\.+", ".", txt)
    split = re.split(r"[.?!\t\r\n\f]+(?! ?[a-zæøå])", txt)
    for s in split:
        s = s.strip()
        if len(s) > min_len:
            if len(s) > max_len:
                for c in re.split("[,:]", s):
                    if len(c) > min_len:
                        if len(c) > max_len:
                            n = len(c) // (len(c) // max_len + 1)
                            if n > min_len:
                                a = 0
                                for i in range(0, len(c), n):
                                    yield c[i:i + n]
                                    a = i + n
                                if len(c) - a > min_len:
                                    yield c[a:]
                        else:
                            yield c
            else:
                yield s


def preprocess(text, window_size=256, batch_size=32):
    """
    Converts text and labels to numerical values that can be used in the model.

    :param text: a list of strings.
    :param batch_size: number of texts to batch together.
    :param epochs: how many times to repeat the data.
    :return: a TensorFlow dataset containing the data.
    """
    sentences = list(split_and_clean(text))
    del text

    x = tokenizer.texts_to_sequences(sentences)
    x = pad_sequences(x, window_size)
    # x = (pad_sequences([s], window_size) for s in x)

    # data = Dataset.from_generator(lambda: x, output_types=(np.int32,))

    data = Dataset.from_tensor_slices(x)

    data = data.batch(batch_size)

    data = data.prefetch(window_size)

    return data, [len(s) for s in sentences]


def lstm_block(input, units, gpu, sequences=True, bi=False, drop=0.25):
    # Simple block with (optionally bidirectional) LSTM and Dropout
    x = input
    if gpu:
        mem = CuDNNLSTM(units, return_sequences=sequences)
    else:
        mem = LSTM(units, return_sequences=sequences)
    if bi:
        mem = Bidirectional(mem)
    x = mem(x)

    if drop is not None:
        x = Dropout(drop)(x)

    return x


def get_model(window_size, alphabet_size, output_size, lr=None, gpu=None):
    """
    Creates a model that can be used after pre-processing data

    :param window_size: the length of the input sequences.
    :param alphabet_size: the size of the alphabet (number of different characters)
    :param output_size: number of classes in the output.
    :param lr: learning rate for the model. If lr is None the compilation step is skipped.
    :param gpu: boolean indicating whether or not to use GPU.
    :return: the model.
    """
    if gpu is None:
        gpu = len(_get_available_gpus()) > 0

    inp = Input((window_size,))
    x = Embedding(alphabet_size, 16, mask_zero=(not gpu))(inp)
    #     x = lstm_block(x, 64, gpu)
    #     x = lstm_block(x, 64, gpu)
    x = lstm_block(x, 16, gpu, False)
    x = Dense(output_size, softmax)(x)
    mdl = Model(inputs=inp, outputs=x)

    if lr is not None:
        mdl.compile(adam(lr), categorical_crossentropy, [categorical_accuracy])

    return mdl


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("-f", "--file", dest="files",
                        help="write report to FILE", metavar="FILE", nargs="+")

    parser.add_argument("-m", "--model", dest="model",
                        help="path to saved model", metavar="MODEL")

    args = parser.parse_args()

    model = get_model(256, len(alphabet) + 2, 2)

    if args.model:
        model.load_weights(args.model)
    else:
        model.load_weights("LMX7.h5")

    for f in args.files:
        txt = open(f).read()
        data, lengths = preprocess(txt)
        pred = model.predict(data)
        total = np.zeros((pred.shape[-1]))
        byte_count = 0
        for p, l in zip(pred, lengths):
            # print(p, l)
            total += p * l
            byte_count += l

        if byte_count > 0:
            total /= byte_count

        print(f"NOB: {total[0]}, NNO: {total[1]}")
