# Semantic patterns and evidence contract

## What the source corpus supports

The empirical examples are 176 source-authored trap mappings from three Claude certification practice exams from one provider: CCAR-F (60), CCAR-P (63), and CCDV-F (53). The categories below are a manual semantic organization of those rows, with one primary category per row; counts sum to 176. They support reusable comparison questions, not a universal classifier or evidence about learner behavior. Counts describe this labeled corpus only and do not indicate real-world frequency.

Across domains, look for a choice that appears reasonable and addresses much of the stated goal, while one material scenario condition makes it inferior. The decisive difference may be a requirement, answer polarity, execution phase, scope, selection semantics, or an explicit priority. A near-miss can be valid in isolation and still fail the question.

| Pattern | Rows | Reusable comparison question | Grounded examples |
| --- | ---: | --- | --- |
| P1. Probabilistic means for a deterministic requirement | 17 | Does the stem require guaranteed behavior while the choice relies on prompt wording, examples, descriptions, or emphasis that can be ignored? | `MINORUN_CCARF_DRILL-s1-1`; `MINORUN_CCARP_DRILL-p5-1`; `MINORUN_CCDVF_DRILL-design2-3` |
| P2. Correct direction, partial fix, or symptom treatment | 32 | Does the choice improve one part but omit a required field, root cause, boundary, or consistency condition, or create excess scope? | `MINORUN_CCARF_DRILL-s1-3`; `MINORUN_CCARP_DRILL-p1-2`; `MINORUN_CCDVF_DRILL-prompt2-2` |
| P3. Sound method whose precondition fails here | 26 | Would the method work in a nearby scenario, but conflict with this question's observed condition, phase, or scope? | `MINORUN_CCARF_DRILL-s1-10`; `MINORUN_CCARP_DRILL-p2-4`; `MINORUN_CCDVF_DRILL-agent2-1` |
| P4. Wrong optimization axis or overdesign | 12 | Does the option maximize one quality while violating a stated cost, scale, latency, or policy priority, or add unnecessary machinery? | `MINORUN_CCARF_DRILL-s2-3`; `MINORUN_CCARP_DRILL-p1-5`; `MINORUN_CCDVF_DRILL-model2-2` |
| P5. Reverse-direction, exclusion, or violation-target bait | 27 | After normalizing whether the question asks for an exception, an unsuitable practice, an excluded path, or a security finding, does the mapped choice look suspect while actually fitting the stated scope? | `MINORUN_CCARF_DRILL-s1-2`; `MINORUN_CCARP_DRILL-p1-6`; `MINORUN_CCDVF_DRILL-agent2-4`; `MINORUN_CCDVF_DRILL-sec2-4` |
| P6. Combination contains a plausible but wrong atom | 36 | In a single-select combination question, does a tempting set include one unsupported statement alongside sound statements? Check each atom. | `MINORUN_CCARF_DRILL-s1-4`; `MINORUN_CCARP_DRILL-p1-4`; `MINORUN_CCDVF_DRILL-api2-2` |
| P7. Mechanism, fact, or causal relation is misplaced | 15 | Does the option invoke relevant knowledge but get the mechanism, timing, scope, or calculation wrong for the observed facts? | `MINORUN_CCARF_DRILL-s2-1`; `MINORUN_CCARP_DRILL-p3-2`; `MINORUN_CCDVF_DRILL-api2-1` |
| P8. Weak evidence or unsuitable metric | 11 | Does the choice rely on self-reported confidence, averages, counts, or unstructured information that does not measure the required outcome? | `MINORUN_CCARF_DRILL-s1-5`; `MINORUN_CCARP_DRILL-p1-10`; `MINORUN_CCDVF_DRILL-prompt2-6` |

