"""Loading, validating and slicing the knowledge base."""

import json
from dataclasses import dataclass, field
from pathlib import Path

from charterloom.text import fingerprint


@dataclass
class Document:
    """A retrievable unit of organisational knowledge."""

    doc_id: str
    doc_type: str
    title: str
    text: str
    metadata: dict = field(default_factory=dict)


DOC_TYPES = ("blueprint", "post_mortem", "methodology", "workflow_template")


class KnowledgeBase:
    """In memory view of the organisational archive.

    The knowledge base holds four document families. Blueprints and post mortems
    are keyed by project so that evaluation can hold entire projects out of the
    index and avoid any leakage between training and test charters.
    """

    def __init__(self, blueprints, post_mortems, methodologies, templates, root=None):
        self.blueprints = list(blueprints)
        self.post_mortems = list(post_mortems)
        self.methodologies = list(methodologies)
        self.templates = dict(templates)
        self.root = Path(root) if root else None
        self._post_mortem_by_project = {p["project_id"]: p for p in self.post_mortems}

    @classmethod
    def load(cls, directory):
        directory = Path(directory)
        blueprints_path = directory / "blueprints.jsonl"
        if not blueprints_path.exists():
            raise FileNotFoundError(
                f"No knowledge base found at {directory}. Run 'charterloom kb' to generate it."
            )
        blueprints = _read_jsonl(blueprints_path)
        post_mortems = _read_jsonl(directory / "post_mortems.jsonl")
        methodologies = []
        for path in sorted((directory / "methodologies").glob("*.md")):
            text = path.read_text(encoding="utf8")
            title = text.splitlines()[0].lstrip("#").strip() if text.strip() else path.stem
            methodologies.append({"methodology_id": path.stem, "title": title, "text": text, "path": str(path)})
        templates = {}
        for path in sorted((directory / "workflow_templates").glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf8"))
            templates[payload["archetype"]] = payload
        kb = cls(blueprints, post_mortems, methodologies, templates, root=directory)
        kb.validate()
        return kb

    def validate(self):
        ids = [b["project_id"] for b in self.blueprints]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate project identifiers in blueprints")
        missing = set(ids) ^ set(self._post_mortem_by_project)
        if missing:
            raise ValueError(f"Blueprints and post mortems are misaligned for {len(missing)} projects")
        if not self.templates:
            raise ValueError("Workflow template library is empty")

    def project_ids(self):
        return [b["project_id"] for b in self.blueprints]

    def subset(self, project_ids):
        """Return a knowledge base restricted to ``project_ids``; shared documents are kept."""
        keep = set(project_ids)
        return KnowledgeBase(
            [b for b in self.blueprints if b["project_id"] in keep],
            [p for p in self.post_mortems if p["project_id"] in keep],
            self.methodologies,
            self.templates,
            root=self.root,
        )

    def post_mortem_for(self, project_id):
        return self._post_mortem_by_project.get(project_id)

    def documents(self):
        docs = []
        for b in self.blueprints:
            docs.append(Document(
                doc_id=b["blueprint_id"], doc_type="blueprint", title=b["title"], text=b["text"],
                metadata={"project_id": b["project_id"], "workflow_archetype": b["workflow_archetype"],
                          "outcome_score": b["outcome_score"], "high_performing": b["high_performing"],
                          "domain": b["domain"], "project_type": b["project_type"], "year": b["year"]},
            ))
        for p in self.post_mortems:
            docs.append(Document(
                doc_id=p["post_mortem_id"], doc_type="post_mortem", title=p["title"], text=p["text"],
                metadata={"project_id": p["project_id"], "workflow_archetype": p["workflow_archetype"],
                          "outcome_score": p["outcome_score"],
                          "recommended_adjustments": p["recommended_adjustments"]},
            ))
        for m in self.methodologies:
            docs.append(Document(doc_id=f"METHOD_{m['methodology_id']}", doc_type="methodology",
                                 title=m["title"], text=m["text"], metadata={"source": m.get("path", "")}))
        for key, t in self.templates.items():
            docs.append(Document(doc_id=f"TEMPLATE_{key}", doc_type="workflow_template", title=t["display_name"],
                                 text=t.get("description_text", t["summary"]), metadata={"workflow_archetype": key}))
        return docs

    def fingerprint(self):
        return fingerprint(len(self.blueprints), *(b["blueprint_id"] + str(b["outcome_score"]) for b in self.blueprints),
                           *(m["text"] for m in self.methodologies))

    def stats(self):
        docs = self.documents()
        counts = {}
        for d in docs:
            counts[d.doc_type] = counts.get(d.doc_type, 0) + 1
        return {"documents": len(docs), "by_type": counts,
                "words": sum(len(d.text.split()) for d in docs)}


def load_ground_truth(directory):
    path = Path(directory) / "ground_truth" / "latent_labels.jsonl"
    if not path.exists():
        return {}
    return {row["project_id"]: row for row in _read_jsonl(path)}


def _read_jsonl(path):
    rows = []
    with open(path, encoding="utf8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows
