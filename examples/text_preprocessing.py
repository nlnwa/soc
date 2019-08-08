import os
import re
from collections import Counter
from itertools import chain

import tensorflow_datasets.public_api as tfds

# Creates text encoder

if not os.path.isfile("nonnwiki-TokenTextEncoderL.tokens"):
    print("Loading wikis...")

    no_wiki = open("../res/wiki/nowiki.txt")
    nn_wiki = open("../res/wiki/nnwiki.txt")

    it = (text for text in chain(no_wiki, nn_wiki) if len(text) > 64)

    it = (w for text in it for w in re.split(r"\W+", text))

    counter = Counter(it).most_common(2 ** 15)

    print("Building encoder...")

    encoder = tfds.features.text.TokenTextEncoder([c[0] for c in counter], lowercase=True)

    print("Saving encoder...")

    encoder.save_to_file("nonnwiki-TokenTextEncoderL")
else:
    encoder = tfds.features.text.TokenTextEncoder.load_from_file("nonnwiki-TokenTextEncoderL")

encoding = encoder.encode("En norsk tekst for å teste.")

for enc in encoding:
    print(enc, "|", encoder.decode([enc]))
