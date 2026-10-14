"""State machine validation, editing and rendering.

Generated configurations are consumed by a project management backend, so they
must be structurally sound before they leave Charterloom. The validator enforces
graph properties (single entry point, reachability, no trap states), referential
integrity of guards and triggers, and compliance properties such as segregation
of duties on release transitions for strictly regulated work.
"""

from collections import deque
from dataclasses import dataclass, field

from charterloom.catalog import REGIME_BY_KEY
from charterloom.text import minus

CATEGORY_COLOURS = {
    "backlog": "#E8EEF7",
    "todo": "#D6E4F5",
    "in_progress": "#FCE9C8",
    "review": "#E3D9F2",
    "blocked": "#F6D3D3",
    "done": "#D3EFDA",
    "cancelled": "#E4E4E4",
}


@dataclass
class ValidationReport:
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    @property
    def valid(self):
        return not self.errors

    def to_dict(self):
        return {"valid": self.valid, "errors": self.errors, "warnings": self.warnings, "stats": self.stats}


def _adjacency(config):
    graph = {s["key"]: [] for s in config["states"]}
    for t in config["transitions"]:
        if t["from"] in graph:
            graph[t["from"]].append(t["to"])
    return graph


def _reachable(graph, start):
    seen = {start}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        for nxt in graph.get(node, []):
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    return seen


def validate(config):
    """Validate a workflow configuration and return a ``ValidationReport``."""
    report = ValidationReport()
    states = config.get("states", [])
    transitions = config.get("transitions", [])
    keys = [s["key"] for s in states]
    key_set = set(keys)

    if len(keys) != len(key_set):
        report.errors.append("Duplicate state keys detected")
    t_keys = [t["key"] for t in transitions]
    if len(t_keys) != len(set(t_keys)):
        report.errors.append("Duplicate transition keys detected")

    initial = [s["key"] for s in states if s.get("initial")]
    terminal = {s["key"] for s in states if s.get("terminal")}
    if len(initial) != 1:
        report.errors.append(f"Expected exactly one initial state, found {len(initial)}")
    if not terminal:
        report.errors.append("No terminal state defined")

    for t in transitions:
        for end in ("from", "to"):
            if t[end] not in key_set:
                report.errors.append(f"Transition {t['key']} references unknown state {t[end]}")
        if t["from"] in terminal:
            report.errors.append(f"Transition {t['key']} leaves terminal state {t['from']}")
        for g in t.get("guards", []):
            if g["type"] == "approval" and int(g.get("min_approvals", 0)) < 1:
                report.errors.append(f"Approval guard on {t['key']} requires at least one approver")

    for s in states:
        wip = s.get("wip_limit")
        if wip is not None and (not isinstance(wip, int) or wip < 1):
            report.errors.append(f"State {s['key']} has invalid WIP limit {wip}")
        sla = s.get("sla_hours")
        if sla is not None and sla <= 0:
            report.errors.append(f"State {s['key']} has invalid SLA {sla}")

    graph = _adjacency(config)
    if len(initial) == 1 and not report.errors:
        reachable = _reachable(graph, initial[0])
        unreachable = sorted(key_set ^ reachable)
        if unreachable:
            report.errors.append(f"Unreachable states: {', '.join(unreachable)}")
        for key in keys:
            if key in terminal:
                continue
            if not (_reachable(graph, key) & terminal):
                report.errors.append(f"State {key} cannot reach any terminal state")
        report.stats["reachable_states"] = len(reachable)

    for trig in config.get("triggers", []):
        for part in str(trig.get("action", "")).split(";"):
            verb, _, target = part.partition(":")
            if verb == "transition" and target not in set(t_keys):
                report.errors.append(f"Trigger {trig['key']} references unknown transition {target}")
            if verb == "move" and target not in key_set:
                report.errors.append(f"Trigger {trig['key']} references unknown state {target}")

    regimes = config.get("compliance", {}).get("regimes", [])
    strict = [r for r in regimes if r in REGIME_BY_KEY and REGIME_BY_KEY[r].strictness >= 2]
    release_key = config.get("anchors", {}).get("release_transition")
    release = next((t for t in transitions if t["key"] == release_key), None)
    if strict and release is not None:
        segregated = any(g["type"] == "approval" and g.get("distinct_from_author") for g in release["guards"])
        if not segregated:
            report.errors.append("Strict regimes require segregation of duties on the release transition")
    if release is None and release_key:
        report.warnings.append(f"Release anchor {release_key} not found")

    for s in states:
        if s["category"] == "in_progress" and s.get("wip_limit") is None:
            report.warnings.append(f"Active state {s['key']} has no WIP limit")

    report.stats.update({
        "states": len(states),
        "transitions": len(transitions),
        "triggers": len(config.get("triggers", [])),
        "guarded_transitions": sum(1 for t in transitions if t.get("guards")),
        "terminal_states": len(terminal),
    })
    return report


