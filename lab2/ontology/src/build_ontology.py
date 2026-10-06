#!/usr/bin/env python3
"""Emit the VideoCardOntology v1.0.0 as OWL 2 Functional-Style Syntax.

Stdlib only, deterministic (fixed ordering, no timestamps). The TBox is written
out here; the ABox comes from ontology_data.py.

Usage: python3 build_ontology.py [--mutate T06|T07|T08|T09] [output.fss]   (default: stdout)

--mutate emits a negative-test copy of the ontology (Task 5, spec Table 6): the
final ontology with one minimal, explicit ABox edit listed in MUTATIONS below.
Without --mutate the output is the final ontology, unchanged.

All Russian rdfs:label / rdfs:comment literals carry the language tag @ru.
Numeric data values: volumeGiB / busWidthBit -> xsd:positiveInteger,
fanCount -> xsd:nonNegativeInteger, frequencyMHz / powerW / lengthMM -> xsd:decimal.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import ontology_data as D  # noqa: E402

NS = "https://example.org/ontologies/videocard#"
ONT_IRI = "https://example.org/ontologies/videocard"
VERSION_IRI = "https://example.org/ontologies/videocard/1.0.0"

# --- TBox tables -------------------------------------------------------------
# (local name, Russian label, Russian comment, direct superclass or None)
CLASSES = [
    ("VideoCardModel", "Модель видеокарты",
     "Модель дискретной видеокарты; основной объект описания.", None),
    ("ModelComponent", "Компонент модели",
     "Общий класс для модели GPU, конфигурации видеопамяти и системы охлаждения.", None),
    ("GPUModel", "Модель GPU",
     "Модель графического процессора; подкласс «Компонент модели».", "ModelComponent"),
    ("MemoryConfiguration", "Конфигурация видеопамяти",
     "Тип, объём и организация памяти; подкласс «Компонент модели».", "ModelComponent"),
    ("CoolingSystem", "Система охлаждения",
     "Вариант охлаждения модели карты; подкласс «Компонент модели».", "ModelComponent"),
    ("ActiveCooling", "Активное охлаждение",
     "Подкласс «Система охлаждения»; охлаждение с вентилятором.", "CoolingSystem"),
    ("PassiveCooling", "Пассивное охлаждение",
     "Подкласс «Система охлаждения»; охлаждение без вентилятора.", "CoolingSystem"),
    ("Manufacturer", "Производитель",
     "Организация, выпускающая модель видеокарты или модель GPU.", None),
    ("ConnectionInterface", "Интерфейс подключения",
     "Стандарт подключения видеокарты к компьютеру.", None),
    ("VideoOutput", "Видеовыход",
     "Поддерживаемый моделью тип интерфейса вывода изображения.", None),
    ("MemoryType", "Тип памяти",
     "Технология видеопамяти, например GDDR6.", None),
    ("GPUArchitecture", "Архитектура GPU",
     "Архитектура графического процессора.", None),
    ("Purpose", "Назначение",
     "Заявленная область использования модели видеокарты.", None),
]

DEFINED_CLASSES = [
    ("CardWith8GBMemory", "Карта с памятью от 8 ГиБ",
     "Определяемый класс: модель видеокарты, у которой конфигурация памяти имеет объём не менее 8 ГиБ. "
     "Принадлежность выводится reasoner."),
    ("CardWithActiveCooling", "Карта с активным охлаждением",
     "Определяемый класс: модель видеокарты, у которой система охлаждения является активной. "
     "Принадлежность выводится reasoner."),
]

# (local name, label, comment, domain, range)
OBJECT_PROPERTIES = [
    ("usesGPU", "использует GPU", "Связывает модель видеокарты с используемой моделью GPU.",
     "VideoCardModel", "GPUModel"),
    ("hasMemory", "имеет память", "Связывает модель видеокарты с конфигурацией видеопамяти.",
     "VideoCardModel", "MemoryConfiguration"),
    ("hasCooling", "имеет охлаждение", "Связывает модель видеокарты с системой охлаждения.",
     "VideoCardModel", "CoolingSystem"),
    ("hasInterface", "имеет интерфейс", "Связывает модель видеокарты с интерфейсом подключения.",
     "VideoCardModel", "ConnectionInterface"),
    ("hasVideoOutput", "имеет видеовыход", "Связывает модель видеокарты с поддерживаемым видеовыходом.",
     "VideoCardModel", "VideoOutput"),
    ("producedByManufacturer", "выпущена производителем",
     "Связывает модель видеокарты с производителем.", "VideoCardModel", "Manufacturer"),
    ("gpuProducedBy", "GPU выпущен производителем",
     "Связывает модель GPU с производителем.", "GPUModel", "Manufacturer"),
    ("hasArchitecture", "имеет архитектуру",
     "Связывает модель GPU с архитектурой GPU.", "GPUModel", "GPUArchitecture"),
    ("hasMemoryType", "имеет тип памяти",
     "Связывает конфигурацию видеопамяти с типом памяти.", "MemoryConfiguration", "MemoryType"),
    ("hasPurpose", "имеет назначение",
     "Связывает модель видеокарты с назначением.", "VideoCardModel", "Purpose"),
]

NAME_DOMAIN = ["VideoCardModel", "GPUModel", "Manufacturer", "ConnectionInterface",
               "VideoOutput", "MemoryType", "GPUArchitecture", "Purpose"]

# (local name, label, comment, domain, xsd range, kind)   kind: 'dtype' | 'decpos'
NUMERIC_PROPERTIES = [
    ("volumeGiB", "объём, ГиБ", "Объём видеопамяти в ГиБ.",
     "MemoryConfiguration", "xsd:positiveInteger"),
    ("busWidthBit", "ширина шины, бит", "Ширина шины памяти в битах.",
     "MemoryConfiguration", "xsd:positiveInteger"),
    ("frequencyMHz", "частота, МГц", "Частота модели GPU в МГц (десятичное число больше 0).",
     "GPUModel", "DEC"),
    ("powerW", "мощность, Вт",
     "Заявленная мощность модели платы в Вт (не рекомендуемая мощность блока питания); десятичное число больше 0.",
     "VideoCardModel", "DEC"),
    ("lengthMM", "длина, мм", "Длина платы в мм (десятичное число больше 0).",
     "VideoCardModel", "DEC"),
    ("fanCount", "число вентиляторов", "Число вентиляторов системы охлаждения, шт.",
     "CoolingSystem", "xsd:nonNegativeInteger"),
]
DATA_TYPE = {p[0]: p[4] for p in NUMERIC_PROPERTIES}
DATA_TYPE["frequencyMHz"] = DATA_TYPE["powerW"] = DATA_TYPE["lengthMM"] = "xsd:decimal"

TOP_LEVEL_DISJOINT = ["VideoCardModel", "ModelComponent", "Manufacturer", "ConnectionInterface",
                      "VideoOutput", "MemoryType", "GPUArchitecture", "Purpose"]
COMPONENT_DISJOINT = ["GPUModel", "MemoryConfiguration", "CoolingSystem"]

EXACTLY_ONE = [("usesGPU", "GPUModel"), ("hasMemory", "MemoryConfiguration"),
               ("hasCooling", "CoolingSystem"), ("hasInterface", "ConnectionInterface"),
               ("producedByManufacturer", "Manufacturer")]

# --- negative-test mutations (Task 5) -----------------------------------------
# Each mutation is a list of (old_line, new_line) ABox edits applied to the generated
# FSS lines: (old, None) removes `old`, (None, new) adds `new` before DifferentIndividuals,
# (old, new) replaces `old` in place. Every `old` line must occur exactly once.
MUTATIONS = {
    # T06: an active cooling individual is additionally asserted PassiveCooling
    # (ActiveCooling and PassiveCooling are disjoint).
    "T06": [(None, "ClassAssertion(vc:PassiveCooling vc:Cooling_Active_2fan)")],
    # T07: U01 additionally uses a second, different GPU (violates usesGPU exactly 1;
    # the GPUs are already pairwise different via DifferentIndividuals).
    "T07": [(None, "ObjectPropertyAssertion(vc:usesGPU vc:U01 vc:GPU_G2)")],
    # T08: the volume of Mem_4GiB_GDDR5 is REPLACED (not added) by -8 typed xsd:integer,
    # outside the range xsd:positiveInteger; volumeGiB stays single-valued (functional).
    "T08": [('DataPropertyAssertion(vc:volumeGiB vc:Mem_4GiB_GDDR5 "4"^^xsd:positiveInteger)',
             'DataPropertyAssertion(vc:volumeGiB vc:Mem_4GiB_GDDR5 "-8"^^xsd:integer)')],
    # T09: U05 loses its hasMemory assertion (open world: still consistent, card must flag it).
    "T09": [("ObjectPropertyAssertion(vc:hasMemory vc:U05 vc:Mem_6GiB_GDDR6)", None)],
}


def apply_mutation(lines, mutation):
    for old, new in mutation:
        if old is None:
            at = lines.index(next(l for l in lines if l.startswith("DifferentIndividuals(")))
            lines.insert(at, new)
            continue
        hits = [i for i, l in enumerate(lines) if l == old]
        if len(hits) != 1:
            raise SystemExit("mutation: expected exactly one line %r, found %d" % (old, len(hits)))
        if new is None:
            del lines[hits[0]]
        else:
            lines[hits[0]] = new


# --- FSS helpers -------------------------------------------------------------


def q(s):
    """FSS quoted string with backslash/quote escaping."""
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def vc(local):
    return "vc:" + local


def ru(s):
    return q(s) + "@ru"


def lit(value, dtype):
    return '"%s"^^%s' % (value, dtype)


def annotations(local, label, comment):
    return [
        "AnnotationAssertion(rdfs:label %s %s)" % (vc(local), ru(label)),
        "AnnotationAssertion(rdfs:comment %s %s)" % (vc(local), ru(comment)),
    ]


def decimal_pos():
    return 'DatatypeRestriction(xsd:decimal xsd:minExclusive %s)' % lit(0, "xsd:decimal")


def build(mutation=None):
    L = []
    add = L.append

    add("Prefix(:=<%s>)" % NS)
    add("Prefix(vc:=<%s>)" % NS)
    add("Prefix(owl:=<http://www.w3.org/2002/07/owl#>)")
    add("Prefix(rdf:=<http://www.w3.org/1999/02/22-rdf-syntax-ns#>)")
    add("Prefix(rdfs:=<http://www.w3.org/2000/01/rdf-schema#>)")
    add("Prefix(xsd:=<http://www.w3.org/2001/XMLSchema#>)")
    add("Prefix(xml:=<http://www.w3.org/XML/1998/namespace>)")
    add("")
    add("Ontology(<%s> <%s>" % (ONT_IRI, VERSION_IRI))
    add("")
    add("Annotation(rdfs:label %s)" % ru("Онтология дискретных видеокарт"))
    add("Annotation(rdfs:comment %s)" % ru(
        "Учебная онтология предметной области «Дискретные видеокарты», версия 1.0.0."))
    add("")

    # Declarations
    for c in CLASSES:
        add("Declaration(Class(%s))" % vc(c[0]))
    for c in DEFINED_CLASSES:
        add("Declaration(Class(%s))" % vc(c[0]))
    for p in OBJECT_PROPERTIES:
        add("Declaration(ObjectProperty(%s))" % vc(p[0]))
    add("Declaration(DataProperty(%s))" % vc("name"))
    for p in NUMERIC_PROPERTIES:
        add("Declaration(DataProperty(%s))" % vc(p[0]))
    for ind in D.ALL_INDIVIDUALS:
        add("Declaration(NamedIndividual(%s))" % vc(ind["iri"]))
    add("")

    # Annotations of the TBox
    for c in CLASSES:
        L.extend(annotations(c[0], c[1], c[2]))
    for c in DEFINED_CLASSES:
        L.extend(annotations(*c))
    for p in OBJECT_PROPERTIES:
        L.extend(annotations(p[0], p[1], p[2]))
    L.extend(annotations("name", "название",
                         "Название сущности (строка, единица отсутствует)."))
    for p in NUMERIC_PROPERTIES:
        L.extend(annotations(p[0], p[1], p[2]))
    add("")

    # Class hierarchy
    for c in CLASSES:
        if c[3]:
            add("SubClassOf(%s %s)" % (vc(c[0]), vc(c[3])))
    add("")

    # Disjointness (4.4.2)
    add("DisjointClasses(%s)" % " ".join(vc(x) for x in TOP_LEVEL_DISJOINT))
    add("DisjointClasses(%s)" % " ".join(vc(x) for x in COMPONENT_DISJOINT))
    add("DisjointClasses(%s %s)" % (vc("ActiveCooling"), vc("PassiveCooling")))
    add("")

    # Object properties
    for p in OBJECT_PROPERTIES:
        add("ObjectPropertyDomain(%s %s)" % (vc(p[0]), vc(p[3])))
        add("ObjectPropertyRange(%s %s)" % (vc(p[0]), vc(p[4])))
    add("")

    # Data properties
    add("DataPropertyDomain(%s ObjectUnionOf(%s))"
        % (vc("name"), " ".join(vc(x) for x in NAME_DOMAIN)))
    add("DataPropertyRange(%s xsd:string)" % vc("name"))
    for p in NUMERIC_PROPERTIES:
        name, dom, rng = p[0], p[3], DATA_TYPE[p[0]]
        add("DataPropertyDomain(%s %s)" % (vc(name), vc(dom)))
        if rng == "xsd:decimal":
            add("DataPropertyRange(%s %s)" % (vc(name), decimal_pos()))
        else:
            add("DataPropertyRange(%s %s)" % (vc(name), rng))
        add("FunctionalDataProperty(%s)" % vc(name))
    add("")

    # Restrictions on VideoCardModel (4.4.4, 4.4.5)
    for prop, rng in EXACTLY_ONE:
        add("SubClassOf(%s ObjectExactCardinality(1 %s))" % (vc("VideoCardModel"), vc(prop)))
    for prop, rng in EXACTLY_ONE:
        add("SubClassOf(%s ObjectAllValuesFrom(%s %s))"
            % (vc("VideoCardModel"), vc(prop), vc(rng)))
    add("SubClassOf(%s ObjectMinCardinality(1 %s))" % (vc("VideoCardModel"), vc("hasVideoOutput")))
    add("")

    # Defined classes (4.4.3)
    add("EquivalentClasses(%s ObjectIntersectionOf(%s ObjectSomeValuesFrom(%s "
        "DataSomeValuesFrom(%s DatatypeRestriction(xsd:integer xsd:minInclusive %s)))))"
        % (vc("CardWith8GBMemory"), vc("VideoCardModel"), vc("hasMemory"),
           vc("volumeGiB"), lit(8, "xsd:integer")))
    add("EquivalentClasses(%s ObjectIntersectionOf(%s ObjectSomeValuesFrom(%s %s)))"
        % (vc("CardWithActiveCooling"), vc("VideoCardModel"), vc("hasCooling"),
           vc("ActiveCooling")))
    add("")

    # ABox
    for ind in D.ALL_INDIVIDUALS:
        i = vc(ind["iri"])
        add("ClassAssertion(%s %s)" % (vc(ind["owl_class"]), i))
        L.extend(annotations(ind["iri"], ind["label"], ind["comment"]))
        if "name" in ind:
            add("DataPropertyAssertion(%s %s %s)" % (vc("name"), i, q(ind["name"])))
        for prop in sorted(ind["data"]):
            add("DataPropertyAssertion(%s %s %s)"
                % (vc(prop), i, lit(ind["data"][prop], DATA_TYPE[prop])))
        for prop in sorted(ind["links"]):
            for t in ind["links"][prop]:
                add("ObjectPropertyAssertion(%s %s %s)" % (vc(prop), i, vc(t)))
    add("")
    add("DifferentIndividuals(%s)" % " ".join(vc(i["iri"]) for i in D.ALL_INDIVIDUALS))
    add("")
    add(")")
    if mutation:
        apply_mutation(L, MUTATIONS[mutation])
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mutate", choices=sorted(MUTATIONS), help="emit the negative-test copy for this test id")
    ap.add_argument("output", nargs="?", help="output .fss file (default: stdout)")
    args = ap.parse_args()
    text = build(args.mutate)
    if args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    else:
        sys.stdout.buffer.write(text.encode("utf-8"))


if __name__ == "__main__":
    main()
