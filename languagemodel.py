import re

import numpy as np
from sklearn.metrics import confusion_matrix, classification_report
from tensorflow.python.data import Dataset
from tensorflow.python.keras import Input, Model
from tensorflow.python.keras.activations import softmax
from tensorflow.python.keras.callbacks import ReduceLROnPlateau, EarlyStopping
from tensorflow.python.keras.layers import Embedding, LSTM, Dense, Dropout
from tensorflow.python.keras.losses import categorical_crossentropy
from tensorflow.python.keras.metrics import categorical_accuracy
from tensorflow.python.keras.models import load_model
from tensorflow.python.keras.optimizers import adam
from tensorflow.python.keras.preprocessing.sequence import pad_sequences
from tensorflow.python.keras.preprocessing.text import Tokenizer
from tensorflow.python.keras.utils import to_categorical

# import tensorflow.python.keras.backend as K
#
LATIN_ALPHABET = " abcdefghijklmnopqrstuvwxyz0123456789"
NORWEGIAN_ALPHABET = LATIN_ALPHABET + "æøå"
#
# weights = np.ones((3, 3))
# weights[0, 2] = 128
# weights[1, 2] = 128
#
# weights[2, 0] = 16
# weights[2, 1] = 16
#
#
# # https://github.com/keras-team/keras/issues/2115
# def w_categorical_crossentropy(y_true, y_pred):
#     nb_cl = len(weights)
#     final_mask = K.zeros_like(y_pred[:, 0])
#     y_pred_max = K.max(y_pred, axis=1)
#     y_pred_max = K.reshape(y_pred_max, (K.shape(y_pred)[0], 1))
#     y_pred_max_mat = K.equal(y_pred, y_pred_max)
#     for c_p, c_t in product(range(nb_cl), range(nb_cl)):
#         final_mask += (weights[c_t, c_p] * y_pred_max_mat[:, c_p] * y_true[:, c_t])
#     return K.categorical_crossentropy(y_pred, y_true) * final_mask


def get_model(window_size, alphabet_size, output_size, lr=1e-3):
    """
    Creates a model that can be used after pre-processing data

    :param window_size: the length of the input sequences.
    :param alphabet_size: the size of the alphabet (number of different characters)
    :param output_size: number of classes in the output.
    :param lr: learning rate for the model. If lr is None the compilation step is skipped.
    :return: the model.
    """
    inp = Input((window_size,))
    x = Embedding(alphabet_size, 16, mask_zero=True)(inp)
    x = LSTM(128)(x)
    x = Dense(128)(x)
    x = Dropout(0.25)(x)
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

        if weights is None:
            self.model = get_model(window_size, len(alphabet) + 2, len(languages), lr)
        else:
            self.model = load_model(weights)
            assert self.model.input_shape == (None, window_size)
            assert self.model.output_shape == (None, len(languages))

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

    def train(self, texts, labels, batch_size=128, epochs=1, verbose=0, callbacks=None, val_split=None,
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
            val = self._convert_data(val[0], val[1], batch_size, epochs, True)

        self.model.fit(train,
                       steps_per_epoch=val_split // batch_size + 1,
                       epochs=epochs,
                       verbose=verbose,
                       callbacks=callbacks,
                       validation_data=val,
                       class_weight=class_weight, )

    def test(self, texts, labels, batch_size=128, verbose=0, callbacks=None):
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

    def predict(self, texts, raw=False, batch_size=128, verbose=0, callbacks=None):
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
        preds = [self.languages[p] for p in np.argmax(pre, axis=-1)]
        return preds

    def save(self, path=None):
        """
        Saves the model to file.

        :param path: the path to use.
        """
        if path is None:
            path = f"LanguageModel-{len(self.languages)}-{self.tokenizer.num_words}.hdf5"
        self.model.save(path)


if __name__ == '__main__':
    x_train, y_train = [], []
    x_val, y_val = [], []
    langs = ["nob", "nno", "other"]

    for x, y in zip(open("res/wili-2018/x_train.txt"), open("res/wili-2018/y_train.txt")):
        y = y.replace("\n", "")
        for s in re.split("[.?!]", x):
            x_train.append(s)
            if y in langs:
                y_train.append(y)
            else:
                y_train.append("other")

    for x, y in zip(open("res/wili-2018/x_test.txt"), open("res/wili-2018/y_test.txt")):
        y = y.replace("\n", "")
        for s in re.split("[.?!]", x):
            x_val.append(s)
            if y in langs:
                y_val.append(y)
            else:
                y_val.append("other")

    model = LanguageModel(languages=langs)

    lrcb = ReduceLROnPlateau(patience=2)
    escb = EarlyStopping(patience=5, restore_best_weights=True)

    model.train(x_train + x_val, y_train + y_val, val_split=len(x_train), batch_size=128, epochs=32, verbose=1,
                callbacks=[lrcb, escb], class_weight={0: 16, 1: 16, 2: 1})

    pre = model.predict(x_val)

    for s, p, a in zip(x_val, pre, y_val):
        if p != a:
            print(p, a, s)

    print(confusion_matrix(y_val, pre, langs))
    print(classification_report(y_val, pre, langs))
    model.save()
