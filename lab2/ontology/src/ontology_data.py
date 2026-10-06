"""Teaching dataset for VideoCardOntology v1.0.0 as plain Python data.

Data only: no OWL emission, no reasoner. Task 3 turns these tables into OWL;
make_expected.py derives the fixed expected answers from them.

Each individual is a dict:
    iri      local name in namespace https://example.org/ontologies/videocard#
    kind     data-table kind (see KINDS)
    owl_class  local name of the OWL class for the ClassAssertion
    label    Russian rdfs:label
    comment  Russian rdfs:comment
    name     xsd:string value of data property `name` (only where applicable;
             absent for MemoryConfiguration and CoolingSystem individuals)
    data     {data property local name: python number}; exactly one value each
             (integers for volumeGiB, busWidthBit, fanCount; decimal-valued
             properties frequencyMHz, powerW, lengthMM are given as ints and
             must be emitted as xsd:decimal literals)
    links    {object property local name: [target iri, ...]}

Defined classes CardWith8GBMemory / CardWithActiveCooling are never asserted.
"""

MARKER = "учебная модель"  # annotation marker carried by every U-model comment

# kind -> OWL class local name
KIND_TO_CLASS = {
    "model": "VideoCardModel",
    "manufacturer": "Manufacturer",
    "gpu": "GPUModel",
    "architecture": "GPUArchitecture",
    "interface": "ConnectionInterface",
    "output": "VideoOutput",
    "memory_type": "MemoryType",
    "purpose": "Purpose",
    "memory_config": "MemoryConfiguration",
    # cooling: owl_class is per individual (ActiveCooling / PassiveCooling)
}


def _ind(iri, kind, label, comment, name=None, data=None, links=None, owl_class=None):
    d = {
        "iri": iri,
        "kind": kind,
        "owl_class": owl_class or KIND_TO_CLASS[kind],
        "label": label,
        "comment": comment,
        "data": dict(data or {}),
        "links": {k: list(v) for k, v in (links or {}).items()},
    }
    if name is not None:
        d["name"] = name
    return d


# --- reference individuals ---------------------------------------------------
MANUFACTURERS = [
    _ind("P1", "manufacturer", "Производитель P1",
         "Условный производитель P1 (вымышленные учебные данные).", name="P1"),
    _ind("P2", "manufacturer", "Производитель P2",
         "Условный производитель P2 (вымышленные учебные данные).", name="P2"),
]

ARCHITECTURES = [
    _ind("Arch_A1", "architecture", "Архитектура A1",
         "Условная архитектура графического процессора A1.", name="A1"),
    _ind("Arch_A2", "architecture", "Архитектура A2",
         "Условная архитектура графического процессора A2.", name="A2"),
    _ind("Arch_A3", "architecture", "Архитектура A3",
         "Условная архитектура графического процессора A3.", name="A3"),
]

GPUS = [
    _ind("GPU_G1", "gpu", "Графический процессор G1",
         "Условный графический процессор G1 (учебные данные).", name="G1",
         data={"frequencyMHz": 900},
         links={"hasArchitecture": ["Arch_A1"], "gpuProducedBy": ["P1"]}),
    _ind("GPU_G2", "gpu", "Графический процессор G2",
         "Условный графический процессор G2 (учебные данные).", name="G2",
         data={"frequencyMHz": 1200},
         links={"hasArchitecture": ["Arch_A1"], "gpuProducedBy": ["P1"]}),
    _ind("GPU_G3", "gpu", "Графический процессор G3",
         "Условный графический процессор G3 (учебные данные).", name="G3",
         data={"frequencyMHz": 1500},
         links={"hasArchitecture": ["Arch_A2"], "gpuProducedBy": ["P2"]}),
    _ind("GPU_G4", "gpu", "Графический процессор G4",
         "Условный графический процессор G4 (учебные данные).", name="G4",
         data={"frequencyMHz": 1800},
         links={"hasArchitecture": ["Arch_A2"], "gpuProducedBy": ["P2"]}),
    _ind("GPU_G5", "gpu", "Графический процессор G5",
         "Условный графический процессор G5 (учебные данные).", name="G5",
         data={"frequencyMHz": 2200},
         links={"hasArchitecture": ["Arch_A3"], "gpuProducedBy": ["P2"]}),
]

