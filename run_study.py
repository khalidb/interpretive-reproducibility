#!/usr/bin/env python3
"""
Runs the prospective/retrospective interpretive-provenance use case
(biliary atresia GWAS, Chen et al. 2018) against local Ollama models.

Requires Ollama running locally with the target models already pulled:
    ollama pull llama3:latest
    ollama pull mistral:latest

Usage:
    python3 run_study.py --repeats 5
    python3 run_study.py --repeats 5 --labels neutral
    python3 run_study.py --repeats 5 --labels named neutral

Label ablation:
    --labels named   uses the original vocabulary: exploratory / candidate /
                      validated. This is what the first run used.
    --labels neutral uses arbitrary tokens: Tier A / Tier B / Tier C, with
                      the identical compound-criterion definitions attached
                      to each tier. The point is to check whether a model's
                      scope choice tracks the stated logic (threshold AND
                      replication) or tracks the familiar domain vocabulary
                      ("candidate [gene/locus]" is common idiom in GWAS
                      papers, independent of whether replication occurred).
                      If a model's answers differ between named and neutral
                      given the exact same evidence and logic, that is
                      evidence the named-label result was a lexical reflex
                      rather than an application of the stated criteria.

Output:
    Writes one JSON file per run to ./outputs/, plus a combined
    outputs/all_runs.json at the end (accumulates across script invocations
    rather than overwriting, so a --labels neutral run does not erase a
    prior --labels named run). Each record contains the model, mode, label
    set, repeat index, temperature, the full prompt sent, and the raw
    response text. Nothing is scored automatically. Scoring is done by hand
    afterward, since that is the actual point of the exercise: reading
    whether the model's own stated reasoning supports the scope it picked.
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error

DEFAULT_HOST = "http://localhost:11434"
DEFAULT_MODELS = ["llama3:latest", "mistral:latest"]  # Llama 3 8B, Mistral 7B
DEFAULT_TEMPERATURE = 0.7
DEFAULT_REPEATS = 5
DEFAULT_LABEL_SETS = ["named"]

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "outputs")

# Each label set maps the same three-tier compound logic onto different
# surface tokens. The low/mid/high semantics are identical across sets:
#   low  = preliminary; threshold not reached, or not replicated, or both
#   mid  = threshold reached AND independently replicated, mechanism not
#          established
#   high = threshold reached AND independently replicated AND mechanism
#          directly demonstrated
LABEL_SETS = {
    "named": {
        "low": "exploratory",
        "mid": "candidate",
        "high": "validated",
    },
    "neutral": {
        "low": "Tier A",
        "mid": "Tier B",
        "high": "Tier C",
    },
}


def scope_definitions(labels):
    return f"""Scope qualifier definitions:
- {labels['low']}: preliminary or hypothesis-generating; has not reached an
  accepted statistical threshold, has not been independently replicated,
  or both.
- {labels['mid']}: reaches an accepted statistical threshold and has been
  independently replicated, but the causal or functional mechanism is not
  established.
- {labels['high']}: reaches an accepted statistical threshold, has been
  independently replicated, AND the causal or functional mechanism has
  been directly demonstrated."""


def response_structure_prospective(labels):
    return f"""Respond in exactly this structure:
1. Evidence used: list the IDs of the evidence items you relied on.
2. Reasoning steps: a numbered list of the inferential steps connecting
   that evidence to your conclusion.
3. Claim: a single sentence stating your conclusion about EFEMP1 and BA
   susceptibility.
4. Scope: exactly one of {labels['low']}, {labels['mid']}, or
   {labels['high']}, with one sentence justifying the choice."""


def response_structure_retrospective(labels):
    return f"""Respond in exactly this structure:
1. Evidence used: list, in your own words, the findings the authors treated
   as evidence for their central claim.
2. Reasoning steps: a numbered list of the inferential steps connecting
   that evidence to the authors' claim, as you understand them from the
   text.
