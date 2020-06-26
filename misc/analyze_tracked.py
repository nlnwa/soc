import re
from collections import Counter

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from misc.util import jaccard, text_to_counter


def add_columns(df, compare_with_start=False):
    tmp = df.iloc[0:0]
    if compare_with_start:
        for uri, subdf in df.groupby("original_url"):
            subdf = subdf.copy()
            subdf["text_sim"] = [
                jaccard(text_to_counter(subdf.iloc[0].text), text_to_counter(subdf.iloc[i].text))
                for i in range(len(subdf))]
            subdf["tag_sim"] = [
                jaccard(text_to_counter(subdf.iloc[0].text, "\t"), text_to_counter(subdf.iloc[i].text, "\t"))
                for i in range(len(subdf))]
            subdf["link_sim"] = [
                jaccard(text_to_counter(subdf.iloc[0].links, "\t"), text_to_counter(subdf.iloc[i].links, "\t"))
                for i in range(len(subdf))]
            tmp = pd.concat((tmp, subdf))
    else:
        for uri, subdf in df.groupby("original_url"):
            subdf = subdf.copy()
            subdf["text_sim"] = [np.nan] + [
                jaccard(text_to_counter(subdf.iloc[i].text), text_to_counter(subdf.iloc[i + 1].text))
                for i in range(len(subdf) - 1)]
            subdf["tag_sim"] = [np.nan] + [
                jaccard(text_to_counter(subdf.iloc[i].text, "\t"), text_to_counter(subdf.iloc[i + 1].text, "\t"))
                for i in range(len(subdf) - 1)]
            subdf["link_sim"] = [np.nan] + [
                jaccard(text_to_counter(subdf.iloc[i].links, "\t"), text_to_counter(subdf.iloc[i + 1].links, "\t"))
                for i in range(len(subdf) - 1)]
            tmp = pd.concat((tmp, subdf))
    return tmp


def plot_sim(url, df, sim="text_sim"):
    getter = df.groupby("original_url").get_group(url)
    fig, ax = plt.subplots()
    ax.plot((getter["timestamp"] - getter["timestamp"].iloc[0]) / 3600, getter[sim])
    ax.set_title(url)
    ax.set_ylabel("Similarity")
    ax.set_xlabel("Hours")
    return fig


def plot_ts_diff(url, df):
    getter = df.groupby("original_url").get_group(url)
    fig, ax = plt.subplots()
    ax.plot((getter["timestamp"] - getter["timestamp"].iloc[0]) / 3600, (getter["timestamp"].diff() / 60))
    ax.set_title(url)
    ax.set_ylabel("Delay (minutes)")
    ax.set_xlabel("Hours")
    return fig


def plot_similarities(url, df):
    getter = df.groupby("original_url").get_group(url)
    fig, ax = plt.subplots()
    for sim in ["text_sim", "tag_sim", "link_sim"]:
        ax.plot((getter["timestamp"] - getter["timestamp"].iloc[0]) / 3600, getter[sim])
    ax.set_title(url)
    ax.set_ylabel("Similarity")
    ax.set_xlabel("Hours")
    return fig


def main():
    df = pd.read_csv("tracked.csv")
    df = add_columns(df)
    for url in ["http://www.vg.no/", "https://www.nrk.no/nyheter/", "http://www.dagbladet.no/"]:
        plot_sim(url, df).show()
        plot_ts_diff(url, df).show()
    plot_similarities("http://www.dagbladet.no/", add_columns(df, True)).show()
    print(df.corr().iloc[-3::, -3::])


if __name__ == '__main__':
    main()