INTERFACES = [
    _ind("PCIe_3_0_x16", "interface", "PCIe 3.0 x16",
         "Интерфейс подключения PCI Express 3.0 x16.", name="PCIe 3.0 x16"),
    _ind("PCIe_4_0_x16", "interface", "PCIe 4.0 x16",
         "Интерфейс подключения PCI Express 4.0 x16.", name="PCIe 4.0 x16"),
    _ind("PCIe_5_0_x16", "interface", "PCIe 5.0 x16",
         "Интерфейс подключения PCI Express 5.0 x16.", name="PCIe 5.0 x16"),
]

VIDEO_OUTPUTS = [
    _ind("HDMI", "output", "HDMI", "Видеовыход HDMI.", name="HDMI"),
    _ind("DisplayPort", "output", "DisplayPort", "Видеовыход DisplayPort.", name="DisplayPort"),
    _ind("DVI", "output", "DVI", "Видеовыход DVI.", name="DVI"),
    _ind("VGA", "output", "VGA", "Видеовыход VGA.", name="VGA"),
]

MEMORY_TYPES = [
    _ind("GDDR5", "memory_type", "GDDR5", "Тип видеопамяти GDDR5.", name="GDDR5"),
    _ind("GDDR6", "memory_type", "GDDR6", "Тип видеопамяти GDDR6.", name="GDDR6"),
    _ind("GDDR6X", "memory_type", "GDDR6X", "Тип видеопамяти GDDR6X.", name="GDDR6X"),
]

PURPOSES = [
    _ind("Office", "purpose", "Офисное назначение",
         "Назначение: офисная работа.", name="Office"),
    _ind("Gaming", "purpose", "Игровое назначение",
         "Назначение: игры.", name="Gaming"),
    _ind("Workstation", "purpose", "Рабочая станция",
         "Назначение: профессиональная рабочая станция.", name="Workstation"),
]


def _mem(volume, mtype, bus):
    iri = "Mem_%dGiB_%s" % (volume, mtype)
    return _ind(iri, "memory_config",
                "Конфигурация памяти %d ГиБ %s" % (volume, mtype),
                "Конфигурация видеопамяти: %d ГиБ, тип %s, шина %d бит (учебные данные)."
                % (volume, mtype, bus),
                data={"volumeGiB": volume, "busWidthBit": bus},
                links={"hasMemoryType": [mtype]})


MEMORY_CONFIGS = [
    _mem(2, "GDDR5", 64),
    _mem(4, "GDDR5", 128),
    _mem(6, "GDDR6", 192),
    _mem(8, "GDDR6", 256),    # shared by U02 and U06
    _mem(12, "GDDR6", 192),
    _mem(16, "GDDR6", 256),
    _mem(24, "GDDR6X", 384),
]

COOLINGS = [
    _ind("Cooling_Passive", "cooling", "Пассивное охлаждение",
         "Пассивная система охлаждения без вентиляторов.",
         data={"fanCount": 0}, owl_class="PassiveCooling"),
    _ind("Cooling_Active_2fan", "cooling", "Активное охлаждение, 2 вентилятора",
         "Активная система охлаждения с двумя вентиляторами.",
         data={"fanCount": 2}, owl_class="ActiveCooling"),
    _ind("Cooling_Active_3fan", "cooling", "Активное охлаждение, 3 вентилятора",
         "Активная система охлаждения с тремя вентиляторами.",
         data={"fanCount": 3}, owl_class="ActiveCooling"),
]

