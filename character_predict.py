import os
import random

from tensorflow.python.data import Dataset
from tensorflow.python.keras import Input, Model
from tensorflow.python.keras.backend import _get_available_gpus, one_hot
from tensorflow.python.keras.callbacks import ReduceLROnPlateau, EarlyStopping, ModelCheckpoint
from tensorflow.python.keras.layers import Embedding, LSTM, Dropout, CuDNNLSTM, Bidirectional
from tensorflow.python.keras.losses import categorical_crossentropy
from tensorflow.python.keras.metrics import categorical_accuracy
from tensorflow.python.keras.optimizers import adam
from tensorflow.python.keras.preprocessing.sequence import pad_sequences
from tensorflow.python.keras.preprocessing.text import Tokenizer

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

LATIN_ALPHABET = "abcdefghijklmnopqrstuvwxyz"
NORWEGIAN_ALPHABET = LATIN_ALPHABET + "æøå"
NUMBERS = "0123456789"

alphabet = " " + NORWEGIAN_ALPHABET.upper() + NORWEGIAN_ALPHABET.lower() + NUMBERS

tokenizer = Tokenizer(len(alphabet) + 2, char_level=True, lower=False, oov_token="\u0000")
tokenizer.fit_on_texts(alphabet)


# def split_and_clean(txt, min_len=8, max_len=256):
#     txt = re.sub(r"\s+", " ", txt)
#     txt = re.sub(r"\.+", ".", txt)
#     split = re.split(r"[.?!\t\r\n\f]+(?! ?[a-zæøå])", txt)
#     for s in split:
#         s = s.strip()
#         if len(s) > min_len:
#             if len(s) > max_len:
#                 for c in re.split("[,:]", s):
#                     if len(c) > min_len:
#                         if len(c) > max_len:
#                             n = len(c) // (len(c) // max_len + 1)
#                             if n > min_len:
#                                 a = 0
#                                 for i in range(0, len(c), n):
#                                     yield c[i:i + n]
#                                     a = i + n
#                                 if len(c) - a > min_len:
#                                     yield c[a:]
#                         else:
#                             yield c
#             else:
#                 yield s

def preprocess(text, window_size=256, batch_size=32):
    """
    Converts text and labels to numerical values that can be used in the model.

    :param text: a list of strings.
    :param batch_size: number of texts to batch together.
    :param epochs: how many times to repeat the data.
    :return: a TensorFlow dataset containing the data.
    """
    sentences = text

    x = tokenizer.texts_to_sequences(sentences)
    x = pad_sequences(x, window_size + 1)
    # x = (pad_sequences([s], window_size) for s in x)

    # data = Dataset.from_generator(lambda: x, output_types=(np.int32,))

    data = Dataset.from_tensor_slices(x)

    def pre(a):
        # print(a[1:])
        # print(one_hot(a[1:], len(alphabet) + 2))
        return a[:-1], one_hot(a[1:], len(alphabet) + 2)

    data = data.map(pre)

    data = data.batch(batch_size)

    data = data.prefetch(window_size)

    return data, [len(s) for s in sentences]


def lstm_block(input, units, gpu, sequences=True, bi=False, drop=0.25, activation=None):
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


def get_model(window_size, alphabet_size, lr=3e-4, gpu=None):
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
    x = lstm_block(x, 16, gpu)
    #     x = lstm_block(x, 16, gpu)
    x = lstm_block(x, alphabet_size, gpu)
    x = (x + 1) / 2

    mdl = Model(inputs=inp, outputs=x)

    if lr is not None:
        mdl.compile(adam(lr), categorical_crossentropy, [categorical_accuracy])

    return mdl


langs = ["nob", "nno"]

base_path = "res/wiki/%s"

data = {}

for n in ["train", "val", "test"]:
    nowiki = [(line.strip(), "nob") for line in open(base_path % f"nowiki-{n}.txt")]
    nnwiki = [(line.strip(), "nno") for line in open(base_path % f"nnwiki-{n}.txt")]

    m = min(len(nowiki), len(nnwiki))
    sample = random.sample(nowiki, m)
    sample += random.sample(nnwiki, m)

    random.shuffle(sample)

    data[n] = sample

x_train, y_train = zip(*data["train"])
x_val, y_val = zip(*data["val"])
x_test, y_test = zip(*data["test"])

print(len(x_train), len(y_train), len(x_val), len(y_val), len(x_test), len(y_test))

model = get_model(256, len(alphabet) + 2, )

model.summary()

lrcb = ReduceLROnPlateau(patience=4)
escb = EarlyStopping(patience=8, restore_best_weights=True)
mccb = ModelCheckpoint("LMX8.h5", save_best_only=True, save_weights_only=True)

train_data, _ = preprocess(x_train)
val_data, _ = preprocess(x_val)
model.fit(train_data, validation_data=val_data, steps_per_epoch=len(x_train) // 32 + 1, epochs=128, verbose=1,
          callbacks=[lrcb, escb, mccb])
