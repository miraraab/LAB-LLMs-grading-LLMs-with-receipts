# Benchmark Audit
## Client Scenario: Hospital Discharge Letter Summarization for GPs

**Scenario:** A hospital wants to automatically summarize discharge letters for handover to general practitioners (GPs). Priority: medication must be captured completely and with correct dosages. Critical failure modes are missing medications (omission) and incorrect dosages (distortion) — both are hard to detect without access to the original document.

---

## Benchmark 1: MMLU Pro (2024)

**Source:** [MMLU-Pro — NeurIPS 2024](https://arxiv.org/abs/2406.04127)

### Why it seemed relevant
MMLU Pro contains a medical subset that tests whether models possess the medical factual knowledge required to correctly handle dosage information. At first glance, a model that scores well on medical questions should theoretically produce more accurate medication summaries.

### Contamination Risk
**🔴 High**
MMLU Pro is a direct extension of MMLU (2021), whose questions have been publicly available for years. Despite moving from 4 to 10 answer options to reduce guessing, the underlying questions and answer patterns are well-known and likely present in training corpora of frontier models.

### Saturation Risk
**🔴 High**
By early 2026, top models cluster around 90% on MMLU Pro (e.g., Gemini 3 Pro 90.1%), making the benchmark nearly ineffective for differentiating between leading models. The spread between top performers is too narrow for reliable ranking.

### Format
- [x] Multiple Choice

### Critical Issue for This Use Case
The multiple-choice format fundamentally mismatches the task. A model can correctly identify the right answer from a predefined list while being poor at generating that same answer from scratch. Our task requires *generation and extraction*, not *selection*. MMLU Pro measures knowledge recall — not summarization fidelity or omission detection.

### Verdict
**❌ Reject**

MMLU Pro tests the wrong capability for this scenario. Even perfect medical knowledge does not prevent a model from omitting a medication or hallucinating a dosage in free-form generation. The benchmark is also saturated and contaminated, making it useless for model differentiation.

---

## Benchmark 2: IFEVAL (2023)

**Source:** [IFEval — arxiv 2311.07911](https://arxiv.org/abs/2311.07911)

### Why it seemed relevant
Discharge letter summaries have strict structural requirements: they must contain a medication section, follow a defined format, and include specific fields (diagnosis, follow-up appointments, dosages). IFEVAL tests whether models follow verifiable natural language instructions — e.g., "include a section titled Medication" or "list at least 3 items."

### Contamination Risk
**🟡 Medium**
IFEVAL's verifiable instructions (e.g., word count, keyword inclusion) are rule-based and less susceptible to classical contamination. However, the benchmark has been public since 2023 and is widely used in model training pipelines for instruction-tuning.

### Saturation Risk
**🟡 Medium**
Frontier models perform well on IFEVAL, but the benchmark can be adapted with domain-specific instructions that are unlikely to be saturated.

### Format
- [x] Free-form text (with rule-based verification)

### Critical Issue for This Use Case
IFEVAL tests **format compliance**, not **content accuracy**. A model can perfectly produce a structured "Medication" section — and still hallucinate a drug name or omit a critical dosage. These are orthogonal problems. Structure is a *necessary but not sufficient* condition for a correct summary.

### Verdict
**⚠️ Adapt**

Useful as one layer of evaluation — verifying that the output contains the required sections and structure. Must be combined with content-level verification (ground truth comparison or LLM-as-judge for accuracy and completeness). Do not use as a standalone benchmark.

**Adaptation strategy:** Replace generic IFEVAL instructions with domain-specific ones, e.g.:
- "The summary must include a section titled 'Current Medication'"
- "Each medication must be listed with name, dosage, and frequency"
- "The summary must not exceed 300 words"

---

## Benchmark 3: Needle in a Haystack (2023)

**Source:** [NIAH — github.com/gkamradt](https://github.com/gkamradt/LLMTest_NeedleInAHaystack)

### Why it seemed relevant
Discharge letters can be long, multi-page documents. NIAH tests whether a model can locate specific information (a "needle") buried within a long context (the "haystack"). Intuitively, finding the medication list in a long clinical document seems like exactly this task.

### Contamination Risk
**🟡 Medium**
The original NIAH is publicly available and well-known. The specific test structure (insert a fact, ask the model to retrieve it) is widely replicated. Frontier models are likely optimized for this pattern.

### Saturation Risk
**🔴 High**
The lesson explicitly marks NIAH as saturated (confirmed by RULER 2024). Most frontier models now pass standard NIAH tests with near-perfect scores, making it useless for differentiation.

### Format
- [x] Free-form text (retrieval)

### Critical Issue for This Use Case
NIAH tests retrieval of **a single, predefined fact**. Our problem requires **complete extraction of all medications** — a fundamentally different task. A model can successfully retrieve one needle while missing two others. Omission detection across multiple items is not what NIAH was designed to test.

Additionally, NIAH uses synthetic documents, not real clinical text with the formatting irregularities and medical terminology of actual discharge letters.

### Verdict
**❌ Reject**

Too simple, saturated, and structurally mismatched. Single-fact retrieval ≠ complete multi-item extraction. Does not test the failure modes we care about (omission, distortion).

---

## Summary

| Benchmark | Year | Contamination | Saturation | Verdict | Core Problem |
|---|---|---|---|---|---|
| MMLU Pro | 2024 | 🔴 High | 🔴 High | ❌ Reject | MC format ≠ generation task |
| IFEVAL | 2023 | 🟡 Medium | 🟡 Medium | ⚠️ Adapt | Format ≠ content accuracy |
| Needle in a Haystack | 2023 | 🟡 Medium | 🔴 High | ❌ Reject | Single retrieval ≠ completeness |

### Key Takeaway
No standard benchmark from the lesson adequately covers this use case. This is expected: the scenario requires evaluating **free-form summarization with multi-item completeness and factual accuracy** — a combination that existing benchmarks do not test directly. A custom evaluation dataset is necessary (→ Step 3).