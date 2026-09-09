# MODEL_EVAL.md

# Quiver Workbench — Model Evaluation Standard

## 1. Purpose

This project is a private evaluation workbench for answering one practical question:

> **Which AI model is most reliable for analyzing niche cat-food market trends through the lens of behavioral economics?**

The objective is **model selection and continuous regression testing**, not finding a model that "passes" a benchmark.

The benchmark should evolve from real failures and real market-analysis tasks. Every useful failure becomes a new arrow in the quiver.

---

## 2. Evaluation Target

The primary task is:

```text
Market signals
    ↓
Evidence collection
    ↓
Trend identification
    ↓
Niche opportunity hypothesis
    ↓
Behavioral-economic explanation
    ↓
Commercial implication
    ↓
Uncertainty / confidence
```

A strong model must do more than identify products that appear popular.

It should distinguish:

- popularity vs. genuine trend
- trend vs. temporary spike
- demand vs. seller activity
- correlation vs. causal explanation
- stated preference vs. revealed preference
- search/social attention vs. purchase behavior
- high sales vs. attractive opportunity
- niche growth vs. crowded competition

---

## 3. Domain Scope

Initial suite:

```text
suites/catfood/
```

Primary domain:

> Niche cat-food market analysis using behavioral economics.

Potential subdomains:

- functional cat food
- wet food
- freeze-dried / air-dried
- supplements / toppers
- urinary / digestive / sensitive-stomach positioning
- premiumization
- natural / clean-label positioning
- convenience products
- treats
- multi-cat households
- senior-cat products
- kitten products
- owner anxiety / reassurance
- anthropomorphism
- health signaling
- loss aversion
- social proof
- novelty / curiosity
- habit formation
- price anchoring
- bundle effects
- trust and authority

The suite must not assume that any one of these is a trend before evidence supports it.

---

## 4. What "Good" Looks Like

A high-quality analysis should:

### Evidence

- use current, relevant sources
- distinguish primary from secondary evidence
- provide traceable citations
- avoid fabricated sources
- separate observed facts from interpretation

### Market analysis

- identify a concrete niche
- explain why the signal matters
- examine growth, demand, competition and monetization
- distinguish durable trends from temporary effects
- identify counter-evidence

### Behavioral economics

Connect observations to mechanisms such as:

- loss aversion
- status quo bias
- social proof
- scarcity
- anchoring
- framing
- endowment effect
- present bias
- choice architecture
- commitment / consistency
- affect heuristic
- uncertainty reduction
- mental accounting
- identity signaling
- anthropomorphism

The model must not simply attach a behavioral-economics label to an observation. It should explain the mechanism:

```text
Observed behavior
→ behavioral mechanism
→ predicted consumer behavior
→ commercial implication
```

### Commercial usefulness

The final analysis should help answer:

```text
Should we enter this niche?
For whom?
With what product positioning?
At what price logic?
Against which competitors?
With what evidence?
What could make the thesis wrong?
```

---

## 5. Evaluation Principles

### 5.1 Real tasks over synthetic tasks

Prioritize:

- actual Shopee/Lazada observations
- actual product listings
- actual review data
- actual price history
- actual search/social signals
- real competitor sets
- real product pages
- real market questions

Synthetic tasks are useful primarily for targeted failure modes.

### 5.2 Evidence before narrative

A compelling story is not sufficient.

The evaluator should ask:

```text
What is observed?
What is inferred?
What is hypothesized?
What is unknown?
```

### 5.3 Hold out information when possible

If the evaluator already knows an outcome, hide it from the model and compare the prediction afterward.

Use holdouts to test:

- trend direction
- likely winning attributes
- consumer segment
- price band
- product positioning
- likely demand drivers

### 5.4 Trap pattern matching

Create cases where the obvious answer is wrong.

Examples:

- a product has huge sales but declining demand
- a category has many sellers but weak buyer economics
- reviews are numerous but mostly low-intent
- a viral product has no durable repeat purchase
- a "premium" product is actually price-anchored discounting
- social engagement is high but commercial conversion is weak

### 5.5 Reproducibility

Every case should contain:

- exact question
- data snapshot / fixture
- date
- expected reasoning constraints
- scoring rubric
- verification method

---

## 6. Four Evaluation Mechanisms

| Mechanism | Purpose |
|---|---|
| Verifiable | Claims must be traceable to evidence |
| Holdout | Test whether the model can infer hidden outcomes |
| Computable | Test calculations and quantitative reasoning |
| Trap | Detect attractive but incorrect narratives |

Every suite should contain all four where practical.

---

## 7. Core Rubric

Each dimension is scored:

```text
0 = absent / wrong
1 = shallow / partially useful
2 = correct and practically useful
```

Default dimensions:

| Dimension | What to inspect |
|---|---|
| Evidence quality | Sources, freshness, traceability |
| Trend detection | Signal vs. noise |
| Market reasoning | Demand, competition, economics |
| Behavioral economics | Mechanism quality |
| Causal discipline | Fact/inference separation |
| Quantitative accuracy | Prices, rates, calculations |
| Counter-evidence | Attempts to falsify thesis |
| Commercial usefulness | Actionable niche decision |
| Uncertainty | Confidence and limitations |
| Instruction following | Follows requested format/scope |

Default maximum:

```text
20 points
```

Do not use a single overall score without preserving dimension-level scores.

---

## 8. Critical Failure Gates

A case can fail regardless of total score if it contains:

- fabricated citation
- fabricated numerical evidence
- materially incorrect calculation
- unsupported claim presented as fact
- failure to identify obvious contradictory evidence
- severe hallucination
- recommendation based on data that does not support the conclusion
- deliberate instruction to ignore evidence
- severe sycophancy when the case is designed to test contradiction

---

## 9. Failure Taxonomy

Use one primary failure:

```text
FABRICATED_SOURCE
NUMERICAL_ERROR
EVIDENCE_MISREAD
TREND_FALSE_POSITIVE
TREND_FALSE_NEGATIVE
CAUSALITY_ERROR
BEHAVIORAL_LABEL_ONLY
BEHAVIORAL_MECHANISM_ERROR
COMPETITION_BLINDNESS
ECONOMIC_REASONING_ERROR
SYCHOPHANCY
CONFIDENCE_ERROR
HOLDOUT_FAILURE
TRAP_FAILURE
INSTRUCTION_FAILURE
CONTEXT_FAILURE
TOOL_FAILURE
OTHER
```

Note: `SYCHOPHANCY` is retained as the project label if that spelling is used by existing cases; otherwise prefer `SYCOPHANCY` only if the suite standard is explicitly changed. Do not silently rename existing historical categories.

Severity:

```text
P0_CRITICAL
P1_HIGH
P2_MEDIUM
P3_LOW
```

---

## 10. Sycophancy Tests

Every suite should eventually contain cases that deliberately provide a plausible but false premise.

Example:

```text
Premise:
"Freeze-dried cat food is clearly the fastest-growing category,
so we should enter it immediately."

Task:
Evaluate the premise using the supplied evidence.
```

A good model should:

1. challenge the premise when evidence disagrees
2. identify missing evidence
3. distinguish the premise from the conclusion
4. avoid agreeing merely because the user sounds confident

---

## 11. Citation Integrity

For every important external claim:

```text
Claim
→ Source
→ Source date
→ What the source actually establishes
```

The evaluator should verify citations manually during the initial phase.

A citation that exists but does not support the claim is a failure.

A plausible-looking URL that does not exist is a critical failure.

---

## 12. Data Freshness

Because the target is market trends, every case should record:

```yaml
data:
  snapshot_date:
  collection_period:
  sources:
```

Do not compare model outputs across different market snapshots as if they were the same task.

---

## 13. Model Comparison

The primary purpose is comparing models.

Record:

```text
model
version
provider
date
suite version
case version
run number
```

Compare:

- total score
- dimension scores
- hard-gate failures
- fabricated-source rate
- numerical-error rate
- trend-detection accuracy
- holdout accuracy
- trap accuracy
- behavioral-economics quality
- commercial usefulness

Do not declare a model superior from average score alone.

---

## 14. Repeated Runs

For tasks with meaningful stochastic variation:

```text
repeat 3 = minimum useful signal
repeat 5 = stronger signal
repeat 10+ = useful for statistical comparison
```

Use repeated runs particularly for:

- open-ended market analysis
- niche discovery
- trend interpretation
- recommendation generation

---

## 15. Human Scoring First

Initial phase:

> **Score manually. Do not introduce LLM-as-judge until approximately 30–40 answers have been read and the evaluator has a stable understanding of what "good" looks like.**

This is important because the rubric itself will evolve after seeing real model behavior.

Later, an LLM judge may assist with:

- repetitive scoring
- consistency checks
- candidate ranking

But high-impact failures should remain human-verifiable.

---

## 16. Provider Feedback

When a model fails, create provider-facing feedback from the same evidence.

Feedback must contain:

```text
Context
Exact task
Model/version
Expected behavior
Observed behavior
Evidence
Failure category
Severity
Reproduction
Comparison with previous model
Suggested improvement
```

Avoid:

```text
"This model is bad at market research."
```

Prefer:

```text
"In EVAL-CAT-007 the model treated seller count as evidence
of consumer demand. The fixture shows seller count increasing
while review velocity and estimated sales decline. The model
therefore classified increased competition as increased demand."
```

The second form is actionable and reproducible.

---

## 17. Data Collection Is the Bottleneck

The harness is not the primary source of evaluation quality.

For this suite:

> **Good market fixtures are more valuable than a sophisticated runner.**

Prioritize building:

```text
real product snapshots
real prices
review samples
seller counts
ranking observations
search signals
competitor sets
time-series snapshots
```

The first milestone should therefore prioritize the Shopee/Lazada data collection pipeline and stable fixtures.

---

## 18. Real Failure → New Evaluation Case

Core rule:

```text
Model fails in real work
        ↓
Capture exact failure
        ↓
Minimize reproduction
        ↓
Add evaluation case
        ↓
Run against all candidate models
        ↓
Keep permanently if useful
```

Target:

> Within two months, at least half of the cases should originate from failures or observations encountered during actual work rather than cases invented in advance.

---

## 19. Recommended Suite Structure

```text
suites/
└── catfood/
    ├── SUITE.md
    ├── cases/
    │   ├── E01-trend-detection.json
    │   ├── E02-source-verification.json
    │   ├── E03-price-analysis.json
    │   ├── E04-behavioral-mechanism.json
    │   ├── E05-sycophancy.json
    │   └── ...
    ├── fixtures/
    └── models.json
```

Shared harness:

```text
harness/run.py
```

Results:

```text
results/
```

Scratch work:

```text
scratch/
```

---

## 20. Baseline Protocol

For the first baseline:

1. Freeze the suite version.
2. Freeze fixture snapshots.
3. Record exact model IDs.
4. Run every case.
5. Repeat open-ended cases where practical.
6. Manually score every answer.
7. Record failure taxonomy.
8. Save raw outputs.
9. Commit `scores.json`.
10. Record the baseline date.

This becomes the reference point for future model releases.

---

## 21. Golden Rule

> **Do not optimize for the model that gives the most convincing market story. Optimize for the model that most reliably turns evidence into a correct, behaviorally grounded, commercially useful thesis — while clearly exposing uncertainty and being willing to say "the evidence does not support this."**
