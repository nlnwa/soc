import math
import multiprocessing
import re
from collections import Counter, namedtuple
from concurrent.futures.process import ProcessPoolExecutor

import numpy as np
from bs4 import BeautifulSoup
from scipy.optimize import curve_fit, newton
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
    if 0 == abs_a == abs_b:
        return 1.
    return 2 * abs_i / (abs_a + abs_b)


def cosine(a, b):
    abs_a, abs_b, abs_i = _find_abs(a, b)
    if 0 == abs_a == abs_b:
        return 1.
    return abs_i / (math.sqrt(abs_a * abs_b))


def jaccard(a, b):
    abs_a, abs_b, abs_i = _find_abs(a, b)
    if 0 == abs_a == abs_b:
        return 1.
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


class SimilarityModel:
    def __init__(self, invertible, **cf_args):
        self.invertible = invertible
        self.cf_args = cf_args

    def func(self, x, *params):
        raise NotImplementedError

    def inv_func(self, t, *params):
        if self.invertible:
            raise NotImplementedError

    def der_func(self, x, *params):
        if not self.invertible:
            raise NotImplementedError

    def eval(self, x, *params):
        return self.func(x, *params)

    def inv_eval(self, t, *params):
        if not (0 < t < 1):
            raise ValueError("Invalid target")

        if self.invertible:
            return self.inv_func(t, *params)
        else:
            return newton(lambda x: self.func(x, *params) - t, 0.0001, lambda x: self.der_func(x, *params))

    def fit(self, diff_times, similarities, scores=True):
        params = curve_fit(self.func, diff_times, similarities, **self.cf_args)[0]
        truth, pred = similarities, self.func(diff_times, *params)
        if scores:
            r2 = r2_score(truth, pred)
            mse = mean_squared_error(truth, pred)
            fitness = max(r2 * (1 - 2 * math.sqrt(mse)), 0)
            return self.func, params, fitness
        return self.func, params


class ExpDecayModel(SimilarityModel):
    def __init__(self, **cf_args):
        default = dict(p0=[1, 0], bounds=(0, 1))
        default.update(**cf_args)
        super().__init__(True, **default)

    def func(self, x, *params):
        b, c = params
        return (1 - c) * b ** (np.abs(x)) + c

    def inv_func(self, t, *params):
        b, c = params
        with np.errstate(all="ignore"):
            return np.log((c - t) / (c - 1)) / np.log(b)


class ExpDecayPlusModel(SimilarityModel):
    def __init__(self, n_params=2, **cf_args):
        self.n_params = n_params
        default = dict(p0=[0] * n_params + [1] * n_params, bounds=(0, 1))
        default.update(cf_args)
        super().__init__(False, **default)

    def func(self, x, *params):
        n = self.n_params
        c0 = params[0]
        b0 = params[n]
        tot = b0 ** x
        for i in range(1, n):
            cn, bn = params[n - i], params[n + i]
            tot = (1 - cn) * tot + cn * bn ** x
        return (1 - c0) * tot + c0

    def der_func(self, x, *params):
        n = self.n_params
        c0 = params[0]
        b0 = params[n]
        tot = b0 ** x * np.log(b0)
        for i in range(1, n):
            cn, bn = params[n - i], params[n + i]
            tot = (1 - cn) * tot + cn * bn ** x * np.log(bn)
        return (1 - c0) * tot


class ConstantEqualExpDecayModel(ExpDecayModel):
    def __init__(self, multiplier_when_equal=2):
        self.multiplier_when_equal = multiplier_when_equal
        super().__init__()

    def func(self, x, *params):
        b, c = params
        m = self.multiplier_when_equal
        return -c * (b ** ((m - 1) / m)) ** ((m * x) / (m - x)) + (b ** ((m - 1) / m)) ** ((m * x) / (m - x)) + c
        # raise NotImplementedError
        # Potentially
        # t = -c (b^((m - 1)/m))^((m x)/(m - x)) + (b^((m - 1)/m))^((m x)/(m - x)) + c

    def inv_func(self, t, *params):
        # Mostly the same as multiplying by the inverse exponential, but with
        # an additional parameter for the multiplier upon equality (similarity=1)
        # otherwise it would blow up to infinity
        b, c = params
        m = self.multiplier_when_equal
        adjusted_b = b ** (1 - 1 / m)  # So that sim=target gives a multiplier of 1
        ied = super(ConstantEqualExpDecayModel, self).inv_func(t, adjusted_b, c)
        return 1 / (1 / m + 1 / ied)


class AdjustedExpDecayModel(ExpDecayModel):
    def __init__(self, adj_base=0.25):
        self.adj_base = adj_base
        super().__init__()

    def func(self, x, *params):
        raise NotImplementedError

    def inv_func(self, t, *params):
        b, c = params
        adj_fac = 1 - self.adj_base ** t  # Adj_fac controls how closely it will follow the ied function
        adjusted_b = (adj_fac ** b - 1) / np.log(adj_fac)  # y'(0)=1,y'(∞)=0
        adjusted_t = (adj_fac ** t - 1) / np.log(adj_fac)

        ied = super(AdjustedExpDecayModel, self).inv_func
        return ied(t, adjusted_b, c) / ied(t, adjusted_t, c)


class HtmlResult(namedtuple("HtmlResult", ["word", "tag", "link", "img"])):
    __slots__ = ()

    def similarities(self, r2, method=jaccard):
        return HtmlResult(
            word=method(self.word, r2.word),
            tag=method(self.tag, r2.tag),
            link=method(self.link, r2.link),
            img=method(self.img, r2.img),
        )

    def similarity(self, r2, method=jaccard):
        comb = self.similarities(r2, method)
        return sum(comb) / len(comb)

    def total(self):
        return sum(self, Counter())


def html_to_counters(html):
    soup = BeautifulSoup(html, "html.parser")
    [s.extract() for s in soup(['style', 'script', '[document]', 'head', 'title'])]
    [s.extract() for s in soup.find_all(attrs={"style": re.compile("display: ?none|visibility: ?hidden")})]

    res = HtmlResult(Counter(), Counter(), Counter(), Counter())

    for tag in soup.stripped_strings:
        tag = re.sub("\\s+", " ", tag)
        res.tag[tag] += 1
        for word in re.split("\\W+", tag):
            if word:
                res.word[word] += 1

    for a in soup.find_all("a", attrs={"href": True}):
        href = a.get("href")
        res.link[href] += 1

    for img in soup.find_all("img", attrs={"src": True}):
        src = img.get("src")
        res.img[src] += 1

    return res
