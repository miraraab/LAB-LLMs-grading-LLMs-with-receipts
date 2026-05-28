# Reflection
## Step 6 Deliverable

---

## Question 1: What would change if your client's data was in French?

The most obvious change is model performance: large language models are trained on
significantly less French-language medical text than English, which means lower
reliability on clinical terminology, abbreviations, and discharge letter conventions
specific to the French healthcare system. A model that correctly captures "Enoxaparin
40mg s.c." in English may paraphrase, abbreviate, or omit it differently in French —
and the performance gap is not predictable without testing.

The less obvious but more serious problem is that the entire evaluation design breaks.
Every synonym list, normalization list, and blacklist in the verification layer is
English. "Nachsorge" has no entry. "Pantoprazole" is the same word, but "Prednisolone"
may appear as "Prednisone" in French prescriptions — a different drug at a different
standard dosage. The regex patterns assume English sentence structure. The LLM judge
was calibrated on English examples. A French evaluation is not a translation of this
design — it is a rebuild from scratch, starting with French-language discharge letters
reviewed by a clinician familiar with French prescription conventions.

The third problem is ground truth verification. Who confirms that the French test cases
are clinically correct? The Prednisolone taper protocol, the CKD contraindication
logic, the post-surgical hallucination traps — all of these need review by someone who
knows both French medical practice and French drug naming conventions. This is not a
translation task. It requires domain expertise in a different clinical context.

---

## Question 2: Your client asks "is this model AGI-level?" — how do you respond?

The honest answer is that the question cannot be answered, and the reason is worth
explaining. "AGI-level" has no agreed definition — not in research, not in clinical
practice, not in this evaluation. If it means "better than a human doing the same
task", you would need to define which human, under which conditions, with how much
time, and with access to what information. A GP reading a discharge letter in 30
seconds is a different baseline than a clinical pharmacist spending 10 minutes. The
model would likely outperform the former on medication completeness and underperform
the latter on clinical judgment.

More practically: the evaluation we ran tests five failure modes across five cases.
It does not test rare diagnoses, multi-page letters, handwritten annotations,
conflicting medication lists, or any of the edge cases that constitute real-world
clinical complexity. A model that passes this evaluation has demonstrated minimum
viable performance on a narrow slice of the task — not general capability. Claiming
AGI-level performance from five test cases would be statistically indefensible and
professionally irresponsible.

The right response to the client is: "That question is not answerable with this
evaluation, and it may not be the right question. The question we can answer is:
under these conditions, for this specific task, does the model perform well enough
to support a limited pilot with human oversight? Based on current results, not yet —
but we have a clear path to get there."

---

## Question 3: What is the one thing you could not evaluate without a human, and why?

Clinical adequacy of borderline outputs. Rule-based checks and LLM judges can
determine whether a medication is present, whether a dosage matches a number, and
whether a term appears on a whitelist. What they cannot determine is whether a
summary that is technically correct is clinically safe for a specific patient in a
specific context. The Partial Fail in Prompt #3 — "blood glucose monitoring" added
as a follow-up instruction — is the clearest example: the phrase triggered no rule,
the LLM judge classified it as BORDERLINE INFERENCE, and only a human reviewer could
confirm that a GP receiving this summary would not act on it incorrectly.

This class of judgment requires integrating clinical knowledge, contextual reading,
and an understanding of how a real GP interprets a summary under time pressure. An
LLM judge trained on medical text may have the vocabulary but not the situated
judgment — it cannot model what a GP does when they see a summary that implies
monitoring for a condition that was explicitly managed without medication. A rule
cannot catch implications. A judge can classify surface patterns. Neither can replace
the question: "would a competent clinician act safely on the basis of this summary?"

In practice, this means any production evaluation of this system requires a clinical
reviewer for at least a sample of outputs — not because automation fails entirely,
but because the failure mode that matters most (a GP taking the wrong action based
on a plausible but incorrect summary) is only detectable by someone who understands
both the clinical stakes and the GP's decision-making process. That is irreducibly
human judgment.