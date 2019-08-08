# Examples
Folder containing various examples that may be of use later, but are not currently relevant to the main program (server.py).

## Files

- `iterate_urls.py`: Iterates through OOS-list and generates a csv file with webpage information.
- `oos-doc2vec.ipynb`: Example generating Doc2Vec vectors from websites using the OOS list generated in `iterate_urls.py`.
- `tatoeba.ipynb`: Generates training, validation, and test datasets for use in `Tatoeba-Model.ipynb` in the Google Drive folder.
- `test_cld.ipynb`: Test program for cld2 on WiLI dataset.
- `text_preprocessing.py`: Example of text preprocessing and encoding in TensorFlow.

In addition, the [Google Drive folder](https://drive.google.com/drive/folders/1Om7PGu_auqUMncnj1tIikawcy_9tnytj) contains various example files, which use Google Colab for increased performance through GPUs:
- `LanguageModel.ipynb`: Language identification model with character LSTM which attempts to differentiate between Norwegian Bokmål and Norwegian Nynorsk from Wikipedia articles.
- `SubwordModel.ipynb`: Language model (AWD-LSTM) that uses subwords.
- `Tatoeba-Model.ipynb`: Language identification model with character LSTM that trains and tests on the [Tatoeba dataset](https://tatoeba.org/eng/downloads).
- `TextClassifier.ipynb`: Mockup of fast.ai language model for use in classification using a [pre-trained model](https://github.com/AugustIndal/Norwegian-no-nn-ULMFiT-language-model).
- `WILI-Model.ipynb`: Language identification model with character LSTM that trains and tests on the [WiLI dataset](https://arxiv.org/abs/1801.07779).
