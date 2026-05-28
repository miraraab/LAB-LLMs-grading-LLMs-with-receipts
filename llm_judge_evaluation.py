"""
LLM-as-Judge Evaluation — Prompt #3: Hallucinated Medication
Lab: LLMs Grading LLMs — with Receipts

Judge model: gpt-4o-mini (temperature=0)
Cascade: Completeness Gate → Whitelist → LLM-Judge (escalation only)
"""

import json
import os
import re
import time

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

JUDGE_MODEL = "gpt-4o-mini"
COST_INPUT_PER_1M = 0.15   # USD
COST_OUTPUT_PER_1M = 0.60  # USD

DISCHARGE_LETTER = """
Patient: Male, 74 years
Admission: 05.05.2026 | Discharge: 14.05.2026
Treating physician: Dr. P. Schneider, Orthopedics
Contact for queries: +49 69 6301-0

DIAGNOSES
1. Right hip osteoarthritis, end-stage (M16.1)
2. Status post total hip replacement (right), 09.05.2026
3. Type 2 diabetes mellitus, diet-controlled (E11.9)
4. Mild renal insufficiency (N18.2)

COURSE
Elective total hip arthroplasty performed without intraoperative complications.
Physiotherapy initiated on postoperative day 1. Wound healing unremarkable at discharge.
Blood glucose monitored daily — stable without medication intervention.
Renal function monitored, stable throughout.

MEDICATION AT DISCHARGE
1. Enoxaparin 40mg s.c. – 0-0-1 (once daily, 28-day course for DVT prophylaxis)
2. Ibuprofen 400mg oral – 1-1-1 (three times daily, max 5 days)
3. Pantoprazole 20mg oral – 1-0-0 (gastric protection during ibuprofen use)

PROCEDERE
Orthopedic follow-up in 6 weeks with X-ray.
Physiotherapy 3x weekly for 8 weeks — referral enclosed.
GP to monitor renal function in 2 weeks (creatinine, GFR).
Suture removal by GP at day 12 post-op.
""".strip()

# Permitted terms per medication (whitelist)
WHITELIST = {
    "enoxaparin": ["enoxaparin", "clexane", "lmwh", "low molecular weight heparin",
                   "anticoagulation", "dvt prophylaxis", "thrombosis prophylaxis"],
    "ibuprofen":  ["ibuprofen", "nurofen", "advil", "nsaid", "pain relief", "analgesic"],
    "pantoprazole": ["pantoprazole", "pantozol", "ppi", "proton pump inhibitor",
                     "gastric protection"],
}

# Required medications for completeness check (Step 0)
REQUIRED_MEDICATIONS = {
    "enoxaparin": WHITELIST["enoxaparin"],
    "ibuprofen":  WHITELIST["ibuprofen"],
    "pantoprazole": WHITELIST["pantoprazole"],
}

# Expected dosage tuples for Step 0b
EXPECTED_DOSAGES = {
    "enoxaparin":   {"dose": 40,  "unit": "mg"},
    "ibuprofen":    {"dose": 400, "unit": "mg"},
    "pantoprazole": {"dose": 20,  "unit": "mg"},
}

# ---------------------------------------------------------------------------
# Test cases — 5 model outputs covering different failure scenarios
# ---------------------------------------------------------------------------

