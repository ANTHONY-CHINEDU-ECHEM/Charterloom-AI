"""Hybrid retrieval over the organisational knowledge base.

Documents are split into section aware, overlapping chunks. Every chunk is
indexed twice:

  lexical   Okapi BM25 implemented as a precomputed sparse weight matrix, so a
            query is scored against every chunk with one sparse matrix product
  semantic  dense LSA embeddings scored by cosine similarity

The two ranked lists are combined with reciprocal rank fusion, which is robust
to the very different score scales of BM25 and cosine similarity. Chunk scores
are then pooled to document level so callers receive whole documents with the
best matching passage attached as evidence.

Project level retrieval uses a second index. Charters are compared in a hybrid
project space that concatenates the semantic embedding with standardised,
interpretable charter features, so that two projects are close when they read
alike and also share delivery characteristics such as team shape, interrupt
load or regulatory exposure. This index supplies precedent blueprints and the
post mortems whose lessons drive the customizer.
"""

import math
from dataclasses import asdict, dataclass, field

import numpy as np
from scipy import sparse
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.preprocessing import StandardScaler, normalize

from charterloom.text import chunk_words, minus, snippet, split_sections, tokenize


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    doc_type: str
    title: str
    section: str
    text: str
    metadata: dict = field(default_factory=dict)


@dataclass
class RetrievalHit:
    doc_id: str
    doc_type: str
    title: str
    score: float
    dense_score: float
    bm25_score: float
    section: str
    passage: str
    metadata: dict
    rank: int = 0

    def to_dict(self, passage_chars=420):
        payload = asdict(self)
        payload["passage"] = snippet(self.passage, passage_chars)
        payload["score"] = round(self.score, 5)
        payload["dense_score"] = round(self.dense_score, 4)
        payload["bm25_score"] = round(self.bm25_score, 3)
        return payload


def build_chunks(documents, max_words=170, overlap=40):
    """Split documents into section aware chunks with title context prepended."""
    chunks = []
    for doc in documents:
        sections = split_sections(doc.text, default_title=doc.title)
        if doc.doc_type == "blueprint":
            sections = [("Blueprint", doc.text)]
        counter = 0
        for heading, body in sections:
            for piece in chunk_words(body, max_words=max_words, overlap=overlap):
                counter += 1
                chunks.append(Chunk(
                    chunk_id=f"{doc.doc_id}#{counter}",
                    doc_id=doc.doc_id,
                    doc_type=doc.doc_type,
                    title=doc.title,
                    section=heading,
                    text=f"{doc.title}. {heading}. {piece}",
                    metadata=doc.metadata,
                ))
    return chunks


class Bm25Index:
    """Okapi BM25 over a fixed chunk collection, stored as a sparse weight matrix."""

    def __init__(self, k1=1.4, b=0.72):
        self.k1 = k1
        self.b = b
        self.vectorizer = CountVectorizer(tokenizer=tokenize, lowercase=False, token_pattern=None, dtype=np.float32)
        self.weights = None

    def fit(self, texts):
        tf = self.vectorizer.fit_transform(texts).tocsr().astype(np.float32)
        n_docs = tf.shape[0]
        df = np.asarray((tf > 0).sum(axis=0)).ravel().astype(np.float64)
        idf = np.log1p((minus(n_docs, df) + 0.5) / (df + 0.5))
        lengths = np.asarray(tf.sum(axis=1)).ravel()
        avg_length = float(lengths.mean()) if n_docs else 1.0
        coo = tf.tocoo()
        norm = self.k1 * (minus(1.0, self.b) + self.b * lengths[coo.row] / avg_length)
        data = idf[coo.col] * coo.data * (self.k1 + 1.0) / (coo.data + norm)
        self.weights = sparse.csr_matrix((data.astype(np.float32), (coo.row, coo.col)), shape=tf.shape)
        self.idf_ = idf
        return self

    def score(self, query):
        q = self.vectorizer.transform([query])
        q.data[:] = 1.0
        return np.asarray((self.weights @ q.T).todense()).ravel()


