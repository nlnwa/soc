import random
import re


def split_articles(wiki):
    txt = open(f"{wiki}.txt").read()
    print(re.findall(r"((^|\s*\n)\n[^\n]*: ?[^\n])", txt))
    split = re.split(r"(^|\s*\n)\n[^\n]*:\s?\n", txt)
    random.shuffle(split)
    return [s for a in split for s in split_and_clean(a)]


def train_val_test_split(data, test_split=0.2, val_split=0.1):
    cutoff_train = round(len(data) * (1 - test_split - val_split))
    cutoff_test = round(len(data) * test_split)
    train, val, test = data[:cutoff_train], data[cutoff_train:-cutoff_test], data[-cutoff_test:]
    random.shuffle(train)
    random.shuffle(val)
    random.shuffle(test)
    return train, val, test


def split_and_clean(txt, min_len=16, max_len=256):
    txt = re.sub(r"\s+", " ", txt)
    txt = re.sub(r"\.\.\.", ".", txt)
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


for wiki in ["nowiki", "nnwiki"]:
    sentences = split_articles(wiki)
    tvt = train, val, test = train_val_test_split(sentences)
    for d, n in zip(tvt, ["train", "val", "test"]):
        f = open(f"{wiki}-{n}.txt", mode="w")
        for line in d:
            f.write(f"{line}\n")