"""Semantic embeddings via latent semantic analysis.

The default encoder is a TF IDF model over unigrams and bigrams followed by a
truncated singular value decomposition (latent semantic analysis) and L2
normalisation. It runs fully offline, is deterministic, trains in seconds on the
bundled corpus and produces dense vectors whose cosine similarity captures
topical and stylistic similarity between charters.

Any encoder that implements ``fit``, ``transform`` and ``dimension`` can be
swapped in, for example a transformer sentence encoder in an environment with
model hub access.
"""

import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

from charterloom.text import tokenize


class LsaEmbedder:
    """TF IDF plus truncated SVD sentence embedder."""

    def __init__(self, dimension=256, max_features=80000, min_df=2, max_df=0.85, n_iter=7, random_state=0):
        self.requested_dimension = dimension
        self.vectorizer = TfidfVectorizer(
            tokenizer=tokenize,
            lowercase=False,
            token_pattern=None,
            ngram_range=(1, 2),
            min_df=min_df,
            max_df=max_df,
            max_features=max_features,
            sublinear_tf=True,
            dtype=np.float32,
        )
        self.svd = None
        self.n_iter = n_iter
        self.random_state = random_state
        self.explained_variance_ = None

    @property
    def dimension(self):
        return self.svd.n_components if self.svd is not None else self.requested_dimension

    def fit(self, texts):
        matrix = self.vectorizer.fit_transform(texts)
        components = int(min(self.requested_dimension, matrix.shape[1] // 2, matrix.shape[0] // 2))
        self.svd = TruncatedSVD(n_components=max(2, components), n_iter=self.n_iter, random_state=self.random_state)
        self.svd.fit(matrix)
        self.explained_variance_ = float(self.svd.explained_variance_ratio_.sum())
        return self

    def transform(self, texts):
        if self.svd is None:
            raise RuntimeError("LsaEmbedder must be fitted before use")
        matrix = self.vectorizer.transform(list(texts))
        dense = self.svd.transform(matrix)
        return normalize(dense).astype(np.float32)

    def fit_transform(self, texts):
        return self.fit(texts).transform(texts)

    def vocabulary_size(self):
        return len(self.vectorizer.vocabulary_)
