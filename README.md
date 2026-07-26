# GWAS interpretive reproducibility use case

Source paper: Chen, Gilbert, Grochowski, et al. (2018), "A genome-wide
association study identifies a susceptibility locus for biliary atresia on
2p16.1 within the gene EFEMP1", PLOS Genetics 14(8):e1007532. Open access,
CC0.

## What this tests

**Prospective mode**: the agent sees only the discovery-cohort statistics
(evidence_discovery_cohort.json), with no mention that a replication study
exists. The evidence supports "suggestive," not "candidate" or "validated."
An agent that reports the association as statistically confirmed from
discovery-only data is overclaiming on statistical grounds.

**Retrospective mode**: the agent sees the paper's own Results and
Discussion text (reasoning_trace_retrospective.md), including the
successful replication and meta-analysis. The statistical claim (genome-
wide significant association) is now genuinely earned. The authors
themselves still call EFEMP1 a "candidate susceptibility gene," explicitly
say the causal mechanism is unclear and other genes might be involved. An
agent that restates this as a confirmed or causal gene for BA is
overclaiming on causal/mechanistic grounds, a different failure mode from
the prospective one, even though both are "overclaiming."

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

```
python3 run_study.py --repeats 5
```

Options:
- `--models` : which models to run, default llama3:latest mistral:latest
- `--repeats` : repetitions per model per mode, default 5
- `--temperature` : sampling temperature, default 0.7
- `--host` : Ollama host, default http://localhost:11434

This produces 2 models x 2 modes x 5 repeats = 20 runs by default. Each run
is saved individually to outputs/, and all runs are also combined into
outputs/all_runs.json.

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
