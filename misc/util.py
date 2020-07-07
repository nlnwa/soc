import math
import multiprocessing
import re
from collections import Counter, namedtuple
from concurrent.futures.process import ProcessPoolExecutor

import numpy as np
from bs4 import BeautifulSoup
from scipy.optimize import curve_fit
from sklearn.metrics import r2_score, mean_squared_error


def _find_abs(a, b):
    if isinstance(a, str) and isinstance(b, str):
        a, b = text_to_counter(a), text_to_counter(b)
    intersect = a & b
    abs_a = sum(a.values()) if isinstance(a, Counter) else len(a)
    abs_b = sum(b.values()) if isinstance(b, Counter) else len(b)
    abs_i = sum(intersect.values()) if isinstance(intersect, Counter) else len(intersect)
    return abs_a, abs_b, abs_i


def similarity_coeffs(a, b):
    abs_a, abs_b, abs_i = _find_abs(a, b)
    dic = 2 * abs_i / (abs_a + abs_b)
    cosine = abs_i / (math.sqrt(abs_a * abs_b))
    jacc = abs_i / (abs_a + abs_b - abs_i)
    return dic, cosine, jacc


def dice(a, b):
    abs_a, abs_b, abs_i = _find_abs(a, b)
    return 2 * abs_i / (abs_a + abs_b)


def cosine(a, b):
    abs_a, abs_b, abs_i = _find_abs(a, b)
    return abs_i / (math.sqrt(abs_a * abs_b))


def jaccard(a, b):
    abs_a, abs_b, abs_i = _find_abs(a, b)
    return abs_i / (abs_a + abs_b - abs_i)


def text_to_counter(text, split="\\W+", multiset=True):
    init = Counter if multiset else set
    return init(re.split(split, str(text).lower()))


def get_counters(texts, split="\\W+", multi=True, tfidf=False):
    counters = [text_to_counter(t, split, multi) for t in texts]
    if tfidf:
        all_terms = sum(counters, Counter())
        term_doc_count = Counter({k: sum(k in c for c in counters) for k in all_terms})

        for i, cn in enumerate(counters):
            counters[i] = Counter({
                k: (1 + math.log2(c)) * (math.log2(len(counters) / (1 + term_doc_count[k])))
                for k, c in cn.items()})
    return counters


def all_diffs(it, method, symmetric=False, equality=0):
    diffs = np.eye(len(it)) * equality
    if symmetric:
        for i, c1 in enumerate(it):
            for j, c2 in enumerate(it[:i]):
                diff = method(c1, c2)
                diffs[i][j] = diff
                diffs[j][i] = diff
    else:
        for i, c1 in enumerate(it):
            for j, c2 in enumerate(it):
                diff = method(c1, c2)
                diffs[i][j] = diff
    return diffs


def exponential_decay(x, b, c):
    return (1 - c) * b ** (np.abs(x)) + c


def inverse_exponential_decay(target, b, c):
    # Solves exponential_decay(x,b,c) = target for x
    with np.errstate(all="ignore"):
        return np.log((c - target) / (c - 1)) / np.log(b)


def find_new_delay(cur_delay, similarity, target, multiplier_when_equal=2, c=0):
    # Mostly the same as multiplying by the inverse exponential, but with c=0
    # and an additional parameter for the multiplier upon equality (similarity=1)
    # otherwise it would blow up to infinity
    adjusted_sim = similarity ** (1 - 1 / multiplier_when_equal)  # So that sim=target gives a multiplier of 1
    ied = inverse_exponential_decay(target, adjusted_sim, c)
    return cur_delay / (1 / multiplier_when_equal + 1 / ied)


def omega_delay(cur_delay, similarity, target, adj_base=0.25, c=0):
    adj_fac = 1 - adj_base ** target  # Adj_fac controls how closely it will follow the ied function
    adjusted_sim = (adj_fac ** similarity - 1) / np.log(adj_fac)  # y'(0)=1,y'(∞)=0
    adjusted_target = (adj_fac ** target - 1) / np.log(adj_fac)

    # y(0)=0,y(t)=1
    mult = inverse_exponential_decay(target, adjusted_sim, c) / inverse_exponential_decay(target, adjusted_target, c)
    return cur_delay * mult


def fit_all_texts(timestamps, texts):
    ts_diffs = all_diffs(timestamps, lambda a, b: (b - a) / 3600)
    tx_sims = all_diffs([text_to_counter(t) for t in texts], jaccard, symmetric=True, equality=1)
    x = ts_diffs.flatten()
    y = tx_sims.flatten()
    params = curve_fit(exponential_decay, x, y,
                       p0=[1, 0], bounds=([0, 0], [1, 1]))[0]
    return params, ts_diffs, tx_sims


def fit_similarity(diff_times, similarities):
    params = curve_fit(exponential_decay, diff_times, similarities,
                       p0=[1, 0], bounds=([0, 0], [1, 1]))[0]
    truth, pred = similarities, exponential_decay(diff_times, *params)
    r2 = r2_score(truth, pred)
    mse = mean_squared_error(truth, pred)
    fitness = max(r2 * (1 - 2 * math.sqrt(mse)), 0)
    return exponential_decay, params, fitness


SimResult = namedtuple("SimResult", ["word", "tag", "link", "img"])


def html_to_counters(html):
    soup = BeautifulSoup(html, "html.parser")
    [s.extract() for s in soup(['style', 'script', '[document]', 'head', 'title'])]
    [s.extract() for s in soup.find_all(attrs={"style": re.compile("display: ?none|visibility: ?hidden")})]

    res = SimResult(Counter(), Counter(), Counter(), Counter())

    for tag in soup.stripped_strings:
        res.tag[tag] += 1
        for word in re.split("\\W+", tag):
            res.word[word] += 1

    for a in soup.find_all("a", attrs={"href": True}):
        href = a.get("href")
        res.link[href] += 1

    for img in soup.find_all("img", attrs={"src": True}):
        src = img.get("src")
        res.img[src] += 1

    return res


def html_sim(html1, html2):
    res1 = html_to_counters(html1)
    res2 = html_to_counters(html2)

    return SimResult(
        word=jaccard(res1.word, res2.word),
        tag=jaccard(res1.tag, res2.tag),
        link=jaccard(res1.link, res2.link),
        img=jaccard(res1.img, res2.img),
    )


if __name__ == '__main__':
    import pandas as pd

    df = pd.read_csv("news2_temp.csv")
    news = df[~df["original_url"].isin({"https://sero.gcloud.api.no:443/", "http://sero.gcloud.api.no/"})]
    df = df[df.text.notna()].sort_values("timestamp").groupby("original_url")
    url = "http://www.vg.no/"
    df = df.get_group(url)
    par, ts, tx = fit_all_texts(df["timestamp"], df["text"])
    # assert abs(exponential_decay(inverse_exponential_decay(0.5, *par), *par) - 0.5) < 1e-10
    y_true = tx.flatten()
    y_pred = exponential_decay(ts.flatten(), *par)
    print(par, r2_score(y_true, y_pred), mean_squared_error(y_true, y_pred))
    import matplotlib.pyplot as plt

    for n in range(0, len(ts), 1):
        plt.plot(ts[n], tx[n], color="g")
    xs = np.arange(ts.min(), ts.max(), 0.01)
    plt.plot(xs, exponential_decay(xs, *par), color="b")
    plt.title(url)
    plt.xlabel("Hours")
    plt.ylabel("Similarity")
    plt.show()
