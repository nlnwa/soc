import json
import os
import re
from typing import Optional

from tensorflow.python.data import Dataset
from tensorflow.python.keras import Input, Model
from tensorflow.python.keras.activations import softmax
from tensorflow.python.keras.backend import _get_available_gpus
from tensorflow.python.keras.layers import Embedding, LSTM, Dense, Dropout, CuDNNLSTM, Bidirectional, LSTM_v2
from tensorflow.python.keras.losses import categorical_crossentropy, sparse_categorical_crossentropy
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


class WiLIModel:
    def __init__(self, char_map: Optional[dict] = None, lang_map: Optional[dict] = None,
                 base_path: Optional[str] = None, **kwargs):
        super(WiLIModel, self).__init__()

        if base_path is None:  # Create
            assert char_map and lang_map
            self.char_map = char_map
            self.lang_map = lang_map

            self.model = self._build(**kwargs)
        else:  # Load
            mp = json.load(open(f"{base_path}.SavedModel/info.json"))
            self.char_map = mp["char"]
            self.lang_map = mp["lang"]
            self.model = self._build(**mp["build"])
            self.model.load_weights(f"{base_path}.SavedModel/weights.h5")

        self.model.compile(adam(3e-4), sparse_categorical_crossentropy)

    def _build(self, bptt: int = 128, embedding_size: int = 64, units=(128, 128, 64),
               i_dropout=0., r_dropout=0., o_dropout=0.):

        self.build_args = {"bptt": bptt, "embedding_size": embedding_size, "units": units, "i_dropout": i_dropout,
                           "r_dropout": r_dropout, "o_dropout": o_dropout}

        if isinstance(units, int):
            units = [units] * 3

        if isinstance(i_dropout, float):
            i_dropout = [i_dropout] * 3

        if isinstance(r_dropout, float):
            r_dropout = [r_dropout] * 3

        inp = Input((bptt,))
        x = Embedding(len(self.char_map) + 2, embedding_size, input_length=bptt)(inp)
        x = LSTM_v2(units[0], dropout=i_dropout[0], recurrent_dropout=r_dropout[0], return_sequences=True)(x)
        x = LSTM_v2(units[1], dropout=i_dropout[1], recurrent_dropout=r_dropout[1], return_sequences=True)(x)
        x = LSTM_v2(units[2], dropout=i_dropout[2], recurrent_dropout=r_dropout[2], return_sequences=False)(x)
        x = Dense(len(self.lang_map), activation=softmax)(x)
        x = Dropout(o_dropout)(x)
        return Model(inputs=inp, outputs=x)

    def save(self, base_path="WiLI-Model"):
        if not os.path.isdir(f"{base_path}.SavedModel"):
            os.mkdir(f"{base_path}.SavedModel")
        json.dump({"char": self.char_map, "lang": self.lang_map, "build": self.build_args},
                  open(f"{base_path}.SavedModel/info.json", "w"))
        self.model.save_weights(f"{base_path}.SavedModel/weights.h5")


m = WiLIModel(char_map={"a": 1}, lang_map={"asd": 0})
m.save()
m = WiLIModel(base_path="WiLI-Model")

print(m.model.layers[0])
print(m.model.summary())

exit(0)


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


def preprocess(text, window_size=256, batch_size=32, epochs=1):
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

    data = data.repeat(epochs)

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

# if __name__ == '__main__':
#     parser = ArgumentParser()
#     parser.add_argument("-f", "--file", dest="files",
#                         help="write report to FILE", metavar="FILE", nargs="+")
#
#     parser.add_argument("-m", "--model", dest="model",
#                         help="path to saved model", metavar="MODEL")
#
#     args = parser.parse_args()
#
#     model = get_model(256, len(alphabet) + 2, 2)
#
#     if args.model:
#         model.load_weights(args.model)
#     else:
#         model.load_weights("LMX7.h5")
#
#     for f in args.files:
#         txt = open(f).read()
#         data, lengths = preprocess(txt)
#         pred = model.predict(data)
#         total = np.zeros((pred.shape[-1]))
#         byte_count = 0
#         for p, l in zip(pred, lengths):
#             # print(p, l)
#             total += p * l
#             byte_count += l
#
#         if byte_count > 0:
#             total /= byte_count
#
#         print(f"NOB: {total[0]}, NNO: {total[1]}")
