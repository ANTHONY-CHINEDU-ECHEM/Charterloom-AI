"""Command line interface.

Usage
  charterloom kb                          generate the synthetic knowledge base
  charterloom build                       train and persist the pipeline
  charterloom evaluate [limit=N]          run the held out evaluation and render figures
  charterloom recommend PATH [out=FILE] [diagram=FILE] [name=TEXT]
  charterloom examples                    run every charter in examples/charters
  charterloom templates                   list the workflow template library
  charterloom serve [host=H] [port=P]     start the REST API
  charterloom all                         kb, build, evaluate and examples in sequence
  charterloom help

Options are passed as key=value pairs so that commands never need dashed flags.
"""

import json
import logging
import sys
from pathlib import Path

from charterloom import __version__
from charterloom.catalog import ARCHETYPE_KEYS
from charterloom.config import load_settings

LOGGER = logging.getLogger("charterloom")


def _configure_logging():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                        datefmt="%H:%M:%S")


def _parse(tokens):
    positional, options = [], {}
    for token in tokens:
        if "=" in token:
            key, value = token.split("=", 1)
            options[key.strip().lower()] = value
        else:
            positional.append(token)
    return positional, options


def cmd_kb(settings, positional, options):
    from charterloom.knowledge.generator import KnowledgeBaseGenerator

    stats = KnowledgeBaseGenerator(settings).write()
    print(json.dumps(stats, indent=2))


def _load_kb(settings):
    from charterloom.knowledge.loader import KnowledgeBase

    return KnowledgeBase.load(settings.knowledge_base_dir)


def cmd_build(settings, positional, options):
    from charterloom.pipeline import CharterloomPipeline

    pipeline = CharterloomPipeline(settings).fit(_load_kb(settings))
    directory = pipeline.save()
    print(json.dumps({k: pipeline.manifest[k] for k in ("version", "training_projects", "chunks_indexed",
                                                         "embedding_dimension", "recommender", "training_seconds")},
                     indent=2))
    print(f"Pipeline saved to {directory}")


def _load_pipeline(settings):
    from charterloom.pipeline import CharterloomPipeline

    return CharterloomPipeline.load(settings.artifacts_dir)


def cmd_evaluate(settings, positional, options):
    from charterloom.evaluation import run_evaluation, write_report
    from charterloom.figures import render_all
    from charterloom.reporting import write_markdown_summary

    limit = int(options["limit"]) if "limit" in options else None
    report, _ = run_evaluation(settings, _load_kb(settings), max_configurations=limit)
    path = write_report(report, settings.reports_dir)
    render_all(report, settings.figures_dir, settings.knowledge_base_dir / "manifest.json")
    summary = write_markdown_summary(report, settings.reports_dir)
    print(json.dumps(report["recommendation"]["models"]["Charterloom blended"], indent=2))
    print(f"Report written to {path} and {summary}")


def _recommend_file(pipeline, path, out=None, diagram=None, name=None):
    from charterloom.state_machine import render_state_machine

    text = Path(path).read_text(encoding="utf8")
    result = pipeline.recommend(text, project_name=name)
    if out:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_text(json.dumps(result, indent=2), encoding="utf8")
    if diagram:
        Path(diagram).parent.mkdir(parents=True, exist_ok=True)
        render_state_machine(result["configuration"], diagram,
                             title=f"{result['project_name']}: {result['configuration']['workflow']['display_name']}")
    return result


def _print_result(result):
    rec = result["recommendation"]
    print(f"\nProject: {result['project_name']}")
    print(f"Recommended workflow: {result['configuration']['workflow']['display_name']} "
          f"(confidence {rec['confidence']:.0%}, review needed: {rec['needs_human_review']})")
    for alt in rec["ranking"][1:]:
        print(f"  alternative {alt['workflow']}: {alt['probability']:.0%}")
    print(result["rationale"]["summary"])
    print("Changes applied to the base template:")
    for change in result["configuration"]["changelog"]:
        print(f"  * {change['change']}  [{change['reason']}]")
    print(f"Configuration valid: {result['configuration']['validation']['valid']}; latency {result['latency_ms']} ms")


def cmd_recommend(settings, positional, options):
    if not positional:
        raise SystemExit("recommend needs a path to a charter file")
    pipeline = _load_pipeline(settings)
    result = _recommend_file(pipeline, positional[0], options.get("out"), options.get("diagram"), options.get("name"))
    _print_result(result)


def cmd_examples(settings, positional, options):
    pipeline = _load_pipeline(settings)
    charters = sorted((settings.examples_dir / "charters").glob("*.md"))
    outputs = settings.examples_dir / "outputs"
    figures = settings.reports_dir / "figures"
    summary = []
    for path in charters:
        result = _recommend_file(pipeline, path, outputs / f"{path.stem}.json", figures / f"workflow_{path.stem}.png")
        _print_result(result)
        summary.append({
            "charter": path.name,
            "project": result["project_name"],
            "workflow": result["configuration"]["workflow"]["display_name"],
            "confidence": result["recommendation"]["confidence"],
            "needs_human_review": result["recommendation"]["needs_human_review"],
            "states": len(result["configuration"]["states"]),
            "transitions": len(result["configuration"]["transitions"]),
            "triggers": len(result["configuration"]["triggers"]),
            "applied_adjustments": [a["code"] for a in result["configuration"]["adjustments"] if a["applied"]],
            "regimes": result["charter_profile"]["regimes"],
            "valid": result["configuration"]["validation"]["valid"],
        })
    (outputs / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf8")


def cmd_templates(settings, positional, options):
    from charterloom.knowledge.templates import build_template

    for key in ARCHETYPE_KEYS:
        t = build_template(key)
        print(f"{t['display_name']:<40} {len(t['states']):>2} states  {len(t['transitions']):>2} transitions  "
              f"{len(t['triggers']):>2} triggers")


def cmd_serve(settings, positional, options):
    import uvicorn

    from charterloom.api import create_app

    uvicorn.run(create_app(settings), host=options.get("host", "0.0.0.0"), port=int(options.get("port", 8000)))


def cmd_all(settings, positional, options):
    for step in (cmd_kb, cmd_build, cmd_evaluate, cmd_examples):
        step(settings, positional, options)


def cmd_help(settings, positional, options):
    print(f"Charterloom AI {__version__}")
    print(__doc__)


COMMANDS = {
    "kb": cmd_kb,
    "build": cmd_build,
    "evaluate": cmd_evaluate,
    "recommend": cmd_recommend,
    "examples": cmd_examples,
    "templates": cmd_templates,
    "serve": cmd_serve,
    "all": cmd_all,
    "help": cmd_help,
}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    _configure_logging()
    command = argv[0] if argv else "help"
    positional, options = _parse(argv[1:])
    settings = load_settings(options.pop("config", None))
    handler = COMMANDS.get(command)
    if handler is None:
        print(f"Unknown command '{command}'.")
        cmd_help(settings, [], {})
        return 2
    handler(settings, positional, options)
    return 0


if __name__ == "__main__":
    sys.exit(main())
