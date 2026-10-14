"""Markdown evaluation summary with HTML tables.

HTML tables are used deliberately: they render on GitHub exactly like Markdown
tables while keeping every generated file free of hyphen characters.
"""

from charterloom.catalog import ADJUSTMENT_BY_CODE, ARCHETYPE_BY_KEY


def html_table(headers, rows):
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = "\n".join("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows)
    return f"<table>\n<thead><tr>{head}</tr></thead>\n<tbody>\n{body}\n</tbody>\n</table>"


def _f(value):
    return f"{value:.3f}" if isinstance(value, float) else str(value)


def write_markdown_summary(report, reports_dir):
    rec = report["recommendation"]
    proto = report["protocol"]
    lines = [
        "# Charterloom AI Evaluation Summary",
        "",
        f"Projects: {proto['projects']}. Training projects: {proto['train_projects']}. "
        f"Held out projects: {proto['test_projects']} ({proto['test_high_performing']} high performing). "
        f"Split: {proto['split']}.",
        "",
        "## Workflow recommendation",
        "",
        html_table(["Model", "Accuracy", "Macro F1", "Weighted F1", "Top 2", "Top 3", "Log loss", "ECE"],
                   [[name, _f(m["accuracy"]), _f(m["macro_f1"]), _f(m["weighted_f1"]), _f(m.get("top2_accuracy", "")),
                     _f(m.get("top3_accuracy", "")), _f(m.get("log_loss", "")), _f(m.get("ece", ""))]
                    for name, m in rec["models"].items()]),
        "",
        "## Per class results",
        "",
        html_table(["Workflow", "Precision", "Recall", "F1", "Support"],
                   [[ARCHETYPE_BY_KEY[k].display_name, _f(v["precision"]), _f(v["recall"]), _f(v["f1"]), v["support"]]
                    for k, v in rec["per_class"].items()]),
        "",
        "## Abstention and oracle agreement",
        "",
        html_table(["Measure", "Value"],
                   [["Review threshold", _f(rec["abstention"]["threshold"])],
                    ["Coverage above threshold", _f(rec["abstention"]["coverage"])],
                    ["Accuracy when confident", _f(rec["abstention"]["accuracy_when_confident"])],
                    ["Accuracy when flagged for review", _f(rec["abstention"]["accuracy_when_flagged"])],
                    ["Recommender agreement with latent optimal workflow", _f(rec["oracle_agreement"]["blended_vs_optimal_all_projects"])],
                    ["Keyword rules agreement with latent optimal workflow", _f(rec["oracle_agreement"]["rules_vs_optimal_all_projects"])],
                    ["Historical human choice agreement with latent optimal", _f(rec["oracle_agreement"]["historical_adoption_vs_optimal"])]]),
        "",
        "## Precedent retrieval",
        "",
        html_table(["Retriever", "Precision at 5", "Precision at 10", "MRR", "nDCG at 10"],
                   [[n, _f(v["precision_at_5"]), _f(v["precision_at_10"]), _f(v["mrr"]), _f(v["ndcg_at_10"])]
                    for n, v in report["retrieval"].items()]),
        "",
        "## Adjustment selection",
        "",
        html_table(["Strategy", "Precision", "Recall", "F1", "Exact set match"],
                   [[n, _f(v["precision"]), _f(v["recall"]), _f(v["f1"]), _f(v["exact_set_match"])]
                    for n, v in report["customization"].items()]),
        "",
        html_table(["Adjustment", "Precision", "Recall", "F1", "Support"],
                   [[ADJUSTMENT_BY_CODE[c].title, _f(v["precision"]), _f(v["recall"]), _f(v["f1"]), v["support"]]
                    for c, v in report["customization"]["Charterloom evidence plus priors"]["per_adjustment"].items()]),
        "",
        "## Generated configurations",
        "",
        html_table(["Measure", "Value"], [[k.replace("_", " ").capitalize(), _f(v)]
                                          for k, v in report["configurations"].items()
                                          if not isinstance(v, dict)]),
        "",
    ]
    path = reports_dir / "evaluation_summary.md"
    path.write_text("\n".join(lines), encoding="utf8")
    return path
