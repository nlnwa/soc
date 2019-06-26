import os
from itertools import chain

import tensorflow_datasets.public_api as tfds

if not os.path.isfile("nonnwiki-SubwordTextEncoder.subwords"):
    print("Loading wikis...")

    no_wiki = open("res/wiki/nowiki.txt")
    nn_wiki = open("res/wiki/nnwiki.txt")

    it = (text for text in chain(no_wiki, nn_wiki) if len(text) > 64)

    print("Building encoder...")

    encoder = tfds.features.text.SubwordTextEncoder.build_from_corpus(it, 2 ** 15)

    print("Saving encoder...")

    encoder.save_to_file("nonnwiki-SubwordTextEncoder")
else:
    encoder = tfds.features.text.SubwordTextEncoder.load_from_file("nowiki-SubwordTextEncoder")


encoding = encoder.encode("t _ sne")

for enc in encoding:
    print(enc, "|", encoder.decode([enc]))