These primary buckets overlap in meaning. P5 includes literal negative questions, but also exclusion and violation-target questions: `MINORUN_CCDVF_DRILL-agent2-4` asks when a self-managed Messages API loop is justified instead of Agent SDK, so a use case that fits the SDK is outside the requested exception; `MINORUN_CCDVF_DRILL-sec2-4` asks what a security review should flag, where an environment-variable reference is mistaken for a committed secret even though the actual issue is a shared administrator token. P6 describes answer structure, while the misleading atom may also fit another pattern; use one primary label only when summarizing this corpus, and add secondary notes only if the evidence supports them. The separately reviewed `MINORUN_CCARP_DRILL-p3-7` illustrates why answer polarity and key membership must be normalized: choice A is valid domain practice but is not the keyed answer to a question asking what is unsuitable. `MINORUN_CCARP_DRILL-p4-8` illustrates a choice that may help yet is comparatively weaker under an explicit cost/evaluation priority; do not call it false. Single-select composites such as `MINORUN_CCARF_DRILL-s2-10` and `MINORUN_CCDVF_DRILL-tech2-1` require atom-by-atom comparison; combination form alone is not evidence of a trap.

Across rows, the source explanations most often establish appeal through a sound component, then defeat the choice with material scenario evidence. Check these dimensions when relevant: context or prior state (`MINORUN_CCDVF_DRILL-agent2-1`), optimization priority (`MINORUN_CCDVF_DRILL-model2-2`), operation mode or phase (`MINORUN_CCARF_DRILL-s2-1`), configuration or precedence (`MINORUN_CCARP_DRILL-p4-9`), and scope (`MINORUN_CCDVF_DRILL-agent2-7`). These are prompts for comparison, not exhaustive categories. Weigh the decisive condition according to the stem; do not count shared features or assume every candidate fails on exactly one condition. A counterfactual belongs in the rationale only when the supplied evidence supports that changed condition.

Do not infer that the source-designated choice was empirically the most attractive, most selected, or uniquely nearest. The source mapping establishes only what the author labeled. Some corpus comparisons summarize why the mapped choice overlaps the key more than other wrong options, rather than comparing each competing distractor individually; independently compare all choices and report a runner-up or tie when supported. Do not rationalize an unsupported ranking. These classifications were not independently checked against current technical documentation. Read current official sources when a fact may have changed or when evaluating another domain. Claude-specific product guidance does not transfer automatically to other products. The 176 labels cover one provider's three Claude exams; this corpus alone does not establish transfer accuracy on other exams or vendors.

## Worked contrasts from the source

These paraphrases show how the comparison works. The source-designated choice is an authored label, not evidence that learners selected it or that it was uniquely nearest. Technical details below reflect the source questions and explanations; treat mutable product behavior as historical and check current official documentation before using it as present-day advice.

