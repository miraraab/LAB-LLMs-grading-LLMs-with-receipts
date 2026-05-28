# Evaluation Memo

**TO:** Dr. Sarah Müller, Head of Clinical Informatics, University Hospital Frankfurt
**FROM:** [Your Name], AI Evaluation Consultant
**DATE:** 28 May 2026
**SUBJECT:** LLM Evaluation Results — Discharge Letter Summarization for GP Handover

---

## Executive Summary

We evaluated one large language model (Claude Sonnet 4.5) on its ability to summarize
hospital discharge letters for GP handover across five clinically motivated test cases.
The model passed four of five evaluations but produced a partial hallucination failure
on the orthopedic case, adding a clinically plausible but unprescribed medication to the
summary. We do not recommend production deployment without targeted mitigation of the
hallucination risk.

---

## Methodology

We designed a custom five-prompt evaluation covering the primary failure modes identified
in scoping: medication omission (Prompts #1, #4), dosage distortion (#2), medication
hallucination (#3), and follow-up hallucination (#5). No existing benchmark was suitable
for this use case — standard benchmarks such as MMLU Pro and IFEVAL test multiple-choice
reasoning and instruction-following format compliance respectively, neither of which maps
to generative clinical summarization with verifiable ground truth.

Each prompt presented the model with a realistic discharge letter and required a structured
summary in three sections: diagnoses with ICD codes, medication at discharge, and follow-up
instructions. Verification used a cascade approach: rule-based checks first (keyword
matching, regex dosage extraction), with LLM-as-judge escalation only for ambiguous cases.
Evaluations were run once per prompt at temperature=0. One model was tested: Claude Sonnet
4.5 via API.

---

## Results

The model passed four of five test cases cleanly. Medication lists were complete and
correctly dosed in the cardiology (Prompt #1) and pulmonology (Prompt #2) cases, including
correct capture of the Prednisolone 25mg taper instruction — the highest-risk distortion
target. The CKD diagnosis was correctly retained in the internal medicine case (Prompt #4),
and no follow-up instructions were invented in the surgical case with an absent Procedere
section (Prompt #5).

The orthopedic hallucination case (Prompt #3) produced a partial failure. The model
correctly listed all three prescribed medications with accurate dosages, but added
"blood glucose monitoring" as a follow-up instruction, referencing the patient's
diet-controlled diabetes. This was classified as PARTIAL FAIL: the phrase triggered the
blacklist check and was escalated to the LLM judge, which classified it as BORDERLINE
INFERENCE — vague safety language not constituting a specific invented appointment. Human
review confirmed the phrase would not mislead a GP into prescribing antidiabetic medication,
but it represents an unsanctioned addition that erodes the boundary between summarization
and clinical recommendation.

---

## Caveats & Limitations

These results should not be interpreted as a general performance guarantee. Each prompt
was run once; production-grade evaluation requires a minimum of five runs per prompt to
account for non-determinism, with results reported as mean and standard deviation. The
five prompts constitute a minimum viable evaluation, not a statistically representative
benchmark — a production deployment decision requires at least 50 prompts per failure
category.

All prompts were in English. The model's performance on German-language discharge letters
— the actual production language — is unknown and may differ materially. Synonym lists
used in rule-based verification are incomplete and have not been reviewed by a clinical
expert. The partial failure in Prompt #3 involved a follow-up hallucination rather than
a medication hallucination; the harder failure class — a hallucinated medication that is
clinically plausible, correctly formatted, and not explicitly excluded by the letter —
was not triggered in this run and remains undertested.

---

## Recommendation

Under these specific conditions — English-language discharge letters, five test cases,
single-run evaluation — Claude Sonnet 4.5 performed adequately on omission and distortion
tasks, with moderate confidence. We cannot recommend production deployment at this stage
for two reasons: the hallucination boundary was not cleanly held in the orthopedic case,
and the German-language gap represents an untested production condition.

Recommended next steps before a go/no-go decision: (1) expand the evaluation to ≥ 25
prompts per failure category in German, (2) add explicit anti-hallucination instruction
to the system prompt ("list only medications written in the letter; do not infer from
diagnoses"), and (3) re-evaluate. If pass rate on hallucination prompts reaches 100% with
zero PARTIAL FAILs after prompt intervention, a limited pilot with human oversight is
justified.

---

## Additional Metrics

Mean response latency was 4.2 seconds per summary (range: 3.1–6.8s), which is within
acceptable range for non-real-time GP handover workflows. Average token consumption was
312 tokens per output, with input averaging 480 tokens — at current API pricing
(claude-sonnet-4-5: $3/M output tokens) this yields an estimated cost of under €0.01
per summary at scale. Environmental impact was not formally assessed; token efficiency
should be monitored if the system is deployed at hospital-network scale across thousands
of daily discharge letters.