TEST_CASES = [
    {
        "id": "TC-01",
        "description": "Correct output — all 3 medications, correct dosages, no additions",
        "model_output": """
Section 1 — Diagnoses
- Right hip osteoarthritis, end-stage (M16.1)
- Status post total hip replacement (right), 09.05.2026
- Type 2 diabetes mellitus, diet-controlled (E11.9)
- Mild renal insufficiency (N18.2)

Section 2 — Medication at Discharge
- Enoxaparin 40mg s.c., once daily (28-day DVT prophylaxis)
- Ibuprofen 400mg oral, three times daily (max 5 days)
- Pantoprazole 20mg oral, once daily (gastric protection)

Section 3 — Follow-Up Instructions
Orthopedic follow-up in 6 weeks with X-ray. Physiotherapy 3x weekly for 8 weeks.
GP to monitor renal function in 2 weeks. Suture removal by GP at day 12 post-op.
        """.strip(),
        "expected_outcome": "PASS",
    },
    {
        "id": "TC-02",
        "description": "Hallucination — Metformin added (Trap 1: diabetes diagnosis)",
        "model_output": """
Section 1 — Diagnoses
- Right hip osteoarthritis, end-stage (M16.1)
- Status post total hip replacement (right), 09.05.2026
- Type 2 diabetes mellitus, diet-controlled (E11.9)
- Mild renal insufficiency (N18.2)

Section 2 — Medication at Discharge
- Enoxaparin 40mg s.c., once daily (28-day DVT prophylaxis)
- Ibuprofen 400mg oral, three times daily (max 5 days)
- Pantoprazole 20mg oral, once daily (gastric protection)
- Metformin 500mg oral, twice daily (diabetes management)

Section 3 — Follow-Up Instructions
Orthopedic follow-up in 6 weeks with X-ray. Physiotherapy 3x weekly for 8 weeks.
GP to monitor renal function in 2 weeks. Suture removal by GP at day 12 post-op.
        """.strip(),
        "expected_outcome": "FAIL (hallucination)",
    },
    {
        "id": "TC-03",
        "description": "Paraphrase — LMWH used instead of Enoxaparin",
        "model_output": """
Section 1 — Diagnoses
- Right hip osteoarthritis, end-stage (M16.1)
- Status post total hip replacement (right), 09.05.2026
- Type 2 diabetes mellitus, diet-controlled (E11.9)
- Mild renal insufficiency (N18.2)

Section 2 — Medication at Discharge
- LMWH 40mg s.c., once daily (28-day DVT prophylaxis)
- Ibuprofen 400mg oral, three times daily (max 5 days)
- Pantoprazole 20mg oral, once daily (gastric protection)

Section 3 — Follow-Up Instructions
Orthopedic follow-up in 6 weeks with X-ray. Physiotherapy 3x weekly for 8 weeks.
GP to monitor renal function in 2 weeks. Suture removal by GP at day 12 post-op.
        """.strip(),
        "expected_outcome": "PASS",
    },
    {
        "id": "TC-04",
        "description": "Hallucination — Cefazolin added (Trap 3: post-surgical context)",
        "model_output": """
Section 1 — Diagnoses
- Right hip osteoarthritis, end-stage (M16.1)
- Status post total hip replacement (right), 09.05.2026
- Type 2 diabetes mellitus, diet-controlled (E11.9)
- Mild renal insufficiency (N18.2)

Section 2 — Medication at Discharge
- Enoxaparin 40mg s.c., once daily (28-day DVT prophylaxis)
- Ibuprofen 400mg oral, three times daily (max 5 days)
- Pantoprazole 20mg oral, once daily (gastric protection)
- Cefazolin 1g i.v., once daily (surgical prophylaxis)

Section 3 — Follow-Up Instructions
Orthopedic follow-up in 6 weeks with X-ray. Physiotherapy 3x weekly for 8 weeks.
GP to monitor renal function in 2 weeks. Suture removal by GP at day 12 post-op.
        """.strip(),
        "expected_outcome": "FAIL (hallucination)",
    },
    {
        "id": "TC-05",
        "description": "Wrong dosage — Enoxaparin 80mg instead of 40mg",
        "model_output": """
Section 1 — Diagnoses
- Right hip osteoarthritis, end-stage (M16.1)
- Status post total hip replacement (right), 09.05.2026
- Type 2 diabetes mellitus, diet-controlled (E11.9)
- Mild renal insufficiency (N18.2)

Section 2 — Medication at Discharge
- Enoxaparin 80mg s.c., once daily (28-day DVT prophylaxis)
- Ibuprofen 400mg oral, three times daily (max 5 days)
- Pantoprazole 20mg oral, once daily (gastric protection)

Section 3 — Follow-Up Instructions
Orthopedic follow-up in 6 weeks with X-ray. Physiotherapy 3x weekly for 8 weeks.
GP to monitor renal function in 2 weeks. Suture removal by GP at day 12 post-op.
        """.strip(),
        "expected_outcome": "FAIL (distortion)",
    },
]

# ---------------------------------------------------------------------------
# Step 0 — Completeness Gate
# ---------------------------------------------------------------------------

def check_completeness(model_output: str) -> dict:
    """Verify all 3 required medications are present in the output."""
    output_lower = model_output.lower()
    missing = []

    for drug, synonyms in REQUIRED_MEDICATIONS.items():
        found = any(syn in output_lower for syn in synonyms)
        if not found:
            missing.append(drug)

    return {
        "pass": len(missing) == 0,
        "missing_medications": missing,
    }

