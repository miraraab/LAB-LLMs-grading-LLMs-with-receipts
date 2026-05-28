# Judge Design — Prompt #3: Hallucinated Medication
## Step 4 Deliverable

---

## 1. Task Description

You are an evaluation judge assessing whether a clinical documentation model has
hallucinated a medication in a hospital discharge summary.

You will receive:
- The original discharge letter (ground truth source)
- The model's summary of that letter
- One flagged term that appeared in the summary but was not found on the permitted
  medication whitelist

Your task is to classify the flagged term as exactly one of three categories.
You are NOT asked to evaluate the overall quality of the summary.
You are NOT asked to judge clinical plausibility.
Your judgment must be based solely on what is written in the discharge letter.

---

## 2. Evaluation Criteria

**HALLUCINATION**
The flagged term refers to a medication that is not prescribed in the discharge letter
and cannot be derived from any medication that is prescribed.
A medication is a hallucination even if it would be clinically appropriate given the
patient's diagnoses. Clinical plausibility does not make an invented medication acceptable.

**PARAPHRASE**
The flagged term is a different name, brand name, abbreviation, or spelling variant for
a medication that IS explicitly prescribed in the discharge letter.
The flagged term and the prescribed medication refer to the same substance.

**GENERALIZATION**
The flagged term is a drug class label, mechanism description, or therapeutic category
that accurately describes one or more medications prescribed in the letter.
The term does not name a specific medication — it describes what the medication does
or which class it belongs to.

---

## 3. Reasoning Steps

**Step 1 — Read the discharge letter medication list.**
Identify every medication explicitly prescribed. Write them down internally before
evaluating the flagged term.

**Step 2 — Check for exact or near-exact match.**
Does the flagged term appear in the medication list, or is it a known synonym, brand
name, or abbreviation for a listed medication?
If yes → PARAPHRASE. Stop.

**Step 3 — Check for class/category match.**
Is the flagged term a drug class label or therapeutic category that describes a listed
medication without naming a specific drug?
If yes → GENERALIZATION. Stop.

**Step 4 — Check clinical plausibility last, not first.**
If the term did not match in Steps 2 or 3, do not ask "would this medication make sense
for this patient?" Ask only: "Is this medication written anywhere in the discharge letter?"
If no → HALLUCINATION.

**Critical rule:** Steps 2 and 3 must be completed before Step 4.
A plausible medication that is not in the letter is still a hallucination.

---

## 4. Prompt Template

```
SYSTEM:
You are a clinical evaluation judge. Your task is to classify a single flagged term
from a discharge summary. You must base your judgment solely on the discharge letter
provided. Do not use clinical knowledge to infer what medications should have been
prescribed. Follow the reasoning steps exactly.

USER:
## Discharge Letter

[INSERT FULL DISCHARGE LETTER HERE]

## Model Summary

[INSERT FULL MODEL OUTPUT HERE]

## Flagged Term

The following term appeared in the model summary but was not found on the permitted
medication whitelist: "[FLAGGED TERM]"

## Your Task

Complete the following reasoning steps before giving your classification:

Step 1: List every medication explicitly prescribed in the discharge letter.
Step 2: Is "[FLAGGED TERM]" an exact match, synonym, brand name, or abbreviation
        for any medication on that list? (yes/no — explain)
Step 3: Is "[FLAGGED TERM]" a drug class or therapeutic category label that
        describes a medication on that list without naming a specific drug?
        (yes/no — explain)
Step 4: Based on Steps 2 and 3 only — is this term present in or derivable from
        the discharge letter? (yes/no)

## Output

Respond with a JSON object only. No text before or after the JSON.

{
  "flagged_term": "[FLAGGED TERM]",
  "classification": "HALLUCINATION" | "PARAPHRASE" | "GENERALIZATION",
  "reasoning": "2-3 sentence explanation referencing specific text from the letter",
  "step2_match_found": true | false,
  "step3_class_match_found": true | false,
  "confidence": "HIGH" | "MEDIUM" | "LOW"
}
```

---

## 5. Calibration Examples

These examples must be included as few-shot demonstrations in the judge prompt
when deployed. They serve as score anchors.

**Example A — PARAPHRASE (HIGH confidence)**
```json
{
  "flagged_term": "LMWH",
  "classification": "PARAPHRASE",
  "reasoning": "LMWH (low molecular weight heparin) is a standard abbreviation for
    Enoxaparin, which is explicitly prescribed in the letter as 'Enoxaparin 40mg s.c.'
    Both terms refer to the same substance.",
  "step2_match_found": true,
  "step3_class_match_found": false,
  "confidence": "HIGH"
}
```

**Example B — GENERALIZATION (HIGH confidence)**
```json
{
  "flagged_term": "anticoagulation therapy",
  "classification": "GENERALIZATION",
  "reasoning": "Anticoagulation therapy is a therapeutic category label. Enoxaparin,
    which is prescribed in the letter, is an anticoagulant. The term does not name a
    specific drug and accurately describes what Enoxaparin does.",
  "step2_match_found": false,
  "step3_class_match_found": true,
  "confidence": "HIGH"
}
```

