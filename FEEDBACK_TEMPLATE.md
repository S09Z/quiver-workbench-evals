# FEEDBACK_TEMPLATE.md

# Model Provider Feedback — Cat-Food Niche Market Evaluation

## 1. Summary

**Provider:** `<provider>`  
**Model:** `<model/version>`  
**Evaluation:** `<CAT-E##>`  
**Run:** `<RUN-ID>`  
**Suite version:** `<version>`  
**Result:** `PASS | FAIL | PARTIAL`  
**Severity:** `P0 | P1 | P2 | P3`  
**Failure:** `<primary category>`

### One-line finding

```text
<Specific, reproducible statement of what the model did incorrectly or unusually well.>
```

---

## 2. Why This Evaluation Matters

### Real-world task

```text
We are evaluating AI models for niche cat-food market analysis
in Thailand, with behavioral economics used to explain consumer
behavior and identify commercially useful opportunities.
```

### Decision affected

```text
<What business decision this analysis informs.>
```

---

## 3. Exact Evaluation

### Prompt

```text
<Exact prompt sent to the model>
```

### Data snapshot

```text
Snapshot date:
Collection period:
Marketplace:
Geography:
```

### Model

```text
Provider:
Model:
Exact model ID:
Version:
Settings:
```

---

## 4. Expected Reasoning

The model should have:

1. Identified the relevant market signal.
2. Distinguished observation from interpretation.
3. Tested alternative explanations.
4. Connected behavior to a plausible behavioral-economic mechanism.
5. Considered competition and commercial economics.
6. Stated uncertainty proportional to evidence.
7. Avoided unsupported or fabricated claims.

---

## 5. Observed Behavior

### What happened?

```text
<Describe only what can be demonstrated from the response.>
```

### Critical excerpt

```text
<Short excerpt from model output>
```

### Evidence

```text
<Fixture row / source / calculation / test result>
```

---

## 6. Expected vs. Actual

| | Expected | Actual |
|---|---|---|
| Trend interpretation | | |
| Evidence use | | |
| Behavioral mechanism | | |
| Quantitative reasoning | | |
| Counter-evidence | | |
| Commercial implication | | |
| Uncertainty | | |

---

## 7. Failure Classification

**Primary:** `<category>`  
**Secondary:** `<category>`  
**Severity:** `<P0/P1/P2/P3>`  
**Cause:** `MODEL | DATA | TOOL | EVALUATOR | UNKNOWN`

### Why this is a model failure

```text
Explain why the available data/context/tool behavior does not
adequately explain the failure.
```

If it is not clearly a model failure:

```text
Do not force attribution. Mark the cause as UNKNOWN or another
appropriate category.
```

---

## 8. Behavioral-Economics Specific Analysis

Use this section whenever the failure concerns consumer psychology.

### Model's claim

```text
<e.g. "Consumers buy this because of loss aversion.">
```

### Problem

```text
<Explain whether the mechanism is actually supported.>
```

### What a stronger analysis would do

```text
Observation
→ behavioral mechanism
→ predicted consumer behavior
→ commercial implication
→ evidence that could falsify the mechanism
```

This prevents "behavioral economics" from becoming a collection of labels attached to arbitrary market observations.

---

## 9. Citation / Evidence Audit

| Claim | Source provided | Source exists | Source supports claim | Result |
|---|---|---|---|---|
| | | | | |

Flag:

```text
FABRICATED_SOURCE
SOURCE_DOES_NOT_SUPPORT_CLAIM
STALE_SOURCE
MISSING_SOURCE
```

---

## 10. Quantitative Audit

### Model calculation

```text
<model's calculation>
```

### Independent calculation

```text
<correct calculation>
```

### Difference

```text
<difference and impact>
```

---

## 11. Regression Comparison

### Previous model

```text
<model/version>
```

### Current model

```text
<model/version>
```

| Metric | Previous | Current | Delta |
|---|---:|---:|---:|
| Total score | | | |
| Evidence quality | | | |
| Trend detection | | | |
| Behavioral economics | | | |
| Quantitative accuracy | | | |
| Commercial usefulness | | | |
| Hard-gate failures | | | |

### Regression status

```text
IMPROVED
REGRESSED
UNCHANGED
MIXED
```

### Interpretation

```text
<Explain the difference and whether it is reproducible.>
```

---

## 12. Minimal Reproduction

```text
Fixture:
<fixture/version>

Prompt:
<minimal prompt>

Expected:
<expected behavior>

Actual:
<actual behavior>

Verification:
<verification command/process>

Result:
<result>
```

The goal is to make the failure easy for the model provider to investigate.

---

## 13. Recommended Improvement

Do not write:

```text
Improve market research.
Improve reasoning.
Be less hallucinating.
```

Write behavior-level guidance:

```text
When market evidence contains competing signals, explicitly
separate demand indicators from supply/activity indicators.
Do not infer consumer demand from seller count alone.

Before concluding that a niche is growing, compare at least
two independent demand signals and identify evidence that could
falsify the growth hypothesis.
```

---

## 14. Provider-Facing Report

### Title

```text
[<P-level>] <Short reproducible issue>
```

### Report

```text
We found a reproducible issue in <model/version> while evaluating
niche cat-food market analysis.

Context:
<real-world context>

Task:
<exact task>

Expected:
<expected behavior>

Observed:
<actual behavior>

Evidence:
<fixture/source/calculation>

Impact:
<business/research impact>

Failure category:
<category>

Reproduction:
<minimal reproduction>

Comparison:
<previous model behavior>

Suggested improvement:
<concrete model behavior>
```

---

## 15. What Worked

Provider feedback should also identify successful behavior.

```text
The model correctly:
- ...
- ...
- ...
```

This prevents the report from becoming an unbalanced list of complaints.

---

## 16. Final Recommendation

```text
SHIP
SHIP_WITH_CAVEATS
HOLD
REGRESSION
INVESTIGATE
```

### Reason

```text
<Concise evidence-based conclusion>
```

---

## 17. Golden Rule

> **The goal is not to find the model that tells the most convincing story about the cat-food market. The goal is to find the model that most reliably converts market evidence into a defensible behavioral-economic hypothesis and a useful commercial decision — while knowing when the evidence is insufficient.**