3. Claim: restate the authors' central claim in a single sentence.
4. Scope: exactly one of {labels['low']}, {labels['mid']}, or
   {labels['high']}, with one sentence justifying the choice based on what
   the text actually supports."""


def build_prospective_prompt(evidence_json_text, labels):
    return f"""You are a geneticist reviewing preliminary results from a genome-wide
association study (GWAS) of biliary atresia (BA), a rare pediatric liver
disease. You are given only the evidence below, from a single discovery
cohort. No replication cohort has been analyzed yet, and no functional or
mechanistic follow-up study exists yet. Do not use any outside knowledge
you may have about this gene, locus, or disease. Base your answer only on
the evidence provided.

{scope_definitions(labels)}

Evidence:
{evidence_json_text}

{response_structure_prospective(labels)}"""


def build_retrospective_prompt(reasoning_trace_text, labels):
    return f"""Below is an excerpt from the Results and Discussion sections of a published
genetics paper on biliary atresia (BA). Read it and reconstruct the
authors' own reasoning. Base your answer only on what is stated in the text
below, not on outside knowledge of this gene or locus.

{scope_definitions(labels)}

Text:
{reasoning_trace_text}

{response_structure_retrospective(labels)}"""


def call_ollama(host, model, prompt, temperature):
    url = f"{host}/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature},
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return body.get("response", "")


def load_existing_runs(combined_path):
    if os.path.exists(combined_path):
        with open(combined_path, "r") as f:
            return json.load(f)
    return []


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    parser.add_argument("--repeats", type=int, default=DEFAULT_REPEATS)
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    parser.add_argument(
        "--labels",
        nargs="+",
        choices=list(LABEL_SETS.keys()),
        default=DEFAULT_LABEL_SETS,
        help="Which label set(s) to run: named (original), neutral "
        "(Tier A/B/C ablation), or both.",
    )
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    evidence_path = os.path.join(SCRIPT_DIR, "evidence_discovery_cohort.json")
    trace_path = os.path.join(SCRIPT_DIR, "reasoning_trace_retrospective.md")

    with open(evidence_path, "r") as f:
        evidence_json_text = f.read()
    with open(trace_path, "r") as f:
        reasoning_trace_text = f.read()

    combined_path = os.path.join(OUTPUT_DIR, "all_runs.json")
    all_runs = load_existing_runs(combined_path)

    total = len(args.models) * len(args.labels) * 2 * args.repeats
    done = 0

    for label_set_name in args.labels:
        labels = LABEL_SETS[label_set_name]
        modes = {
            "prospective": build_prospective_prompt(evidence_json_text, labels),
            "retrospective": build_retrospective_prompt(
                reasoning_trace_text, labels
            ),
        }

        for model in args.models:
            for mode_name, prompt in modes.items():
                for repeat_idx in range(1, args.repeats + 1):
                    done += 1
                    print(
                        f"[{done}/{total}] model={model} mode={mode_name} "
                        f"labels={label_set_name} repeat={repeat_idx} ...",
                        file=sys.stderr,
                    )
                    try:
                        response_text = call_ollama(
                            args.host, model, prompt, args.temperature
                        )
                    except urllib.error.URLError as e:
                        print(
                            f"  ERROR calling Ollama for {model}/{mode_name}/"
                            f"{label_set_name}/{repeat_idx}: {e}",
                            file=sys.stderr,
                        )
                        response_text = None

                    record = {
                        "model": model,
                        "mode": mode_name,
                        "label_set": label_set_name,
                        "labels": labels,
                        "repeat": repeat_idx,
                        "temperature": args.temperature,
                        "prompt": prompt,
                        "response": response_text,
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    }
                    all_runs.append(record)

                    safe_model = model.replace(":", "-").replace("/", "-")
                    out_name = (
                        f"{safe_model}__{mode_name}__{label_set_name}"
                        f"__{repeat_idx}.json"
                    )
                    with open(os.path.join(OUTPUT_DIR, out_name), "w") as f:
                        json.dump(record, f, indent=2)

    with open(combined_path, "w") as f:
        json.dump(all_runs, f, indent=2)

    print(f"\nDone. {len(all_runs)} total runs now in {combined_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