# --- the 8 teaching models ---------------------------------------------------
# (iri, gpu, memory config, cooling, interface, manufacturer, outputs, purpose,
#  powerW, lengthMM) -- memory/cooling/type/manufacturer fixed by Table 5.
_MODEL_ROWS = [
    ("U01", "GPU_G1", "Mem_4GiB_GDDR5", "Cooling_Passive", "PCIe_3_0_x16", "P1",
     ["HDMI", "VGA"], "Office", 40, 160),
    ("U02", "GPU_G2", "Mem_8GiB_GDDR6", "Cooling_Active_2fan", "PCIe_4_0_x16", "P1",
     ["HDMI", "DisplayPort"], "Gaming", 150, 240),
    ("U03", "GPU_G3", "Mem_12GiB_GDDR6", "Cooling_Active_2fan", "PCIe_4_0_x16", "P2",
     ["HDMI", "DisplayPort"], "Gaming", 185, 265),
    ("U04", "GPU_G4", "Mem_16GiB_GDDR6", "Cooling_Active_3fan", "PCIe_4_0_x16", "P2",
     ["HDMI", "DisplayPort"], "Workstation", 260, 310),
    ("U05", "GPU_G2", "Mem_6GiB_GDDR6", "Cooling_Active_2fan", "PCIe_3_0_x16", "P1",
     ["HDMI", "DVI"], "Office", 120, 220),
    ("U06", "GPU_G3", "Mem_8GiB_GDDR6", "Cooling_Passive", "PCIe_3_0_x16", "P2",
     ["HDMI", "DVI"], "Office", 75, 200),
    ("U07", "GPU_G5", "Mem_24GiB_GDDR6X", "Cooling_Active_3fan", "PCIe_5_0_x16", "P2",
     ["DisplayPort", "HDMI"], "Workstation", 350, 336),
    ("U08", "GPU_G1", "Mem_2GiB_GDDR5", "Cooling_Passive", "PCIe_3_0_x16", "P1",
     ["VGA", "DVI"], "Office", 30, 145),
]

MODELS = [
    _ind(iri, "model", "Видеокарта %s" % iri,
         "Видеокарта %s — %s." % (iri, MARKER),
         name=iri,
         data={"powerW": power, "lengthMM": length},
         links={
             "usesGPU": [gpu],
             "hasMemory": [mem],
             "hasCooling": [cool],
             "hasInterface": [iface],
             "producedByManufacturer": [man],
             "hasVideoOutput": outs,
             "hasPurpose": [purpose],
         })
    for (iri, gpu, mem, cool, iface, man, outs, purpose, power, length) in _MODEL_ROWS
]

# --- aggregate views for Task 3 ----------------------------------------------
# Order: reference individuals, components, models. One DifferentIndividuals
# axiom must cover exactly ALL_INDIVIDUALS.
ALL_INDIVIDUALS = (
    MANUFACTURERS + ARCHITECTURES + INTERFACES + VIDEO_OUTPUTS + MEMORY_TYPES
    + PURPOSES + GPUS + MEMORY_CONFIGS + COOLINGS + MODELS
)

BY_KIND = {
    "manufacturer": MANUFACTURERS,
    "architecture": ARCHITECTURES,
    "interface": INTERFACES,
    "output": VIDEO_OUTPUTS,
    "memory_type": MEMORY_TYPES,
    "purpose": PURPOSES,
    "gpu": GPUS,
    "memory_config": MEMORY_CONFIGS,
    "cooling": COOLINGS,
    "model": MODELS,
}

BY_IRI = {i["iri"]: i for i in ALL_INDIVIDUALS}


def _check_integrity():
    assert len(BY_IRI) == len(ALL_INDIVIDUALS), "duplicate individual IRIs"
    for ind in ALL_INDIVIDUALS:
        for prop, targets in ind["links"].items():
            for t in targets:
                assert t in BY_IRI, "dangling link %s -%s-> %s" % (ind["iri"], prop, t)


_check_integrity()