- **`MINORUN_CCARF_DRILL-s1-1` — end-state guarantee:** The stem requires every session to end with a recorded resolution or a human handoff, including customer departures. The key is B, which checks those records in code and creates a handoff if both are absent; the source labels A (prompt plus few-shot) as the trap because it improves guidance but cannot enforce it or act after departure. C is weaker for a separate reason: silence is not proof that a refund was resolved.
- **`MINORUN_CCARF_DRILL-s6-5` — preserve three distinct unknown states:** Contract extraction must distinguish no renewal clause, an ambiguous clause, and an unlisted renewal type. The key is B (`null`, `unclear`, and `other` plus detail); the source labels A as the trap because one `unknown` bucket erases distinctions and sends even harmless omissions to review. C gives up the enum's constrained values altogether, while D forces missing or ambiguous cases into invented values.
- **`MINORUN_CCARP_DRILL-p2-7` — optimize against the actual usage pattern:** The design review needs the entire standard, while requests are 15–30 minutes apart and logs show repeated cache writes with almost no reads. The key is A, which changes the cache lifetime; the source labels B (retrieve only selected sections) as the trap because it drops context the task explicitly needs. C's periodic keep-alive requests also address expiry, but waste calls during idle periods. The question's cache lifetime and pricing details are source-era facts, not current settings or advice.
- **`MINORUN_CCARP_DRILL-p1-5` — fixed branches favor routing:** Four procedures have fixed content, and the free-form question only needs classification into one procedure. The key is B, a classifier that routes to the corresponding fixed guidance; the source labels A (an agent with a search tool) as the trap because flexibility adds cost, latency, and room for answer variation. C runs all four procedures even though only one applies; D's evaluate-and-rewrite loop fits variable text quality rather than fixed instructions.
- **`MINORUN_CCARP_DRILL-p3-7` — normalize the negative prompt:** The question asks which index practice is unsuitable; D is keyed because mixing vectors from different embedding models breaks meaningful similarity comparison. The source labels A (filter to the current policy version) as the trap: it can look like it hides old material, yet is a valid way to prevent obsolete rules from answering current-policy questions. B's document replacement and C's pre-release retrieval checks are also supported by the source explanation, so do not call A technically wrong.
- **`MINORUN_CCDVF_DRILL-tech2-1` — inspect each atom in a combination:** The prompt asks for two correct statements; the key C combines the input-plus-output context limit with the fact that equivalent text can tokenize differently by language. The source labels A as the trap: it includes true statement ① but also claims temperature zero guarantees identical text, which the source explanation rejects. B and D also include false statement ③, which confuses an output cap with input context size.
- **`MINORUN_CCDVF_DRILL-api2-3` — distinguish expiry from no cache creation:** Requests arrive seconds apart, but cache creation and read counts are both zero for a 640-token input. The key is B, matching the source explanation's then-current model-specific minimum-length premise; the source labels A (expiry) as the trap because expiry would explain a new write, not zero writes. D is separately contradicted by the source's prefix behavior: changing a later user message does not invalidate an unchanged earlier system prefix. The model threshold is mutable and must be rechecked before current use.
- **`MINORUN_CCDVF_DRILL-prompt2-6` — verify the cited source:** A confident answer cites a clause absent from the retrieved contract. The key is D, which checks the citation against the document in code and withholds unsupported text; the source labels A (self-reported confidence) as the trap because confident wording can accompany a fabricated citation. B only asks the model to comply, and C may lower error risk without detecting an error that still occurs.

## Review output contract

Produce one record per question considered, including held questions. Keep source evidence separate from model judgment. Use this stable shape (additional provenance fields are allowed when their meaning is clear):

```json
{
  "question_key": {"source": "stable question ID", "version": "stable version ID or content hash"},
  "question_polarity": "positive | negative | except | other",
  "selection": {"mode": "single | multi | unknown", "required_count": 1},
  "priority": ["best", "minimum_cost"],
  "answer_key": {"labels": ["B"], "basis": "reference or explanation supporting the key", "validity": "checked | uncertain | conflict"},
  "source_mapping": {"choice_id": "...", "original_index": 0, "label": "A", "status": "consistent | conflict | unresolved"},
  "existing_flag": null,
  "decision": "source_label | candidate | held | no_unique_trap",
  "evidence_basis": "source_explicit | model_inferred",
  "choices": [
    {"id": "...", "original_index": 0, "label": "A"},
    {"id": "...", "original_index": 1, "label": "B"}
  ],
  "trap_choice": {"id": "...", "original_index": 0, "label": "A"},
  "trap_label": "A",
  "pattern_id": "P2",
  "confidence": "strong | moderate | tentative | insufficient",
  "rationale": {
    "appeal": "...",
    "decisive_gap": "...",
    "competitor_comparison": [
      {"choice_id": "...", "label": "C", "why_weaker_or_tie": "..."}
    ]
  },
  "uncertainty": []
}
```

`question_key.source` identifies the question itself in its source system; it must not be only a provider name. Use the stable version ID when available, otherwise a content hash for the exact question/choice version. Use `source_mapping: null` and `existing_flag: null` when either provenance item was not supplied.