class StateMachineEditor:
    """Safe, anchor aware edits on a workflow configuration."""

    def __init__(self, config):
        self.config = config
        self.changelog = []

    def _state(self, key):
        return next((s for s in self.config["states"] if s["key"] == key), None)

    def _transition(self, key):
        return next((t for t in self.config["transitions"] if t["key"] == key), None)

    def log(self, change, reason, evidence=()):
        self.changelog.append({"change": change, "reason": reason, "evidence": list(evidence)})

    def insert_gate(self, key, name, approver_role, artifact, reason, evidence=(), sla_hours=72, min_approvals=1):
        """Splice a review gate between the pre release state and the release target.

        The release anchor transition A to R becomes A to G; a new transition G to R
        carries the gate approval; a failure transition G back to the rework state
        keeps the graph free of trap states. The anchor then moves to G to R so
        further gates chain in a deterministic order.
        """
        if self._state(key):
            return False
        anchors = self.config["anchors"]
        release = self._transition(anchors["release_transition"])
        if release is None:
            return False
        target = release["to"]
        position = next(i for i, s in enumerate(self.config["states"]) if s["key"] == target)
        self.config["states"].insert(position, {
            "key": key, "name": name, "category": "review", "initial": False, "terminal": False,
            "wip_limit": None, "sla_hours": sla_hours, "entry_criteria": [f"{artifact.replace('_', ' ').capitalize()} prepared"],
            "exit_criteria": [f"Approved by {approver_role.replace('_', ' ')}"],
        })
        release["to"] = key
        passed = {
            "key": f"{key}_passed", "name": f"{name} passed", "from": key, "to": target,
            "guards": [{"type": "approval", "role": approver_role, "min_approvals": min_approvals,
                        "distinct_from_author": True},
                       {"type": "linked_artifact", "artifact": artifact}],
            "actions": [],
        }
        failed = {"key": f"{key}_failed", "name": f"{name} failed", "from": key, "to": anchors["rework"],
                  "guards": [{"type": "field_required", "field": f"{key}_findings"}],
                  "actions": [{"type": "notify", "audience": "assignee"}]}
        self.config["transitions"].extend([passed, failed])
        anchors["release_transition"] = passed["key"]
        if approver_role not in self.config["roles"]:
            self.config["roles"].append(approver_role)
        self.log(f"Inserted gate '{name}' before {target}", reason, evidence)
        return True

    def add_guard(self, transition_key, guard, reason, evidence=()):
        t = self._transition(transition_key)
        if t is None or guard in t["guards"]:
            return False
        t["guards"].append(guard)
        is_release = transition_key == self.config.get("anchors", {}).get("release_transition")
        label = f"the release transition ({transition_key})" if is_release else transition_key
        detail = guard.get("role") or guard.get("field") or guard.get("artifact") or guard.get("checklist") or guard.get("meaning")
        kind = guard["type"].replace("_", " ")
        self.log(f"Added {kind} guard{f' ({detail})' if detail else ''} to {label}", reason, evidence)
        return True

    def add_trigger(self, trigger, reason, evidence=()):
        if any(t["key"] == trigger["key"] for t in self.config["triggers"]):
            return False
        self.config["triggers"].append(trigger)
        self.log(f"Added automation '{trigger['key']}'", reason, evidence)
        return True

    def add_ceremony(self, ceremony, reason, evidence=()):
        if any(c["name"] == ceremony["name"] for c in self.config["ceremonies"]):
            return False
        self.config["ceremonies"].append(ceremony)
        self.log(f"Added ceremony '{ceremony['name']}'", reason, evidence)
        return True

    def set_wip(self, state_key, value, reason):
        s = self._state(state_key)
        if s is None:
            return False
        old = s.get("wip_limit")
        s["wip_limit"] = int(max(1, value))
        if old != s["wip_limit"]:
            self.log(f"WIP limit for {state_key} set from {old} to {s['wip_limit']}", reason)
        return True

    def mark_release(self):
        """Flag the transition that finally releases work so backends can treat it specially."""
        key = self.config["anchors"]["release_transition"]
        for t in self.config["transitions"]:
            t["is_release"] = t["key"] == key

    def scale_sla(self, factor, reason):
        changed = 0
        for s in self.config["states"]:
            if s.get("sla_hours"):
                s["sla_hours"] = int(max(1, round(s["sla_hours"] * factor)))
                changed += 1
        if changed:
            self.log(f"Scaled {changed} state SLAs by {factor:.2f}", reason)


def _layers(config):
    """Longest path layering after removing cycle closing edges, so the main flow reads left to right."""
    graph = _adjacency(config)
    initial = next(s["key"] for s in config["states"] if s.get("initial"))
    forward = {k: [] for k in graph}
    state, order = {}, []

    def visit(node):
        state[node] = "active"
        for nxt in graph[node]:
            if state.get(nxt) == "active":
                continue
            forward[node].append(nxt)
            if nxt not in state:
                visit(nxt)
        state[node] = "done"
        order.append(node)

    visit(initial)
    for key in graph:
        if key not in state:
            visit(key)
    depth = {k: 0 for k in graph}
    for node in reversed(order):
        for nxt in forward[node]:
            depth[nxt] = max(depth[nxt], depth[node] + 1)
    return depth


