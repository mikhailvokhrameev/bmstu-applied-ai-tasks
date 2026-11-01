#!/usr/bin/env python3
"""Generate tests/expected.json from ontology_data.py (deterministic, stdlib only).

Expected answers are derived from the dataset tables, then asserted against the
sets mandated by the spec (Table 5 / section 8.2). No reasoner is involved.
Usage: python3 ontology/src/make_expected.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import ontology_data as D  # noqa: E402

OUT = os.path.normpath(os.path.join(HERE, "..", "..", "tests", "expected.json"))

MODELS = D.MODELS
MODEL_IRIS = sorted(m["iri"] for m in MODELS)


def target(ind, prop):
    """Single target of a functional-in-practice link (exactly one)."""
    t = ind["links"][prop]
    assert len(t) == 1, (ind["iri"], prop, t)
    return D.BY_IRI[t[0]]


def models_where(pred):
    return sorted(m["iri"] for m in MODELS if pred(m))


def volume(m):
    return target(m, "hasMemory")["data"]["volumeGiB"]


def memory_type(m):
    return target(target(m, "hasMemory"), "hasMemoryType")["iri"]


def is_active(m):
    return target(m, "hasCooling")["owl_class"] == "ActiveCooling"


q1 = {i["iri"]: models_where(lambda m, p=i["iri"]: target(m, "producedByManufacturer")["iri"] == p)
      for i in D.MANUFACTURERS}
q2 = {i["iri"]: models_where(lambda m, g=i["iri"]: target(m, "usesGPU")["iri"] == g)
      for i in D.GPUS}
q3 = models_where(lambda m: volume(m) >= 8)
q4 = {i["iri"]: models_where(lambda m, t=i["iri"]: memory_type(m) == t)
      for i in D.MEMORY_TYPES}
q5 = models_where(is_active)
q6 = {i["iri"]: models_where(lambda m, o=i["iri"]: o in m["links"]["hasVideoOutput"])
      for i in D.VIDEO_OUTPUTS}
q7 = {i["iri"]: models_where(lambda m, f=i["iri"]: target(m, "hasInterface")["iri"] == f)
      for i in D.INTERFACES}
q8 = sorted(set(q3) & set(q5))

# Representative argument per parameterised question (some-but-not-all models).
REPRESENTATIVE = {
    "Q1": "P1",
    "Q2": "GPU_G3",
    "Q4": "GDDR6",
    "Q6": "DVI",
    "Q7": "PCIe_4_0_x16",
}


def build():
    def param(qid, text, argument, table):
        rep = REPRESENTATIVE[qid]
        members = table[rep]
        negatives = sorted(set(MODEL_IRIS) - set(members))
        return {
            "question": text,
            "argument": argument,
            "representative": rep,
            "positive_example": members[0],
            "negative_example": negatives[0],
            "expected": table,
        }

    def plain(text, members):
        return {"question": text, "argument": None, "representative": None, "expected": members}

    return {
        "format": (
            "Fixed expected answers for the 8 control questions, written by "
            "ontology/src/make_expected.py from ontology/src/ontology_data.py BEFORE any "
            "reasoner run. questions.Qn.expected is either a dict {argument IRI local name: "
            "sorted list of VideoCardModel individual local names} (Q1, Q2, Q4, Q6, Q7) or a "
            "sorted list (Q3, Q5, Q8, no argument). All names are local names in "
            "https://example.org/ontologies/videocard#. 'representative' is the argument used "
            "for the documented positive/negative check (member and non-member exist); "
            "it is null for argument-less questions. 'universe' lists all models."
        ),
        "namespace": "https://example.org/ontologies/videocard#",
        "universe": MODEL_IRIS,
        "questions": {
            "Q1": param("Q1", "Models produced by a given manufacturer", "manufacturer", q1),
            "Q2": param("Q2", "Models using a given GPU", "gpu", q2),
            "Q3": plain("Models with memory of at least 8 GiB (CardWith8GBMemory)", q3),
            "Q4": param("Q4", "Models with a given memory type", "memory type", q4),
            "Q5": plain("Models with active cooling (CardWithActiveCooling)", q5),
            "Q6": param("Q6", "Models having a given video output", "video output", q6),
            "Q7": param("Q7", "Models with a given connection interface", "interface", q7),
            "Q8": plain("Models with memory >= 8 GiB AND active cooling", q8),
        },
    }


def check():
    # Sets mandated by Table 5 / spec 8.2 and Global Constraints.
    assert q3 == ["U02", "U03", "U04", "U06", "U07"], q3
    assert q5 == ["U02", "U03", "U04", "U05", "U07"], q5
    assert q8 == ["U02", "U03", "U04", "U07"], q8
    assert q1["P1"] == ["U01", "U02", "U05", "U08"], q1
    assert q1["P2"] == ["U03", "U04", "U06", "U07"], q1
    assert q4["GDDR6"] == ["U02", "U03", "U04", "U05", "U06"], q4
    assert q4["GDDR5"] == ["U01", "U08"], q4
    assert q4["GDDR6X"] == ["U07"], q4
    assert MODEL_IRIS == ["U0%d" % i for i in range(1, 9)]
    # Table 5 dataset values directly.
    table5 = {
        "U01": (4, False, "GDDR5", "P1"), "U02": (8, True, "GDDR6", "P1"),
        "U03": (12, True, "GDDR6", "P2"), "U04": (16, True, "GDDR6", "P2"),
        "U05": (6, True, "GDDR6", "P1"), "U06": (8, False, "GDDR6", "P2"),
        "U07": (24, True, "GDDR6X", "P2"), "U08": (2, False, "GDDR5", "P1"),
    }
    for m in MODELS:
        got = (volume(m), is_active(m), memory_type(m), target(m, "producedByManufacturer")["iri"])
        assert got == table5[m["iri"]], (m["iri"], got)
    # Every parameterised answer table covers all argument individuals; every
    # question has >=1 positive and >=1 negative example for its representative.
    for qid, table in (("Q1", q1), ("Q2", q2), ("Q4", q4), ("Q6", q6), ("Q7", q7)):
        rep = REPRESENTATIVE[qid]
        pos = set(table[rep])
        neg = set(MODEL_IRIS) - pos
        assert pos and neg, (qid, rep, "need positive and negative example")
    for qid, members in (("Q3", q3), ("Q5", q5), ("Q8", q8)):
        assert members and set(MODEL_IRIS) - set(members), qid
    assert len(q2) == 5 and all(q2.values()), "each of the 5 GPUs must be used by >=1 model"
    assert any(len(v) > 1 for v in q2.values()), "some GPU must be shared"
    # Every model carries the marker; each model has exactly one of each single link.
    for m in MODELS:
        assert D.MARKER in m["comment"], m["iri"]
        for p in ("usesGPU", "hasMemory", "hasCooling", "hasInterface",
                  "producedByManufacturer", "hasPurpose"):
            assert len(m["links"][p]) == 1, (m["iri"], p)
        assert len(m["links"]["hasVideoOutput"]) >= 1, m["iri"]
        assert set(m["data"]) == {"powerW", "lengthMM"}, m["iri"]
    # Shared memory config (U02 and U06) and a shared GPU exist.
    assert q2 and target(MODELS[1], "hasMemory")["iri"] == target(MODELS[5], "hasMemory")["iri"]


def main():
    check()
    text = json.dumps(build(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print("wrote %s; assertions passed" % OUT)


if __name__ == "__main__":
    main()