`original_index` is the zero-based position in the source option order, not the current display position. Include every choice in `choices`, with stable IDs, original indexes, and labels; this lets a reviewer verify that `trap_choice` is wrong according to the answer key. Keep source IDs and displayed positions separate if options have been shuffled. `source_mapping` records input provenance only: preserve the original explicit mapping, including a conflicting or unresolved one, without treating it as an accepted label. `existing_flag` similarly preserves the prior flag when provided. Any collision between the existing flag and source mapping or proposed choice requires `decision: held`; retain both provenance records and set `trap_choice` and `trap_label` to null. Use `decision: source_label` only when the explicit mapping is consistent with the verified key and normalized polarity and has no unresolved flag collision. A source mapping outranks a competing model guess only after these validity checks. `candidate` requires an evidence-backed comparative judgment and must never designate a keyed answer. `trap_label` is exactly `trap_choice.label` and must match an original choice label; taxonomy names belong in the optional `pattern_id`, never in `trap_label`. Use `trap_choice: null` and `trap_label: null` for held or `no_unique_trap`. `held` is appropriate when answer validity, polarity, selection semantics, source mapping conflicts, or factual currency cannot be resolved. Use `no_unique_trap` when comparison is complete and either no wrong choice plausibly stands out as a near-miss or multiple wrong choices are equally strong. `confidence` describes the strength of available evidence qualitatively, not a probability. Preserve all original labels and indexes even when display order differs.

The answer-key basis should point to the supplied source explanation, official reference, or other evidence. State the exact stem requirement or priority that defeats the candidate and compare it against each other wrong choice, with one comparison entry per choice. Do not rank by counting shared components, surface resemblance, or preferences absent from the stem. Reserve `uncertainty` for unresolved material issues; informational caveats may be stated in the rationale. An inferred `candidate` must have a checked answer key, `confidence` of `strong` or `moderate`, and an empty `uncertainty` list. If relative ranking remains materially uncertain, use `no_unique_trap` when comparison is complete or `held` when evidence is missing/conflicting. A valid `source_label` may retain a note about independent ranking ambiguity, but it must not collide with the existing flag. For multi-select questions, do not assign an individual choice as a trap unless the selection semantics and per-choice scoring make that judgment meaningful; otherwise hold the question. A negative/EXCEPT question may designate a technically true option as a wrong answer because it fails the requested answer-key membership. Explain that distinction explicitly.

## Validate review output

Resolve the helper from the actual directory containing `SKILL.md`, regardless of the current project. Run the standard-library validator on a JSON file containing either a record array or `{"records": [...]}`. It prints a machine-readable `{"valid": boolean, "errors": [...]}` object and exits nonzero when it finds errors:

```bash
python3 /path/to/exam-trap-choices/scripts/validate_review.py review.json --questions questions.json
```

For exact choice and existing-flag checks, optionally pass normalized source questions. This is a deliberately small input contract, not a parser for arbitrary exam-bank exports:

```json
{
  "questions": [
    {
      "question_key": {"source": "stable question ID", "version": "stable version ID or content hash"},
      "answer_key": {"labels": ["choice-label"]},
      "choices": [{"id": "stable-choice-ID", "original_index": 0, "label": "choice-label"}],
      "source_mapping": {"choice_id": "stable-choice-ID", "original_index": 0, "label": "choice-label"},
      "existing_flag": {"choice_id": "stable-choice-ID", "original_index": 0, "label": "choice-label"}
    }
  ]
}
```

Use `null` or omit `source_mapping`/`existing_flag` when absent. The normalized question key is the stable question ID plus version/content hash; a review record may use `case_id` plus `version` when no `question_key` is available. When `--questions` is supplied, every question in that file must have one review record. The validator checks structural consistency and reports errors; it does not judge semantic appeal, correctness of explanations, or whether a stated requirement truly supports the comparison. The regression tests use synthetic fixtures and contain no exam-bank question text.