class HybridRetriever:
    """BM25 plus dense retrieval fused with reciprocal rank fusion."""

    def __init__(self, embedder, k1=1.4, b=0.72, rrf_k=60, candidate_pool=200, chunk_size=170, chunk_overlap=40):
        self.embedder = embedder
        self.bm25 = Bm25Index(k1=k1, b=b)
        self.rrf_k = rrf_k
        self.candidate_pool = candidate_pool
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.chunks = []
        self.chunk_embeddings = None
        self._doc_types = None
        self._project_ids = None

    def index(self, documents):
        self.chunks = build_chunks(documents, self.chunk_size, self.chunk_overlap)
        texts = [c.text for c in self.chunks]
        self.bm25.fit(texts)
        self.chunk_embeddings = self.embedder.transform(texts)
        self._doc_types = np.array([c.doc_type for c in self.chunks])
        self._project_ids = np.array([c.metadata.get("project_id", "") for c in self.chunks])
        return self

    def __len__(self):
        return len(self.chunks)

    def _allowed(self, doc_types, exclude_project_ids):
        mask = np.ones(len(self.chunks), dtype=bool)
        if doc_types:
            mask &= np.isin(self._doc_types, list(doc_types))
        if exclude_project_ids:
            mask &= ~np.isin(self._project_ids, list(exclude_project_ids))
        return np.flatnonzero(mask)

    def search(self, query, top_k=8, doc_types=None, exclude_project_ids=None, query_embedding=None):
        """Return the ``top_k`` best documents for ``query`` with their best supporting passage."""
        allowed = self._allowed(doc_types, exclude_project_ids)
        if allowed.size == 0:
            return []
        if query_embedding is None:
            query_embedding = self.embedder.transform([query])[0]
        dense = self.chunk_embeddings[allowed] @ query_embedding
        lexical = self.bm25.score(query)[allowed]
        pool = min(self.candidate_pool, allowed.size)
        fused = {}
        for scores in (dense, lexical):
            order = np.argsort(np.negative(scores), kind="stable")[:pool]
            for rank, local in enumerate(order, start=1):
                fused[local] = fused.get(local, 0.0) + 1.0 / (self.rrf_k + rank)
        best_by_doc = {}
        for local, score in fused.items():
            chunk = self.chunks[allowed[local]]
            current = best_by_doc.get(chunk.doc_id)
            if current is None or score > current[0]:
                best_by_doc[chunk.doc_id] = (score, local)
        ranked = sorted(best_by_doc.items(), key=lambda item: item[1][0], reverse=True)[:top_k]
        hits = []
        for position, (doc_id, (score, local)) in enumerate(ranked, start=1):
            chunk = self.chunks[allowed[local]]
            hits.append(RetrievalHit(
                doc_id=doc_id, doc_type=chunk.doc_type, title=chunk.title, score=float(score),
                dense_score=float(dense[local]), bm25_score=float(lexical[local]), section=chunk.section,
                passage=chunk.text, metadata=dict(chunk.metadata), rank=position,
            ))
        return hits


class ProjectSpace:
    """Hybrid vector space joining semantic embeddings with standardised charter features."""

    def __init__(self, feature_weight=2.0):
        self.feature_weight = feature_weight
        self.scaler = StandardScaler()

    def fit(self, features):
        self.scaler.fit(features)
        return self

    def transform(self, embeddings, features):
        scaled = normalize(self.scaler.transform(np.atleast_2d(features)))
        joined = np.hstack([np.atleast_2d(embeddings), self.feature_weight * scaled])
        return normalize(joined).astype(np.float32)


class ProjectIndex:
    """Nearest historical projects in the hybrid project space."""

    def __init__(self, space):
        self.space = space

    def fit(self, vectors, blueprints, post_mortems_by_project):
        self.vectors = np.asarray(vectors, dtype=np.float32)
        self.blueprints = list(blueprints)
        self.post_mortems = post_mortems_by_project
        self.project_ids = np.array([b["project_id"] for b in self.blueprints])
        return self

    def nearest(self, vector, top_k, exclude_project_ids=None):
        sims = self.vectors @ np.asarray(vector, dtype=np.float32)
        allowed = np.ones(len(sims), dtype=bool)
        if exclude_project_ids:
            allowed &= ~np.isin(self.project_ids, list(exclude_project_ids))
        candidates = np.flatnonzero(allowed)
        order = candidates[np.argsort(np.negative(sims[candidates]), kind="stable")[:top_k]]
        return [(int(i), float(sims[i])) for i in order]

    def blueprint_hits(self, vector, top_k, exclude_project_ids=None):
        hits = []
        for rank, (i, sim) in enumerate(self.nearest(vector, top_k, exclude_project_ids), start=1):
            b = self.blueprints[i]
            hits.append(RetrievalHit(
                doc_id=b["blueprint_id"], doc_type="blueprint", title=b["title"], score=sim, dense_score=sim,
                bm25_score=0.0, section="Blueprint", passage=b["text"].split("Charter summary follows.")[0],
                metadata={"project_id": b["project_id"], "workflow_archetype": b["workflow_archetype"],
                          "outcome_score": b["outcome_score"], "high_performing": b["high_performing"],
                          "domain": b["domain"], "project_type": b["project_type"]},
                rank=rank,
            ))
        return hits

    def post_mortem_hits(self, vector, top_k, exclude_project_ids=None):
        hits = []
        for rank, (i, sim) in enumerate(self.nearest(vector, top_k, exclude_project_ids), start=1):
            pm = self.post_mortems.get(self.blueprints[i]["project_id"])
            if pm is None:
                continue
            sections = dict(split_sections(pm["text"]))
            lessons = sections.get("Lessons and recommended workflow adjustments", pm["text"])
            hits.append(RetrievalHit(
                doc_id=pm["post_mortem_id"], doc_type="post_mortem", title=pm["title"], score=sim,
                dense_score=sim, bm25_score=0.0, section="Lessons and recommended workflow adjustments",
                passage=lessons,
                metadata={"project_id": pm["project_id"], "workflow_archetype": pm["workflow_archetype"],
                          "outcome_score": pm["outcome_score"],
                          "recommended_adjustments": pm["recommended_adjustments"]},
                rank=rank,
            ))
        return hits


def mean_reciprocal_rank(relevance_lists):
    total = 0.0
    for flags in relevance_lists:
        for rank, flag in enumerate(flags, start=1):
            if flag:
                total += 1.0 / rank
                break
    return total / max(1, len(relevance_lists))


def ndcg_at_k(flags, k, total_relevant=None):
    """Normalised discounted cumulative gain with binary relevance."""
    flags = list(flags)[:k]
    dcg = sum(1.0 / math.log2(i + 2) for i, f in enumerate(flags) if f)
    available = sum(flags) if total_relevant is None else min(k, total_relevant)
    ideal = sum(1.0 / math.log2(i + 2) for i in range(available))
    return dcg / ideal if ideal else 0.0
