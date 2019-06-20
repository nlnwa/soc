import random
import re

from pycld2 import detect
from sklearn.metrics import confusion_matrix, classification_report

data = {}

for n in ["train", "val", "test"]:
    nowiki = [(line.strip(), "no") for line in open(f"res/wiki/nowiki-{n}.txt")]
    nnwiki = [(line.strip(), "nn") for line in open(f"res/wiki/nnwiki-{n}.txt")]

    m = min(len(nowiki), len(nnwiki))
    sample = random.sample(nowiki, m)
    sample += random.sample(nnwiki, m)

    random.shuffle(sample)

    data[n] = sample

x_train, y_train = zip(*data["train"])
x_val, y_val = zip(*data["val"])
x_test, y_test = zip(*data["test"])


def split_norwegian(text):
    d = detect(text, returnVectors=True, hintLanguage="no")
    if d[0]:
        nor = []
        vec = d[3]
        for v in vec:
            if v[3] not in ["no", "nn"]:
                nor.append(text[v[0]:v[0] + v[1]])
        return nor
    else:
        return None


pred = []
for text in x_test:
    text = re.sub("[]", "", text)
    print(text)
    d = detect(text, returnVectors=True, hintTopLevelDomain="no")
    if d[0]:
        if d[2][0][1] in ["no", "nn"]:
            pred.append(d[2][0][1])
        else:
            pred.append("other")
    else:
        pred.append("un")

print(confusion_matrix(y_test, pred, labels=["no", "nn", "un", "other"]))
print(classification_report(y_test, pred))
