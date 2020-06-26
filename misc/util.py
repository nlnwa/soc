import math
import re
from collections import Counter

import numpy as np
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


def text_to_counter(text, split="\\W+"):
    return Counter(re.split(split, text.lower()))


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
    return math.log((c - target) / (c - 1)) / math.log(b)


def find_new_delay(delay, similarity, target, multiplier_when_equal=2, c=0):
    # Mostly the same as multiplying by the inverse exponential, but with c=0
    # and an additional parameter for the multiplier upon equality (similarity=1)
    # otherwise it would blow up to infinity
    if similarity <= 0:
        return 0
    elif similarity >= 1:
        return multiplier_when_equal
    adjusted_sim = similarity ** (1 - 1 / multiplier_when_equal)  # So that sim=target gives a multiplier of 1
    ied = inverse_exponential_decay(target, adjusted_sim, c)
    return delay / (1 / multiplier_when_equal + 1 / ied)


def fit_similarity(timestamps, texts):
    ts_diffs = all_diffs(timestamps, lambda a, b: (b - a) / 3600)
    tx_sims = all_diffs([text_to_counter(t) for t in texts], jaccard, symmetric=True, equality=1)
    x = ts_diffs.flatten()
    y = tx_sims.flatten()
    params = curve_fit(exponential_decay, x, y,
                       p0=[1, 0], bounds=([0, 0], [1, 1]))[0]
    return params, ts_diffs, tx_sims


if __name__ == '__main__':
    import pandas as pd

    df = pd.read_csv("news2_temp.csv")
    news = df[~df["original_url"].isin({"https://sero.gcloud.api.no:443/", "http://sero.gcloud.api.no/"})]
    df = df[df.text.notna()].sort_values("timestamp").groupby("original_url")
    url = "http://www.vg.no/"
    df = df.get_group(url)
    par, ts, tx = fit_similarity(df["timestamp"], df["text"])
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
