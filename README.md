# GWAS interpretive reproducibility use case

Source paper: Chen, Gilbert, Grochowski, et al. (2018), "A genome-wide
association study identifies a susceptibility locus for biliary atresia on
2p16.1 within the gene EFEMP1", PLOS Genetics 14(8):e1007532. Open access,
CC0.

REDESIGN NOTE (second round): the prospective condition below was
redesigned after the first round of runs. It no longer withholds that a
replication cohort exists. It now gives the agent the complete results,
both cohorts and the meta-analysis, and withholds only the authors' own
Discussion and interpretation. This makes prospective and retrospective
symmetric on the same evidence base, the only difference between the two
conditions is whether the authors' own reasoning is present or withheld.
The original design is preserved as evidence_discovery_cohort.json for
reference but is no longer used by run_study.py.

## What this tests

**Prospective mode**: the agent sees the complete analytical results
(evidence_full_results.json), both cohorts and the meta-analysis, but not
the authors' own Discussion or conclusion. Because the full, genuinely
replicated evidence is present, the correct scope answer here is
"candidate," the same correct answer as retrospective mode. The question
this mode actually tests is whether an agent, reasoning from bare results
with no author present to state the caveat, still correctly withholds an
unearned mechanism claim, or overreaches from "statistically confirmed
association" into "confirmed causal mechanism."

**Retrospective mode**: the agent sees the paper's own Results and
Discussion text (reasoning_trace_retrospective.md), including the
successful replication and meta-analysis. The authors themselves call
EFEMP1 a "candidate susceptibility gene," explicitly saying the causal
mechanism is unclear and other genes might be involved. An agent that
restates this as a confirmed or causal gene for BA fails to reconstruct
the authors' own restraint.

Full prompt text, including the scope-qualifier definitions given to the
agent, is in prompts.md.

## Prerequisites

1. Ollama installed and running locally (default: http://localhost:11434).
2. Both models pulled (Ollama's default `:latest` tags map to Llama 3 8B
   and Mistral 7B respectively, confirm with `ollama list`):
   ```
   ollama pull llama3:latest
   ollama pull mistral:latest
   ```

## Running

Because the prospective condition changed, old and new prospective runs
would both be labeled `"mode": "prospective"` in the output and be hard
to tell apart later. Archive the existing outputs before rerunning:

```
mv outputs outputs_round1_original_design
```

Then run the full study fresh:

```
python3 run_study.py --repeats 5
python3 run_study.py --repeats 5 --labels neutral
```

Options:
- `--models` : which models to run, default llama3:latest mistral:latest
  deepseek-r1:8b
- `--repeats` : repetitions per model per mode, default 5
- `--temperature` : sampling temperature, default 0.7
- `--host` : Ollama host, default http://localhost:11434

This produces 3 models x 2 modes x 5 repeats = 30 runs per label set, 60
runs total across both label sets. Each run is saved individually to
outputs/, and all runs are also combined into outputs/all_runs.json.
Retrospective mode is unchanged from the first round and should reproduce
the same 30/30 result, this reruns it mainly for a clean, unambiguous
combined file rather than because the retrospective result is in doubt.

## What to send back

Just the outputs/ directory (or outputs/all_runs.json alone is enough).
Nothing needs to be interpreted or scored on your end, that's the next
step we do together: reading whether each response's stated scope
(exploratory/candidate/validated) actually matches what its own listed
evidence and reasoning steps support. That mismatch, if it shows up, is
the finding.

## Notes

- The script does not do any automatic scoring. Given how central "does
  the agent's own reasoning support its own scope claim" is to the whole
  point of the letter, this needs a human read rather than a keyword match.
- Temperature is left at Ollama's typical default (0.7) rather than 0,
  since greedy/deterministic decoding would understate the variability
  across repeats that the eScience study's own repeated-run design was
  built to capture. This is worth revisiting once we see the outputs, if
  responses are too noisy to compare cleanly.
