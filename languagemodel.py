import random

import matplotlib.pyplot as plt
import numpy as np
from tensorflow.python.data import Dataset
from tensorflow.python.keras import Input, Model
from tensorflow.python.keras.activations import softmax
from tensorflow.python.keras.backend import _get_available_gpus
from tensorflow.python.keras.callbacks import ReduceLROnPlateau, EarlyStopping, ModelCheckpoint, LearningRateScheduler, \
    Callback
from tensorflow.python.keras.layers import Embedding, LSTM, Dense, Dropout, CuDNNLSTM, Bidirectional
from tensorflow.python.keras.losses import categorical_crossentropy
from tensorflow.python.keras.metrics import categorical_accuracy
from tensorflow.python.keras.optimizers import adam
from tensorflow.python.keras.preprocessing.sequence import pad_sequences
from tensorflow.python.keras.preprocessing.text import Tokenizer
from tensorflow.python.keras.utils import to_categorical

# import tensorflow.python.keras.backend as K
#
from split_wiki import split_and_clean

LATIN_ALPHABET = " abcdefghijklmnopqrstuvwxyz0123456789"
NORWEGIAN_ALPHABET = LATIN_ALPHABET + "æøå"


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


def get_model(window_size, alphabet_size, output_size, lr=1e-3, gpu=None):
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
    x = lstm_block(x, 64, gpu)
    x = lstm_block(x, 64, gpu)
    x = lstm_block(x, 16, gpu, False)(x)
    x = Dense(output_size, softmax)(x)
    model = Model(inputs=inp, outputs=x)
    if lr is not None:
        model.compile(adam(lr), categorical_crossentropy, [categorical_accuracy])
    return model


