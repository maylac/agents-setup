#!/usr/bin/env python3
"""Validate structure and identity consistency in exam trap review JSON."""

import argparse
import json
import sys
from pathlib import Path


def load_json(path):
    try:
        with open(path, encoding="utf-8") as stream:
            return json.load(stream)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read JSON {path}: {exc}") from exc


def records_from(data, key="records"):
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get(key), list):
        return data[key]
    raise ValueError(f"JSON must be an array or an object with a {key!r} array")


def identity(choice):
    if not isinstance(choice, dict):
        return None
    choice_id = choice.get("choice_id", choice.get("id"))
    original_index = choice.get("original_index")
    label = choice.get("label")
    if (not isinstance(choice_id, str) or not choice_id
            or not isinstance(original_index, int) or isinstance(original_index, bool)
            or original_index < 0 or not isinstance(label, str) or not label):
        return None
    return choice_id, original_index, label


def question_key(record):
    qkey = record.get("question_key")
    if isinstance(qkey, dict):
        source, version = qkey.get("source"), qkey.get("version")
    else:
        source, version = record.get("case_id"), record.get("version")
    if not isinstance(source, str) or not source.strip():
        return None
    if not isinstance(version, str) or not version.strip():
        return None
    return source, version


def validate(review_data, questions_data=None):
    errors = []
    try:
        records = records_from(review_data)
    except ValueError as exc:
        return [str(exc)]

    questions_by_key = {}
    if questions_data is not None:
        try:
            questions = records_from(questions_data, "questions")
        except ValueError as exc:
            return [str(exc)]
        for index, question in enumerate(questions):
            key = question_key(question) if isinstance(question, dict) else None
            if key is None:
                errors.append(f"questions[{index}]: requires stable question_key.source and question_key.version")
                continue
            if key in questions_by_key:
                errors.append(f"questions[{index}]: duplicate question/version {key!r}")
            questions_by_key[key] = question

    seen_keys = set()
    for index, record in enumerate(records):
        prefix = f"records[{index}]"
        if not isinstance(record, dict):
            errors.append(f"{prefix}: record must be an object")
            continue

        key = question_key(record)
        if key is None:
            errors.append(f"{prefix}: requires stable question_key.source and question_key.version (or case_id and version)")
        elif key in seen_keys:
            errors.append(f"{prefix}: duplicate question/version {key!r}")
        else:
            seen_keys.add(key)

        choice_rows = record.get("choices")
        choices_by_id = {}
        choice_identities = set()
        choice_indexes = set()
        choice_labels = set()
        if not isinstance(choice_rows, list) or not choice_rows:
            errors.append(f"{prefix}: choices must be a non-empty array")
            choice_rows = []
        for cindex, choice in enumerate(choice_rows):
            cp = f"{prefix}.choices[{cindex}]"
            if not isinstance(choice, dict):
                errors.append(f"{cp}: choice must be an object")
                continue
            cid, original_index, label = choice.get("id"), choice.get("original_index"), choice.get("label")
            if not isinstance(cid, str) or not cid:
                errors.append(f"{cp}: id must be a non-empty string")
            if not isinstance(original_index, int) or isinstance(original_index, bool) or original_index < 0:
                errors.append(f"{cp}: original_index must be a non-negative integer")
            if not isinstance(label, str) or not label:
                errors.append(f"{cp}: label must be a non-empty string")
            if isinstance(cid, str) and cid:
                if cid in choices_by_id:
                    errors.append(f"{cp}: duplicate choice id {cid!r}")
                else:
                    choices_by_id[cid] = choice
            if isinstance(original_index, int) and not isinstance(original_index, bool) and original_index >= 0:
                if original_index in choice_indexes:
                    errors.append(f"{cp}: duplicate original_index {original_index!r}")
                choice_indexes.add(original_index)
            if isinstance(label, str) and label:
                if label in choice_labels:
                    errors.append(f"{cp}: duplicate choice label {label!r}")
                choice_labels.add(label)
            choice_identity = identity(choice)
            if choice_identity is not None:
                choice_identities.add(choice_identity)

        answer_key = record.get("answer_key")
        answer_labels = answer_key.get("labels") if isinstance(answer_key, dict) else None
        if not isinstance(answer_labels, list) or not all(isinstance(x, str) for x in answer_labels):
            errors.append(f"{prefix}: answer_key.labels must be a string array")
            answer_labels = []
        elif not answer_labels and record.get("decision") != "held":
            errors.append(f"{prefix}: accepted decisions require a non-empty answer_key.labels")
        elif any(label not in choice_labels for label in answer_labels):
            errors.append(f"{prefix}: answer_key contains a label absent from choices")
        if isinstance(answer_key, dict) and answer_key.get("validity") == "checked":
            basis = answer_key.get("basis")
            if not isinstance(basis, str) or not basis.strip():
                errors.append(f"{prefix}: checked answer key requires a non-empty basis")

        decision = record.get("decision")
        if decision not in {"source_label", "candidate", "held", "no_unique_trap"}:
            errors.append(f"{prefix}: invalid decision {decision!r}")

        trap = record.get("trap_choice")
        trap_label = record.get("trap_label")
        if trap is None:
            if trap_label is not None:
                errors.append(f"{prefix}: trap_label must be null when trap_choice is null")
        elif isinstance(trap, dict):
            triplet = identity(trap)
            if triplet not in choice_identities:
                errors.append(f"{prefix}: trap_choice id/index/label does not match an original choice")
            if trap_label != trap.get("label"):
                errors.append(f"{prefix}: trap_label must exactly equal trap_choice.label")
            if trap.get("label") not in choice_labels:
                errors.append(f"{prefix}: trap_choice label is not an original choice label")
            if trap.get("label") in answer_labels:
                errors.append(f"{prefix}: trap_choice cannot be a keyed answer")
        else:
            errors.append(f"{prefix}: trap_choice must be an object or null")

        if decision in {"held", "no_unique_trap"} and (trap is not None or trap_label is not None):
            errors.append(f"{prefix}: {decision} must have null trap_choice and trap_label")
        if decision in {"candidate", "source_label"} and (trap is None or trap_label is None):
            errors.append(f"{prefix}: {decision} requires a trap_choice and non-null trap_label")
        if decision in {"candidate", "source_label", "no_unique_trap"}:
            if not isinstance(answer_key, dict) or answer_key.get("validity") != "checked":
                errors.append(f"{prefix}: {decision} requires a checked answer key")
            if not answer_labels:
                errors.append(f"{prefix}: {decision} requires non-empty answer_key.labels")
            basis = answer_key.get("basis") if isinstance(answer_key, dict) else None
            if not isinstance(basis, str) or not basis.strip():
                errors.append(f"{prefix}: {decision} requires a non-empty answer-key basis")
        if decision == "candidate":
            if record.get("evidence_basis") != "model_inferred":
                errors.append(f"{prefix}: candidate requires evidence_basis=model_inferred")
            if record.get("source_mapping") is not None:
                errors.append(f"{prefix}: candidate cannot replace an explicit source mapping")
            if record.get("confidence") not in {"strong", "moderate"}:
                errors.append(f"{prefix}: candidate confidence must be strong or moderate")
            uncertainty = record.get("uncertainty")
            if not isinstance(uncertainty, list) or uncertainty:
                errors.append(f"{prefix}: candidate requires uncertainty=[]; resolve material uncertainty first")
        if decision == "source_label":
            mapping = record.get("source_mapping")
            if not isinstance(mapping, dict) or mapping.get("status") != "consistent":
                errors.append(f"{prefix}: source_label requires a consistent source_mapping")
            elif trap is None or identity(mapping) != identity(trap):
                errors.append(f"{prefix}: source_label trap_choice must match source_mapping")
            if record.get("evidence_basis") != "source_explicit":
                errors.append(f"{prefix}: source_label requires evidence_basis=source_explicit")

        if key is not None and questions_data is not None:
            question = questions_by_key.get(key)
            if question is None:
                errors.append(f"{prefix}: question/version is absent from --questions input")
            else:
                input_choices = question.get("choices")
                expected = set()
                if isinstance(input_choices, list):
                    expected = {item for choice in input_choices if (item := identity(choice)) is not None}
                if choice_identities != expected:
                    errors.append(f"{prefix}: choices do not exactly match --questions identities/indexes/labels")
                input_answer = question.get("answer_key", {}).get("labels", [])
                if set(answer_labels) != set(input_answer):
                    errors.append(f"{prefix}: answer_key labels do not match --questions")

                for field in ("source_mapping", "existing_flag"):
                    input_ref = question.get(field)
                    output_ref = record.get(field)
                    if identity(input_ref) != identity(output_ref):
                        errors.append(f"{prefix}: {field} provenance does not match --questions")

                source_ref = question.get("source_mapping")
                existing_ref = question.get("existing_flag")
                source_identity = identity(source_ref)
                existing_identity = identity(existing_ref)
                proposed_identity = identity(trap)
                conflict = False
                if source_identity is not None and existing_identity is not None and source_identity != existing_identity:
                    conflict = True
                if existing_identity is not None and proposed_identity is not None and existing_identity != proposed_identity:
                    conflict = True
                if conflict and (decision != "held" or trap is not None or trap_label is not None):
                    errors.append(f"{prefix}: existing-flag collision requires held with null trap fields")

    if questions_data is not None:
        question_keys = set(questions_by_key)
        missing = question_keys - seen_keys
        if missing:
            errors.append(f"--questions contains {len(missing)} question/version record(s) absent from review output")

    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("review", help="review JSON: an array or an object with a records array")
    parser.add_argument("--questions", help="optional normalized source-question JSON with a questions array")
    args = parser.parse_args(argv)

    try:
        review_data = load_json(args.review)
        questions_data = load_json(args.questions) if args.questions else None
    except ValueError as exc:
        print(json.dumps({"valid": False, "errors": [str(exc)]}, ensure_ascii=False))
        return 2

    errors = validate(review_data, questions_data)
    print(json.dumps({"valid": not errors, "errors": errors}, ensure_ascii=False))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
