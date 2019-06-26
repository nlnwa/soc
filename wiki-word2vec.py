import json
import re
from pprint import pprint

import numpy
from gensim.models import Doc2Vec
from sklearn.cluster import OPTICS
from sklearn.manifold import TSNE

print("Loading wiki...")

# wiki = re.split("\n\n", open("res/wiki/nowiki.txt").read())
# wiki = [w.strip() for w in wiki]
#
# print(len(wiki))

# wiki = WikiCorpus("res/nowiki-20190601-pages-articles.xml.bz2", article_min_tokens=1000)
# # MmCorpus.serialize("nowiki-corpus.mm", wiki)
#
# # wiki = MmCorpus.load("nowiki-corpus.mm")
#
#
# class TaggedWikiDocument(object):
#     def __init__(self, wiki):
#         self.wiki = wiki
#         self.wiki.metadata = True
#
#     def __iter__(self):
#         for content, (page_id, title) in self.wiki.get_texts():
#             yield TaggedDocument([c for c in content], [title])
#
#
# print("Wiki loaded. Vectorizing...")
# # print(wiki[0])
#
#
# documents = TaggedWikiDocument(wiki)
# model = Doc2Vec(documents, window=8, vector_size=256)
#
# model.save("nowiki-word2vec")
model = Doc2Vec.load("nowiki-word2vec")

# print(model.vocabulary)

# pprint(model.docvecs.most_similar(positive=["Maskinlæring"], topn=10))
pprint(model.docvecs.most_similar(positive=["Mo i Rana"], topn=10))
pprint(model.docvecs.most_similar(positive=["Tiger"], topn=10))
pprint(model.docvecs.most_similar(positive=["Nasjonalbiblioteket"], topn=10))
# pprint(model.docvecs.most_similar(positive=["The Rock"], topn=10))

print("Trained...")
vectors = []
for art in model.docvecs.vectors_docs:
    vectors.append(art)

n_comp = 2
pca = TSNE(n_components=n_comp).fit_transform(vectors)

write = open("nowiki-tsne.csv", "w")
write.write("Title,f1,f2\n")
for art, (pca1, pca2) in zip(model.docvecs.doctags, pca):
    title = re.sub("[,'\"]", "|", art)
    write.write(f"{title},{pca1},{pca2}\n")

# d = {"Article": []}
# for i in range(n_comp):
#     d[f"SVD{i}"] = []
#
# for art, p in zip(wiki[:1000], pca[:1000]):
#     title = re.sub(r"[^\w ]", "", re.split(r":", art, maxsplit=1)[0])[:32]
#     d["Article"].append(title)
#     for i in range(n_comp):
#         d[f"SVD{i}"].append(p[i])
#
# exit(0)
# df = DataFrame(data=d)
# df.to_csv("wiki-svd.tsv", index=False, sep="\t")

print("Vectorized. Clustering...")

# clust = 16

cluster = OPTICS().fit_predict(vectors)
numpy.save("optics-fitpredict.npy", cluster)
clust = max(cluster) + 2

clusters = {str(i): [] for i in cluster}
for art, i in zip(model.docvecs.doctags, cluster):
    clusters[str(i)].append(re.split(r":\n", art, maxsplit=2)[0])
    # print(re.split(r":\n", art, maxsplit=1)[0], i)
    # print(re.split(r":\n", art, maxsplit=1)[0], cluster.predict(vectorizer.transform([art])))

with open('clusters2.json', 'w') as outfile:
    json.dump(clusters, outfile, indent=4, ensure_ascii=False)

print("Clustering done")