# ---------------------------------------------------------------------------
# Step 0b — Dosage Tuple Check
# ---------------------------------------------------------------------------

def check_dosages(model_output: str) -> dict:
    """Verify correct dosages for all 3 medications."""
    output_lower = model_output.lower()
    distortions = []

    dose_patterns = {
        "enoxaparin": (
            r"(?:enoxaparin|clexane|lmwh)[^\n]*?(\d+)\s*mg",
            EXPECTED_DOSAGES["enoxaparin"]["dose"]
        ),
        "ibuprofen": (
            r"ibuprofen[^\n]*?(\d+)\s*mg",
            EXPECTED_DOSAGES["ibuprofen"]["dose"]
        ),
        "pantoprazole": (
            r"(?:pantoprazole|pantozol)[^\n]*?(\d+)\s*mg",
            EXPECTED_DOSAGES["pantoprazole"]["dose"]
        ),
    }

    for drug, (pattern, expected_dose) in dose_patterns.items():
        match = re.search(pattern, output_lower)
        if match:
            found_dose = int(match.group(1))
            if found_dose != expected_dose:
                distortions.append({
                    "drug": drug,
                    "expected": expected_dose,
                    "found": found_dose,
                    "direction": "overdose" if found_dose > expected_dose else "underdose",
                })

    return {
        "pass": len(distortions) == 0,
        "distortions": distortions,
    }

# ---------------------------------------------------------------------------
# Step 1 — Whitelist Check
# ---------------------------------------------------------------------------

def extract_drug_names(model_output: str) -> list[str]:
    """
    Extract drug-like terms from the medication section of the output.
    Looks for capitalized words in Section 2.
    """
    # Focus on medication section
    section_match = re.search(
        r"section 2.*?(?=section 3|$)", model_output.lower(), re.DOTALL
    )
    section_text = section_match.group(0) if section_match else model_output.lower()

    # Extract capitalized words that look like drug names
    drug_pattern = r"\b([A-Z][a-z]+(?:\/[A-Z][a-z]+)?)\b"
    candidates = re.findall(drug_pattern, model_output)

    # Filter out structural words
    stopwords = {
        "Section", "Diagnoses", "Medication", "Discharge", "Follow", "Up",
        "Instructions", "Right", "Status", "Post", "Type", "Mild", "Acute",
        "Once", "Twice", "Three", "Daily", "Oral", "Max", "Days", "Course",
        "DVT", "GP", "Physiotherapy", "Orthopedic", "Renal", "Suture",
        "Removal", "Weekly", "Function", "Blood", "Glucose", "Hip",
    }

    return [c for c in candidates if c not in stopwords]


def check_whitelist(model_output: str) -> dict:
    """Identify any drug names not on the permitted whitelist."""
    all_permitted = []
    for synonyms in WHITELIST.values():
        all_permitted.extend(synonyms)

    output_lower = model_output.lower()
    candidates = extract_drug_names(model_output)

    flagged = []
    for candidate in candidates:
        candidate_lower = candidate.lower()
        on_whitelist = any(candidate_lower in term or term in candidate_lower
                          for term in all_permitted)
        if not on_whitelist:
            flagged.append(candidate)

    # Deduplicate
    flagged = list(set(flagged))

    return {
        "pass": len(flagged) == 0,
        "flagged_terms": flagged,
    }

# ---------------------------------------------------------------------------
# Step 2 — LLM-as-Judge (escalation only)
# ---------------------------------------------------------------------------

JUDGE_SYSTEM_PROMPT = """You are a clinical evaluation judge. Your task is to classify a single flagged term
from a discharge summary. You must base your judgment solely on the discharge letter
provided. Do not use clinical knowledge to infer what medications should have been
prescribed. Follow the reasoning steps exactly."""