class LanguageModel:
    """
    Wrapper class for Keras model which automatically processes text input and generates language predictions.
    Includes methods for training, testing, prediction and saving.
    """
    tokenizer: Tokenizer
    languages: list
    model: Model

    def __init__(self, languages, alphabet=NORWEGIAN_ALPHABET, window_size=128, lr=1e-3, weights=None):
        """
        Creates a language model.

        :param languages: the languages to differentiate between.
        :param alphabet: the alphabet to use. Uses Norwegian alphabet by default.
        :param window_size: the number of characters to input at a time.
                            Default is 128, which is about the size of a long sentence.
        :param lr: the learning rate to use.
        :param weights: optional path to model file.
        """
        self.tokenizer = Tokenizer(len(alphabet) + 2, char_level=True, oov_token="\u0000")
        self.tokenizer.fit_on_texts(alphabet)
        self.languages = languages

        print(pad_sequences(self.tokenizer.texts_to_sequences([alphabet + "èé"]), 64))

        self.model = get_model(window_size, len(alphabet) + 2, len(languages), lr)
        if weights is not None:
            self.model.load_weights(weights)

    def _convert_data(self, texts, labels, batch_size=1, epochs=1, shuffle=False):
        """
        Converts text and labels to numerical values that can be used in the model.

        :param texts: a list of strings.
        :param labels: list of language labels for strings.
        :param batch_size: number of texts to batch together.
        :param epochs: how many times to repeat the data.
        :return: a TensorFlow dataset containing the data.
        """
        if labels is not None:
            assert len(texts) == len(labels)
        langmap = {s: i for i, s in enumerate(self.languages)}
        x = self.tokenizer.texts_to_sequences(texts)
        x = pad_sequences(x, 128)
        if labels is not None:
            y = to_categorical([langmap[l] for l in labels], len(self.languages))
            data = Dataset.from_tensor_slices((x, y))
        else:
            data = Dataset.from_tensor_slices(x)

        if shuffle:
            data = data.shuffle(epochs * batch_size)

        data = data.batch(batch_size)
        data = data.repeat(epochs)

        return data

    def train(self, texts, labels, batch_size=32, epochs=1, verbose=0, callbacks=None, val_split=None,
              class_weight=None):
        """
        Trains the model.

        :param texts: a list of strings.
        :param labels: list of language labels for strings.
        :param batch_size: number of texts to batch together.
        :param epochs: how many times to repeat the data.
        :param verbose: whether or not to print update info. 0 or 1.
        :param callbacks: Keras callbacks to use.
        :param val_split: int or float indicating how to split the data into training and validation.
        :param class_weight: a dict indicating how to weight different classes.
        """
        if val_split is not None:
            if isinstance(val_split, float):
                val_split = round(len(texts) * val_split)
            x_train, y_train = texts[:val_split], labels[:val_split]
            val = texts[val_split:], labels[val_split:]
        else:
            val_split = len(texts)  # For steps per epoch
            x_train, y_train = texts, labels
            val = None

        train = self._convert_data(x_train, y_train, batch_size, epochs, True)
        if val is not None:
            val = self._convert_data(val[0], val[1], batch_size, 1, True)

        self.model.fit(train,
                       steps_per_epoch=val_split // batch_size + 1,
                       epochs=epochs,
                       verbose=verbose,
                       callbacks=callbacks,
                       validation_data=val,
                       class_weight=class_weight)

    def test(self, texts, labels, batch_size=32, verbose=0, callbacks=None):
        """
        Tests the model on a dataset.

        :param texts: a list of strings.
        :param labels: list of language labels for strings.
        :param batch_size: number of texts to batch together.
        :param verbose: whether or not to print update info. 0 or 1.
        :param callbacks: Keras callbacks to use.
        :return: a tuple containing (loss, accuracy)
        """
        data = self._convert_data(texts, labels, batch_size, shuffle=True)
        return self.model.evaluate(data, verbose=verbose, callbacks=callbacks)

    def predict(self, texts, raw=False, batch_size=32, verbose=0, callbacks=None):
        """
        Predicts languages of texts.

        :param texts: a list of strings.
        :param raw: whether or not to return output as raw list of percentages (True) or just the guessed class (False).
        :param batch_size: number of texts to batch together.
        :param verbose: whether or not to print update info. 0 or 1.
        :param callbacks: Keras callbacks to use.
        :return: the language predictions for the texts.
        """
        data = self._convert_data(texts, None, batch_size)
        pre = self.model.predict(data, verbose=verbose, callbacks=callbacks)
        if raw:
            return pre
        if len(pre) == 0:
            return []
        preds = [self.languages[p] for p in np.argmax(pre, axis=-1)]
        return preds

    def save(self, path=None):
        """
        Saves the model to file.

        :param path: the path to use.
        """
        if path is None:
            path = f"LanguageModel-{len(self.languages)}-{self.tokenizer.num_words}.hdf5"
        self.model.save_weights(path)

    def lr_plot(self, texts, labels, batch=32):
        model = get_model(self.model.input_shape[-1], self.tokenizer.num_words, len(self.languages), lr=1e-5)
        model.save_weights("tmp.h5")

        lrcb = LearningRateScheduler(lambda x, y: y * 1.5)
        escb = EarlyStopping("loss", patience=3)

        class Reset(Callback):
            def on_epoch_begin(self, epoch, logs=None):
                self.model.load_weights("tmp.h5")

        data = self._convert_data(texts, labels, batch_size=batch, epochs=24, shuffle=True)
        history = model.fit(data, steps_per_epoch=len(texts) // batch + 1, epochs=24, callbacks=[lrcb, Reset(), escb])
        loss = history.history["loss"]
        lr = history.history["lr"]
        # plt.plot(lr, loss)
        plt.loglog(lr, loss)
        plt.legend(["Loss"])
        plt.show()


if __name__ == '__main__':
    langs = ["nob", "nno"]

    nowiki = open("nowiki.txt").read()
    nnwiki = open("nnwiki.txt").read()

    no_split = nowiki.split("\n\n")
    nn_split = nnwiki.split("\n\n")

    no = [(s, "nob") for t in no_split for s in split_and_clean(t)]
    nn = [(s, "nno") for t in nn_split for s in split_and_clean(t)]

    print(len(no), len(nn))

    train = random.sample(no, 1000000)
    train += random.sample(nn, 1000000)

    random.shuffle(train)

    x_train, y_train = zip(*train)

    model = LanguageModel(languages=langs, lr=3e-4)

    lrcb = ReduceLROnPlateau(patience=4)
    escb = EarlyStopping(patience=8, restore_best_weights=True)
    mccb = ModelCheckpoint("LMX.h5", save_best_only=True, save_weights_only=True)

    print(train[:100])
    print(x_train[:100])
    print(y_train[:100])

    model.train(x_train, y_train, val_split=0.8, batch_size=32, epochs=128, verbose=1,
                callbacks=[lrcb, escb, mccb])

    # pre = model.predict(x_val)
    #
    # for s, p, a in zip(x_val, pre, y_val):
    #     if p != a:
    #         print(p, a, s)
    #
    # print(confusion_matrix(y_val, pre, langs))
    # print(classification_report(y_val, pre, langs))
    # model.save()
