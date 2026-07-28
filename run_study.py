#!/usr/bin/env python3
"""
Runs the prospective/retrospective interpretive-provenance use case
(biliary atresia GWAS, Chen et al. 2018) against local Ollama models.

REDESIGN NOTE (second round): the prospective condition was redesigned.
It no longer withholds that a replication cohort exists. It now gives the
agent the full results, both cohorts and the meta-analysis, and withholds
only the authors' own Discussion and interpretation. This makes
prospective and retrospective symmetric on the same evidence base, the
only difference is whether the authors' own reasoning is present. The
prior design (discovery-cohort-only evidence) tested whether an agent
notices a missing replication cohort. This design tests whether an agent
reasoning from bare, fully replicated results, with no author present to
state the caveat, still correctly withholds a mechanism claim, or
overreaches from a confirmed statistical association into a confirmed
causal mechanism. See evidence_full_results.json and the updated
prospective prompt in prompts.md.

Requires Ollama running locally with the target models already pulled:
    ollama pull llama3:latest
    ollama pull mistral:latest
    ollama pull deepseek-r1:8b

deepseek-r1:8b is a current-generation open-weight reasoning model,
added as a robustness check against the concern (raised independently
by two reviewers) that the original two models, Llama 3 8B and
Mistral 7B, are no longer representative of what readers associate
with agentic reasoning systems. It emits an explicit chain-of-thought
before its final answer. Depending on the Ollama version, this shows
up either inline in the response text (wrapped in <think> tags) or in
a separate "thinking" field if the request asks for it. This script
requests it explicitly via the "think" option and captures both
fields defensively, so the full reasoning trace is preserved either
way.

Usage:
    python3 run_study.py --repeats 5
    python3 run_study.py --repeats 5 --models deepseek-r1:8b
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
    rather than overwriting, so re-running with a new model or label set
    does not erase prior runs). Each record contains the model, mode, label
    set, repeat index, temperature, the full prompt sent, the raw response
    text, and, for reasoning models, the separate thinking trace if the
    running Ollama version exposes one. Nothing is scored automatically.
    Scoring is done by hand afterward, since that is the actual point of
    the exercise: reading whether the model's own stated reasoning
    supports the scope it picked.
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error

DEFAULT_HOST = "http://localhost:11434"
DEFAULT_MODELS = ["llama3:latest", "mistral:latest", "deepseek-r1:8b"]  # Llama 3 8B, Mistral 7B, DeepSeek-R1 8B
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
    return f"""You are a geneticist reviewing the complete analytical results of a
genetic association study of biliary atresia (BA), a rare pediatric liver
disease. The evidence below includes results from two separate patient
cohorts and a combined meta-analysis. It does not include any
interpretation, discussion, or conclusion written by the study's authors.
Do not use any outside knowledge you may have about this gene, locus, or
disease. Base your answer only on the evidence provided.

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
        "think": True,
        "options": {"temperature": temperature},
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=900) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        # Older Ollama versions, or non-reasoning models, may reject the
        # "think" field outright. Retry once without it before giving up,
        # so this script still works against llama3/mistral and against
        # Ollama versions that predate the think parameter.
        payload.pop("think", None)
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=900) as resp:
            body = json.loads(resp.read().decode("utf-8"))

    response_text = body.get("response", "")
    thinking_text = body.get("thinking", "")

    # If the running Ollama version does not separate thinking into its
    # own field, a reasoning model's <think>...</think> block will be
    # sitting inline inside response_text already. In that case
    # thinking_text stays empty and the full trace is still preserved,
    # just undivided, in response_text. We do not attempt to strip or
    # parse <think> tags here. The point of this script is to keep the
    # model's own words intact for a human to read afterward, not to
    # post-process them.
    return response_text, thinking_text


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

    evidence_path = os.path.join(SCRIPT_DIR, "evidence_full_results.json")
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
                        response_text, thinking_text = call_ollama(
                            args.host, model, prompt, args.temperature
                        )
                    except (urllib.error.URLError, TimeoutError, OSError) as e:
                        print(
                            f"  ERROR calling Ollama for {model}/{mode_name}/"
                            f"{label_set_name}/{repeat_idx}: {e}. Recording "
                            f"as failed and continuing with the next run.",
                            file=sys.stderr,
                        )
                        response_text = None
                        thinking_text = None

                    record = {
                        "model": model,
                        "mode": mode_name,
                        "label_set": label_set_name,
                        "labels": labels,
                        "repeat": repeat_idx,
                        "temperature": args.temperature,
                        "prompt": prompt,
                        "response": response_text,
                        "thinking": thinking_text,
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