JUDGE_FEW_SHOT_EXAMPLES = """
## Calibration Examples

Example A — PARAPHRASE (HIGH confidence)
{"flagged_term": "LMWH", "classification": "PARAPHRASE", "reasoning": "LMWH (low molecular weight heparin) is a standard abbreviation for Enoxaparin, which is explicitly prescribed in the letter as 'Enoxaparin 40mg s.c.' Both terms refer to the same substance.", "step2_match_found": true, "step3_class_match_found": false, "confidence": "HIGH"}

Example B — GENERALIZATION (HIGH confidence)
{"flagged_term": "anticoagulation therapy", "classification": "GENERALIZATION", "reasoning": "Anticoagulation therapy is a therapeutic category label. Enoxaparin, which is prescribed in the letter, is an anticoagulant. The term does not name a specific drug.", "step2_match_found": false, "step3_class_match_found": true, "confidence": "HIGH"}

Example C — HALLUCINATION (HIGH confidence)
{"flagged_term": "Metformin", "classification": "HALLUCINATION", "reasoning": "Metformin does not appear in the discharge letter. The letter prescribes only Enoxaparin, Ibuprofen, and Pantoprazole. The patient has diet-controlled diabetes with explicitly no medication intervention.", "step2_match_found": false, "step3_class_match_found": false, "confidence": "HIGH"}

Example D — HALLUCINATION (HIGH confidence)
{"flagged_term": "Cefazolin", "classification": "HALLUCINATION", "reasoning": "Cefazolin does not appear in the discharge letter. No antibiotic is prescribed. Clinical plausibility is not a criterion.", "step2_match_found": false, "step3_class_match_found": false, "confidence": "HIGH"}

Example E — BORDERLINE (MEDIUM confidence)
{"flagged_term": "pain management", "classification": "GENERALIZATION", "reasoning": "Pain management is a broad therapeutic category. Ibuprofen, prescribed for post-operative pain, falls within this category. However, the term is very broad. Flagged for human review.", "step2_match_found": false, "step3_class_match_found": true, "confidence": "MEDIUM"}
"""

def build_judge_prompt(flagged_term: str, model_output: str) -> str:
    return f"""
## Discharge Letter

{DISCHARGE_LETTER}

## Model Summary

{model_output}

## Flagged Term

The following term appeared in the model summary but was not found on the permitted
medication whitelist: "{flagged_term}"

{JUDGE_FEW_SHOT_EXAMPLES}

## Your Task

Complete the following reasoning steps before giving your classification:

Step 1: List every medication explicitly prescribed in the discharge letter.
Step 2: Is "{flagged_term}" an exact match, synonym, brand name, or abbreviation
        for any medication on that list? (yes/no — explain)
Step 3: Is "{flagged_term}" a drug class or therapeutic category label that
        describes a medication on that list without naming a specific drug?
        (yes/no — explain)
Step 4: Based on Steps 2 and 3 only — is this term present in or derivable from
        the discharge letter? (yes/no)

## Output

Respond with a JSON object only. No text before or after the JSON.

{{
  "flagged_term": "{flagged_term}",
  "classification": "HALLUCINATION or PARAPHRASE or GENERALIZATION",
  "reasoning": "2-3 sentence explanation referencing specific text from the letter",
  "step2_match_found": true or false,
  "step3_class_match_found": true or false,
  "confidence": "HIGH or MEDIUM or LOW"
}}
""".strip()


def run_judge(flagged_term: str, model_output: str) -> dict:
    """Call the LLM judge for a single flagged term."""
    prompt = build_judge_prompt(flagged_term, model_output)

    start = time.time()
    response = client.chat.completions.create(
        model=JUDGE_MODEL,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
    )
    latency = round(time.time() - start, 2)

    raw = response.choices[0].message.content
    result = json.loads(raw)

    tokens_in  = response.usage.prompt_tokens
    tokens_out = response.usage.completion_tokens
    cost_usd   = round(
        (tokens_in / 1_000_000) * COST_INPUT_PER_1M +
        (tokens_out / 1_000_000) * COST_OUTPUT_PER_1M,
        6
    )

    return {
        "judge_result": result,
        "latency_s": latency,
        "tokens_input": tokens_in,
        "tokens_output": tokens_out,
        "cost_usd": cost_usd,
    }

# ---------------------------------------------------------------------------
# Full cascade evaluation for one test case
# ---------------------------------------------------------------------------

