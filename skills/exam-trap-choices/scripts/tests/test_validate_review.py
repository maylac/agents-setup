import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import validate_review


CHOICES = [
    {"id": "choice-left", "original_index": 0, "label": "option-left"},
    {"id": "choice-right", "original_index": 1, "label": "option-right"},
]


def base_record():
    return {
        "question_key": {"source": "stable-question-id", "version": "version-hash"},
        "question_polarity": "positive",
        "selection": {"mode": "single", "required_count": 1},
        "answer_key": {"labels": ["option-right"], "basis": "supplied answer explanation", "validity": "checked"},
        "source_mapping": None,
        "existing_flag": None,
        "decision": "candidate",
        "evidence_basis": "model_inferred",
        "choices": CHOICES,
        "trap_choice": CHOICES[0],
        "trap_label": "option-left",
        "pattern_id": "pattern-alpha",
        "confidence": "moderate",
        "rationale": {"appeal": "plausible", "decisive_gap": "misses a stated requirement", "competitor_comparison": []},
        "uncertainty": [],
    }


def normalized_question(source_mapping=None, existing_flag=None):
    return {
        "question_key": {"source": "stable-question-id", "version": "version-hash"},
        "answer_key": {"labels": ["option-right"]},
        "choices": CHOICES,
        "source_mapping": source_mapping,
        "existing_flag": existing_flag,
    }


class ValidateReviewTests(unittest.TestCase):
    def test_valid_source_label(self):
        record = base_record()
        mapping = {"choice_id": "choice-left", "original_index": 0, "label": "option-left", "status": "consistent"}
        record.update({"decision": "source_label", "evidence_basis": "source_explicit", "source_mapping": mapping})
        self.assertEqual(validate_review.validate({"records": [record]}), [])

    def test_valid_inferred_candidate(self):
        self.assertEqual(validate_review.validate({"records": [base_record()]}), [])

    def test_pattern_name_cannot_be_trap_label(self):
        record = base_record()
        record["trap_label"] = "pattern-alpha"
        self.assertTrue(any("trap_label must exactly equal" in e for e in validate_review.validate({"records": [record]})))

    def test_keyed_choice_cannot_be_trap(self):
        record = base_record()
        record["trap_choice"] = CHOICES[1]
        record["trap_label"] = "option-right"
        self.assertTrue(any("cannot be a keyed answer" in e for e in validate_review.validate({"records": [record]})))

    def test_shuffled_choice_identity_must_keep_original_index(self):
        record = base_record()
        record["trap_choice"] = {"id": "choice-left", "original_index": 1, "label": "option-left"}
        self.assertTrue(any("does not match an original choice" in e for e in validate_review.validate({"records": [record]})))

    def test_unresolved_existing_flag_conflict_rejects_accepted_mapping(self):
        record = base_record()
        mapping = {"choice_id": "choice-left", "original_index": 0, "label": "option-left", "status": "consistent"}
        existing = {"choice_id": "choice-right", "original_index": 1, "label": "option-right"}
        record.update({"decision": "source_label", "evidence_basis": "source_explicit", "source_mapping": mapping, "existing_flag": existing})
        questions = {"questions": [normalized_question(mapping, existing)]}
        self.assertTrue(any("existing-flag collision requires held" in e for e in validate_review.validate({"records": [record]}, questions)))

    def test_held_null_preserves_conflicting_provenance(self):
        mapping = {"choice_id": "choice-left", "original_index": 0, "label": "option-left", "status": "consistent"}
        existing = {"choice_id": "choice-right", "original_index": 1, "label": "option-right"}
        record = base_record()
        record.update({"decision": "held", "evidence_basis": "source_explicit", "source_mapping": mapping, "existing_flag": existing, "trap_choice": None, "trap_label": None, "confidence": "insufficient", "uncertainty": ["source and existing flags conflict"]})
        questions = {"questions": [normalized_question(mapping, existing)]}
        self.assertEqual(validate_review.validate({"records": [record]}, questions), [])

    def test_candidate_with_material_uncertainty_is_rejected(self):
        record = base_record()
        record["uncertainty"] = ["relative ranking remains unresolved"]
        self.assertTrue(any("uncertainty=[]" in e for e in validate_review.validate({"records": [record]})))

    def test_held_may_have_missing_answer_key(self):
        record = base_record()
        record.update({
            "decision": "held",
            "answer_key": {"labels": [], "basis": "", "validity": "uncertain"},
            "trap_choice": None,
            "trap_label": None,
            "confidence": "insufficient",
            "uncertainty": ["answer key not supplied"],
        })
        self.assertEqual(validate_review.validate({"records": [record]}), [])

    def test_candidate_requires_non_null_trap(self):
        record = base_record()
        record.update({"trap_choice": None, "trap_label": None})
        self.assertTrue(any("candidate requires a trap_choice" in e for e in validate_review.validate({"records": [record]})))

    def test_source_label_requires_non_null_trap(self):
        record = base_record()
        mapping = {"choice_id": "choice-left", "original_index": 0, "label": "option-left", "status": "consistent"}
        record.update({"decision": "source_label", "evidence_basis": "source_explicit", "source_mapping": mapping, "trap_choice": None, "trap_label": None})
        self.assertTrue(any("source_label requires a trap_choice" in e for e in validate_review.validate({"records": [record]})))

    def test_source_label_requires_checked_answer_key(self):
        record = base_record()
        mapping = {"choice_id": "choice-left", "original_index": 0, "label": "option-left", "status": "consistent"}
        record.update({"decision": "source_label", "evidence_basis": "source_explicit", "source_mapping": mapping})
        record["answer_key"]["validity"] = "uncertain"
        self.assertTrue(any("source_label requires a checked answer key" in e for e in validate_review.validate({"records": [record]})))

    def test_duplicate_question_version_is_rejected(self):
        first, second = base_record(), base_record()
        second["trap_label"] = "pattern-alpha"
        errors = validate_review.validate({"records": [first, second]})
        self.assertTrue(any("duplicate question/version" in e for e in errors))

    def test_source_label_requires_consistent_mapping(self):
        record = base_record()
        record.update({"decision": "source_label", "evidence_basis": "source_explicit"})
        self.assertTrue(any("requires a consistent source_mapping" in e for e in validate_review.validate({"records": [record]})))

    def test_questions_input_requires_full_review_coverage(self):
        record = base_record()
        questions = {"questions": [normalized_question(), {**normalized_question(), "question_key": {"source": "another-question", "version": "version-hash"}}]}
        self.assertTrue(any("absent from review output" in e for e in validate_review.validate({"records": [record]}, questions)))


if __name__ == "__main__":
    unittest.main()