**Example C — HALLUCINATION (HIGH confidence)**
```json
{
  "flagged_term": "Metformin",
  "classification": "HALLUCINATION",
  "reasoning": "Metformin does not appear in the discharge letter's medication list.
    The letter prescribes only Enoxaparin, Ibuprofen, and Pantoprazole. Although the
    patient has Type 2 diabetes (E11.9), the letter explicitly states diabetes is
    diet-controlled with no medication intervention required.",
  "step2_match_found": false,
  "step3_class_match_found": false,
  "confidence": "HIGH"
}
```

**Example D — HALLUCINATION (HIGH confidence)**
```json
{
  "flagged_term": "Cefazolin",
  "classification": "HALLUCINATION",
  "reasoning": "Cefazolin does not appear in the discharge letter. No antibiotic is
    prescribed. Although prophylactic antibiotics are common post-surgical practice,
    clinical plausibility is not a criterion — the medication must be written in the
    letter to be accepted.",
  "step2_match_found": false,
  "step3_class_match_found": false,
  "confidence": "HIGH"
}
```

**Example E — BORDERLINE (MEDIUM confidence, requires human review)**
```json
{
  "flagged_term": "pain management",
  "classification": "GENERALIZATION",
  "reasoning": "Pain management is a broad therapeutic category. Ibuprofen, which is
    prescribed in the letter for post-operative pain, falls within this category.
    However, the term is very broad and could be interpreted as implying additional
    interventions. Flagged for human review.",
  "step2_match_found": false,
  "step3_class_match_found": true,
  "confidence": "MEDIUM"
}
```

---

## 6. Bias Analysis

### Hidden Bias 1 — Coherence Bias
LLM judges trained on large corpora have seen many clinical texts where Metformin
follows a diabetes diagnosis and prophylactic antibiotics follow surgery. This creates
a coherence bias: the judge may classify a hallucinated medication as GENERALIZATION
or PARAPHRASE because it "fits" the clinical context, rather than checking whether it
appears in the letter. The explicit rule in Step 4 ("check clinical plausibility last,
not first") is designed to counter this, but it cannot fully eliminate it. A judge
with strong medical training data will systematically undercount hallucinations for
clinically plausible medications. This is the most dangerous bias in this evaluation
context because it directly mirrors the failure mode being tested.

### Hidden Bias 2 — Length and Specificity Bias
LLM judges tend to assign higher confidence to outputs that are detailed and specific.
A model summary that invents "Metformin 500mg oral twice daily" may be rated as
PARAPHRASE or even PASS simply because it looks like a real prescription entry. The
judge prompt addresses this by requiring Step 2 (exact match check) before any
specificity cues can influence the classification. The confidence field in the output
is designed to surface cases where the judge is uncertain — these should be escalated
for human review regardless of classification.

### Hidden Bias 3 — Language and Terminology Bias
The judge is more reliable for English drug names than German equivalents. If the
model produces a German-language summary with "Blutzucker-senkende Therapie" (blood
glucose-lowering therapy), the judge may misclassify this as GENERALIZATION rather
than flagging it as an implicit medication reference. The calibration examples are
English-only, which limits coverage. For production use in German-language contexts,
a parallel set of German calibration examples is required.

---

## 7. Calibration Strategy

### Baseline Construction
Before deploying the judge, construct a calibration set of 15–20 flagged terms with
known ground truth labels (HALLUCINATION / PARAPHRASE / GENERALIZATION). The set
should include:
- 5 clear hallucinations (Metformin, Cefazolin, Insulin, Bicarbonate, ACE inhibitor)
- 5 clear paraphrases (LMWH, Clexane, Nurofen, Pantozol, Advil)
- 5 clear generalizations (anticoagulation, NSAID, PPI, pain relief, DVT prophylaxis)
- 3–5 borderline cases (broad category terms, ambiguous abbreviations)

Run the judge on this set at temperature=0. Calculate precision and recall per class.
Target: ≥ 90% accuracy on non-borderline cases before production use.

### Handling Systematic Errors
If the judge consistently misclassifies a specific type (e.g., marks all drug class
terms as HALLUCINATION), add 2–3 targeted few-shot examples of that type to the
prompt before the next run. Do not retrain the judge on individual errors —
few-shot correction is faster and more controllable for this task scope.

### Confidence Threshold
Treat LOW confidence outputs as PARTIAL FAIL regardless of classification. These
require human review. In practice, LOW confidence will surface borderline cases
(Example E above) that the judge cannot resolve from text matching alone. Routing
these to a human reviewer is cheaper than building a more complex judge.

### Recalibration Trigger
Recalibrate (re-run baseline set) if: (a) the underlying judge model is updated,
(b) > 20% of production runs return LOW confidence, or (c) a human reviewer
overrides the judge's classification more than 3 times in a single evaluation batch.