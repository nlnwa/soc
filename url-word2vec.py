import json
import re
from pprint import pprint

import numpy
from gensim.models import Doc2Vec
from sklearn.cluster import Birch
from sklearn.manifold import TSNE

# def iter_urls():
#     for p in os.listdir("res/webpages"):
#         f = open("res/webpages/" + p)
#         url, text = f.read().split("\n", maxsplit=1)
#         yield url, text
#
#
# class TaggedWebpageDocument(object):
#     def __iter__(self):
#         for url, text in iter_urls():
#             yield TaggedDocument([c for c in re.split(r"\s+", re.sub(r"[^\w\s]+", "", text)) if len(c) > 0], [url])
#
#
# print("Webpages loaded. Vectorizing...")
#
# documents = TaggedWebpageDocument()
# model = Doc2Vec(documents, window=8, vector_size=256)
#
# model.save("webpage-word2vec")
model = Doc2Vec.load("webpage-word2vec")

pprint(model.docvecs.most_similar(positive=["https://www.volkskrant.nl"], topn=10))
pprint(model.docvecs.most_similar(positive=["http://www.tilbryllupet.no"], topn=10))
pprint(model.docvecs.most_similar(positive=["https://ridderne.no"], topn=10))
pprint(model.docvecs.most_similar(positive=["https://stillingsok.nav.no"], topn=10))
# print(model.vocabulary)

print("Trained...")
vectors = []
for art in model.docvecs.vectors_docs:
    vectors.append(art)

n_comp = 3
pca = TSNE(n_components=n_comp).fit_transform(vectors)
numpy.save("wp-tsne3.npy", pca)
# pca = numpy.load("wp-tsne3.npy")

# read = open("webpage-tsne.csv")
# next(read)
write = open("webpage-tsne3-vec.csv", "w")
write.write("Title,f1,f2,f3\n")  # + ",".join([f"v{i}" for i in range(256)]) + "\n")
for art, (f1, f2, f3) in zip(model.docvecs.doctags, pca):
    title = re.sub("[,'\"]", "|", art)
    # it = [str(f) for f in vector]
    write.write(",".join([art, str(f1), str(f2), str(f3)]) + "\n")

print("Vectorized. Clustering...")

# clust = 16

cluster = Birch(n_clusters=20).fit_predict(vectors)
numpy.save("birch-fitpredict.npy", cluster)
clust = max(cluster) + 2

clusters = {str(i): [] for i in cluster}
for art, i in zip(model.docvecs.doctags, cluster):
    clusters[str(i)].append(re.split(r":\n", art, maxsplit=2)[0])
    # print(re.split(r":\n", art, maxsplit=1)[0], i)
    # print(re.split(r":\n", art, maxsplit=1)[0], cluster.predict(vectorizer.transform([art])))

with open('webpage-clusters.json', 'w') as outfile:
    json.dump(clusters, outfile, indent=4, ensure_ascii=False)

print("Clustering done")