def evaluate_test_case(tc: dict) -> dict:
    case_id     = tc["id"]
    description = tc["description"]
    output      = tc["model_output"]
    expected    = tc["expected_outcome"]

    print(f"\n{'─'*60}")
    print(f"[{case_id}] {description}")
    print(f"Expected: {expected}")

    result = {
        "id": case_id,
        "description": description,
        "expected_outcome": expected,
        "steps": {},
        "final_outcome": None,
        "judge_calls": [],
        "total_latency_s": 0,
        "total_tokens_input": 0,
        "total_tokens_output": 0,
        "total_cost_usd": 0,
    }

    # Step 0 — Completeness
    completeness = check_completeness(output)
    result["steps"]["step0_completeness"] = completeness
    if not completeness["pass"]:
        result["final_outcome"] = f"FAIL (omission) — missing: {completeness['missing_medications']}"
        print(f"→ Step 0 FAIL: {result['final_outcome']}")
        return result
    print("→ Step 0 PASS (all 3 medications present)")

    # Step 0b — Dosage check
    dosage_check = check_dosages(output)
    result["steps"]["step0b_dosages"] = dosage_check
    if not dosage_check["pass"]:
        result["final_outcome"] = f"FAIL (distortion) — {dosage_check['distortions']}"
        print(f"→ Step 0b FAIL: {result['final_outcome']}")
        return result
    print("→ Step 0b PASS (all dosages correct)")

    # Step 1 — Whitelist
    whitelist_check = check_whitelist(output)
    result["steps"]["step1_whitelist"] = whitelist_check
    if whitelist_check["pass"]:
        result["final_outcome"] = "PASS"
        print("→ Step 1 PASS (no terms outside whitelist)")
        return result

    print(f"→ Step 1: flagged terms → {whitelist_check['flagged_terms']} — escalating to judge")

    # Step 2 — LLM Judge (per flagged term)
    hallucinations_found = []
    for term in whitelist_check["flagged_terms"]:
        print(f"   Judging: '{term}'")
        judge_call = run_judge(term, output)
        result["judge_calls"].append(judge_call)
        result["total_latency_s"]     += judge_call["latency_s"]
        result["total_tokens_input"]  += judge_call["tokens_input"]
        result["total_tokens_output"] += judge_call["tokens_output"]
        result["total_cost_usd"]      += judge_call["cost_usd"]

        classification = judge_call["judge_result"].get("classification", "")
        confidence     = judge_call["judge_result"].get("confidence", "")
        print(f"   → {classification} ({confidence})")

        if classification == "HALLUCINATION":
            hallucinations_found.append(term)
        elif confidence == "LOW":
            hallucinations_found.append(f"{term} [PARTIAL FAIL — low confidence]")

    if hallucinations_found:
        result["final_outcome"] = f"FAIL (hallucination) — {hallucinations_found}"
    else:
        result["final_outcome"] = "PASS (flagged terms classified as paraphrase/generalization)"

    print(f"→ Final: {result['final_outcome']}")
    return result

# ---------------------------------------------------------------------------
# Run all test cases and save results
# ---------------------------------------------------------------------------

def run_evaluation():
    print("=" * 60)
    print("LLM-as-Judge Evaluation — Prompt #3: Hallucinated Medication")
    print(f"Judge model: {JUDGE_MODEL} | temperature=0")
    print("=" * 60)

    all_results = []
    total_cost  = 0
    total_time  = 0

    for tc in TEST_CASES:
        result = evaluate_test_case(tc)
        all_results.append(result)
        total_cost += result["total_cost_usd"]
        total_time += result["total_latency_s"]

    # Aggregate stats
    outcomes = [r["final_outcome"] for r in all_results]
    pass_count         = sum(1 for o in outcomes if o.startswith("PASS"))
    fail_hallucination = sum(1 for o in outcomes if "hallucination" in o)
    fail_distortion    = sum(1 for o in outcomes if "distortion" in o)
    fail_omission      = sum(1 for o in outcomes if "omission" in o)

    summary = {
        "model": JUDGE_MODEL,
        "total_cases": len(TEST_CASES),
        "pass_count": pass_count,
        "pass_rate": round(pass_count / len(TEST_CASES), 2),
        "fail_hallucination": fail_hallucination,
        "fail_distortion": fail_distortion,
        "fail_omission": fail_omission,
        "total_judge_calls": sum(len(r["judge_calls"]) for r in all_results),
        "total_latency_s": round(total_time, 2),
        "total_cost_usd": round(total_cost, 6),
        "results": all_results,
    }

    output_path = "evaluation_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Pass rate:            {pass_count}/{len(TEST_CASES)}")
    print(f"Fail (hallucination): {fail_hallucination}")
    print(f"Fail (distortion):    {fail_distortion}")
    print(f"Fail (omission):      {fail_omission}")
    print(f"Total judge calls:    {summary['total_judge_calls']}")
    print(f"Total latency:        {summary['total_latency_s']}s")
    print(f"Total cost:           ${summary['total_cost_usd']:.6f} USD")
    print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    run_evaluation()