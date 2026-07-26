# Prompts

Both prompts share the same scope-qualifier definitions, given to the agent
in each prompt so it applies them consistently:

- **exploratory**: the evidence is preliminary or hypothesis-generating. It
  has not yet reached an accepted statistical threshold, or it has not been
  independently replicated, or both.
- **candidate**: the evidence has reached an accepted statistical threshold
  and been independently replicated, but the underlying causal or
  functional mechanism has not been established. The finding is a
  candidate for further mechanistic study, not a confirmed cause.
- **validated**: the evidence has reached an accepted statistical threshold,
  been independently replicated, AND the causal or functional mechanism
  has been directly demonstrated (not just proposed as plausible).

These three definitions are our own operational definitions for this study,
written to be self-contained so the agent does not need outside domain
convention to apply them.

---

## Prospective prompt

```
You are a geneticist reviewing preliminary results from a genome-wide
association study (GWAS) of biliary atresia (BA), a rare pediatric liver
disease. You are given only the evidence below, from a single discovery
cohort. No replication cohort has been analyzed yet, and no functional or
mechanistic follow-up study exists yet. Do not use any outside knowledge
you may have about this gene, locus, or disease. Base your answer only on
the evidence provided.

Scope qualifier definitions:
- exploratory: preliminary or hypothesis-generating; has not reached an
  accepted statistical threshold, has not been independently replicated,
  or both.
- candidate: reaches an accepted statistical threshold and has been
  independently replicated, but the causal or functional mechanism is not
  established.
- validated: reaches an accepted statistical threshold, has been
  independently replicated, AND the causal or functional mechanism has
  been directly demonstrated.

Evidence:
<insert contents of evidence_discovery_cohort.json here>

Respond in exactly this structure:
1. Evidence used: list the IDs of the evidence items you relied on.
2. Reasoning steps: a numbered list of the inferential steps connecting
   that evidence to your conclusion.
3. Claim: a single sentence stating your conclusion about EFEMP1 and BA
   susceptibility.
4. Scope: exactly one of exploratory, candidate, or validated, with one
   sentence justifying the choice.
```

---

## Retrospective prompt

```
Below is an excerpt from the Results and Discussion sections of a published
genetics paper on biliary atresia (BA). Read it and reconstruct the
authors' own reasoning. Base your answer only on what is stated in the text
below, not on outside knowledge of this gene or locus.

Scope qualifier definitions:
- exploratory: preliminary or hypothesis-generating; has not reached an
  accepted statistical threshold, has not been independently replicated,
  or both.
- candidate: reaches an accepted statistical threshold and has been
  independently replicated, but the causal or functional mechanism is not
  established.
- validated: reaches an accepted statistical threshold, has been
  independently replicated, AND the causal or functional mechanism has
  been directly demonstrated.

Text:
<insert contents of reasoning_trace_retrospective.md here>

Respond in exactly this structure:
1. Evidence used: list, in your own words, the findings the authors treated
   as evidence for their central claim.
2. Reasoning steps: a numbered list of the inferential steps connecting
   that evidence to the authors' claim, as you understand them from the
   text.
3. Claim: restate the authors' central claim in a single sentence.
4. Scope: exactly one of exploratory, candidate, or validated, with one
   sentence justifying the choice based on what the text actually
   supports.
```
