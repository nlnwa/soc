import json
import re

from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer

print("Loading wiki...")

wiki = re.split("\n\n", open("res/wiki/nowiki.txt").read())
wiki = [w.strip() for w in wiki]

print("Wiki loaded. Vectorizing...")
# print(wiki[0])

vectorizer = TfidfVectorizer()

train = vectorizer.fit_transform(wiki)


# n_comp = 128
# pca = TruncatedSVD(n_components=128).fit_transform(train)
#
# d = {"Article": []}
# for i in range(n_comp):
#     d[f"SVD{i}"] = []
#
# for art, p in zip(wiki[:1000], pca[:1000]):
#     title = re.sub(r"[^\w ]", "", re.split(r":", art, maxsplit=1)[0])[:32]
#     d["Article"].append(title)
#     for i in range(n_comp):
#         d[f"SVD{i}"].append(p[i])

# exit(0)
# df = DataFrame(data=d)
# df.to_csv("wiki-svd.tsv", index=False, sep="\t")

print("Vectorized. Clustering...")

clust = 16
cluster = KMeans(n_clusters=clust).fit_predict(train)


clusters = {i: [] for i in range(clust)}
for art, i in zip(wiki, cluster):
    clusters[i].append(re.split(r":\n", art, maxsplit=1)[0])
    # print(re.split(r":\n", art, maxsplit=1)[0], i)
    # print(re.split(r":\n", art, maxsplit=1)[0], cluster.predict(vectorizer.transform([art])))

with open('clusters.json', 'w') as outfile:
    json.dump(clusters, outfile, indent=4, ensure_ascii=False)

print("Clustering done")
