import re
from collections import Counter

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from misc.util import jaccard, text_to_counter, html_to_counters


def add_columns(df, compare_with_start=False, master=None):
    if master is None:
        master = Counter()
    tmp = df.iloc[0:0]
    if compare_with_start:
        for uri, subdf in df.groupby("uri"):
            word_counters = [text_to_counter(txt) - master for txt in subdf.text]
            tag_counters = [text_to_counter(txt, "\t") for txt in subdf.text]
            link_counters = [text_to_counter(lnk, "\t") for lnk in subdf.links]
            subdf = subdf.copy()
            subdf["text_sim"] = [
                jaccard(word_counters[0], word_counters[i])
                for i in range(len(subdf))]
            subdf["tag_sim"] = [
                jaccard(tag_counters[0], tag_counters[i])
                for i in range(len(subdf))]
            subdf["link_sim"] = [
                jaccard(link_counters[0], link_counters[i])
                for i in range(len(subdf))]
            tmp = pd.concat((tmp, subdf))
    else:
        for uri, subdf in df.groupby("uri"):
            word_counters = [text_to_counter(txt) - master for txt in subdf.text]
            tag_counters = [text_to_counter(txt, "\t") for txt in subdf.text]
            link_counters = [text_to_counter(lnk, "\t") for lnk in subdf.links]
            subdf = subdf.copy()
            subdf["text_sim"] = [np.nan] + [
                jaccard(word_counters[i], word_counters[i + 1])
                for i in range(len(subdf) - 1)]
            subdf["tag_sim"] = [np.nan] + [
                jaccard(tag_counters[i], tag_counters[i + 1])
                for i in range(len(subdf) - 1)]
            subdf["link_sim"] = [np.nan] + [
                jaccard(link_counters[i], link_counters[i + 1])
                for i in range(len(subdf) - 1)]
            tmp = pd.concat((tmp, subdf))
    return tmp


def plot_sim(url, df, sim="text_sim"):
    getter = df.groupby("uri").get_group(url)
    fig, ax = plt.subplots()
    ax.plot((getter["timestamp"] - getter["timestamp"].iloc[0]) / 3600, getter[sim])
    ax.set_title(url)
    ax.set_ylabel("Similarity")
    ax.set_xlabel("Hours")
    return fig


def plot_ts_diff(url, df):
    getter = df.groupby("uri").get_group(url)
    fig, ax = plt.subplots()
    ax.plot((getter["timestamp"] - getter["timestamp"].iloc[0]) / 3600, (getter["timestamp"].diff() / 60))
    ax.set_title(url)
    ax.set_ylabel("Delay (minutes)")
    ax.set_xlabel("Hours")
    return fig


def plot_similarities(url, df):
    getter = df.groupby("uri").get_group(url)
    fig, ax = plt.subplots()
    sims = ["text_sim", "tag_sim", "link_sim"]
    for sim in sims:
        ax.plot((getter["timestamp"] - getter["timestamp"].iloc[0]) / 3600, getter[sim], label=sim)
    # ax.plot((getter["timestamp"] - getter["timestamp"].iloc[0]) / 3600,
    #         [sum(getter[s].iloc[i] for s in sims) / 3 for i in range(len(getter["text_sim"]))], label="average")
    ax.set_title(url)
    ax.legend()
    ax.set_ylabel("Similarity")
    ax.set_xlabel("Hours")
    return fig


def main():
    df = pd.read_csv("adaptive4.csv")
    df = df[df.uri != "https://www.dagbladet.no/"]
    df = df.sort_values("timestamp")
    # g = df.groupby('uri')
    # g = g.apply(lambda x: x.sample(8).reset_index(drop=True) if len(x) >= 8 else None)
    # master = sum((text_to_counter(t) for t in g.text), start=Counter())
    # master = Counter(dict(master.most_common(25)))
    df = add_columns(df)
    for url in ["https://www.vg.no/", "https://www.nrk.no/nyheter/", "https://www.ranablad.no/"]:
        plot_sim(url, df).show()
        plot_ts_diff(url, df).show()
    plot_similarities("https://www.vg.no/", add_columns(df, True)).show()
    print(df.corr().iloc[-3::, -3::])


if __name__ == '__main__':
    main()