def render_state_machine(config, path, title=None):
    """Draw the configuration as a layered state diagram and save it as PNG."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

    depth = _layers(config)
    columns = {}
    for s in config["states"]:
        columns.setdefault(depth[s["key"]], []).append(s)
    n_cols = max(columns) + 1
    n_rows = max(len(v) for v in columns.values())
    fig_w, fig_h = max(10.0, 2.3 * n_cols), max(4.5, 1.35 * n_rows + 1.6)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=150)
    positions = {}
    for col, items in columns.items():
        offset = minus(n_rows, len(items)) / 2.0
        for row, s in enumerate(items):
            positions[s["key"]] = (col * 2.3 + 1.0, (offset + row) * 1.35 + 0.8)
    box_w, box_h = 1.9, 0.72
    for s in config["states"]:
        x, y = positions[s["key"]]
        patch = FancyBboxPatch((x, y), box_w, box_h, boxstyle="round,pad=0.02,rounding_size=0.12",
                               facecolor=CATEGORY_COLOURS.get(s["category"], "#FFFFFF"),
                               edgecolor="#1F2A44", linewidth=2.2 if s.get("terminal") or s.get("initial") else 1.0)
        ax.add_patch(patch)
        label = s["name"]
        if len(label) > 22:
            words = label.split()
            cut = max(1, len(words) // 2)
            label = " ".join(words[:cut]) + "\n" + " ".join(words[cut:])
        ax.text(x + box_w / 2, y + box_h * 0.64, label, ha="center", va="center",
                fontsize=7.4 if "\n" not in label else 6.4, color="#111827", fontweight="bold", linespacing=1.0)
        meta = s["category"].replace("_", " ")
        if s.get("wip_limit"):
            meta += f" | WIP {s['wip_limit']}"
        ax.text(x + box_w / 2, y + box_h * 0.25, meta, ha="center", va="center", fontsize=6.2, color="#374151")
    for t in config["transitions"]:
        if t["from"] not in positions or t["to"] not in positions:
            continue
        x1, y1 = positions[t["from"]]
        x2, y2 = positions[t["to"]]
        forward = depth[t["to"]] > depth[t["from"]]
        if forward:
            skip = minus(depth[t["to"]], depth[t["from"]]) > 1
            start, end = (x1 + box_w, y1 + box_h / 2), (x2, y2 + box_h / 2)
            rad = minus(0.0, 0.12) if skip else 0.0
            if skip:
                start, end = (x1 + box_w / 2, y1 + box_h), (x2 + box_w / 2, y2 + box_h)
            colour, style = ("#1F4E8C" if t.get("guards") else "#6B7280"), "solid"
        else:
            start, end = (x1 + box_w / 2, y1), (x2 + box_w / 2, y2)
            span = max(1.0, abs(minus(x1, x2)))
            bend = min(0.32, 2.2 / span)
            rad = minus(0.0, bend) if x2 < x1 else bend
            colour, style = "#B0AFA8", (0, (3, 2))
        arrow = FancyArrowPatch(start, end, arrowstyle="simple,head_width=4,head_length=5,tail_width=0.35",
                                connectionstyle=f"arc3,rad={rad}", color=colour, linewidth=0.6, alpha=0.9,
                                linestyle=style, mutation_scale=1.0)
        ax.add_patch(arrow)
    ax.text(0.6, minus(0.0, 1.05), "Solid blue: guarded forward transition. Grey: unguarded. Dashed: rework, failure or return path.",
            fontsize=6.8, color="#52514e")
    ax.set_xlim(0.5, n_cols * 2.3 + 0.8)
    ax.set_ylim(minus(0.0, 1.25), n_rows * 1.35 + 1.2)
    ax.axis("off")
    ax.set_title(title or config.get("workflow", {}).get("display_name", "Workflow"), fontsize=12, loc="left",
                 color="#111827", fontweight="bold")
    legend = [("backlog", "Backlog"), ("todo", "To do"), ("in_progress", "In progress"), ("review", "Review or gate"),
              ("blocked", "Blocked"), ("done", "Done"), ("cancelled", "Cancelled")]
    for i, (cat, text) in enumerate(legend):
        ax.add_patch(FancyBboxPatch((0.6 + i * 1.45, n_rows * 1.35 + 0.75), 0.25, 0.22, boxstyle="round,pad=0.01",
                                    facecolor=CATEGORY_COLOURS[cat], edgecolor="#1F2A44", linewidth=0.6))
        ax.text(0.95 + i * 1.45, n_rows * 1.35 + 0.86, text, fontsize=6.5, va="center", color="#374151")
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path
