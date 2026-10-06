# Протокол испытаний VideoCardOntology v1.0.0

Протокол по разделу 8 и пункту 5 (подпункт 5) ТЗ: среда и версии, ожидаемые и фактические результаты, статус каждого
испытания T01–T11, критические замечания к ТЗ, дефекты. Фактические результаты скопированы без изменений из
`tests/results/T01.log … T11.log` последнего (финального) запуска `bash tests/run_tests.sh`.

## 1. Объект и среда испытаний

| Параметр | Значение |
|---|---|
| Объект | `ontology/videocard.owl`, VideoCardOntology 1.0.0 |
| IRI / Version IRI | `https://example.org/ontologies/videocard` / `https://example.org/ontologies/videocard/1.0.0` |
| Формат файла | RDF/XML, UTF-8, 64769 байт, 472 аксиом |
| SHA-256 файла | `d8ac600a45ce642deee38be726ae5d0d81f9e47967a9e1bb07a66b5005ae3661` |
| Дата испытаний | 2026-10-06 |
| Испытатель | автоматический прогон `bash tests/run_tests.sh` (Java-оснастка), без участия Protégé |
| OWL API | 4.5.29 (полная версия сборки: 4.5.29.2024-05-13T12:11:03Z) |
| HermiT | jar 1.4.3.456; `Reasoner.getReasonerVersion()` самоопределяется как 1.4.1.432 (устаревшая константа внутри jar, не версия запускаемого кода) |
| Java | 17.0.2 (Eclipse Adoptium) |
| ОС | Mac OS X 26.6.2 aarch64 |
| Генератор онтологии | Python 3.12.4, только стандартная библиотека |
| Контрольная среда ТЗ (Protégé) | Protégé Desktop 5.6.9 + HermiT — запуск и снимки экрана выполняет пользователь (раздел 4); в этом прогоне Protégé не использовался |

Заголовок запуска, напечатанный оснасткой (первые шесть строк `tests/results/run_tests.log`, без изменений):

```text
VideoCardOntology v1.0.0 test run
OWL API:  4.5.29.2024-05-13T12:11:03Z
HermiT:   1.4.3.456 (Reasoner.getReasonerVersion() self-reports 1.4.1.432)
Java:     17.0.2 (Eclipse Adoptium)
OS:       Mac OS X 26.6.2 aarch64
videocard.owl SHA-256: d8ac600a45ce642deee38be726ae5d0d81f9e47967a9e1bb07a66b5005ae3661
```

Версии OWL API 4.5.29 и HermiT 1.4.3.456 закреплены в `tests/harness/fetch_libs.sh`, Java и ОС взяты из заголовка выше;
тест T11 проверяет, что среда выполнения соответствует закреплённым версиям.

## 2. Методика

- Все испытания выполняет единый запуск `bash tests/run_tests.sh`: загрузка закреплённых jar-файлов, компиляция
  оснастки (`tests/harness/src`), последовательный запуск групп T01–T11 с журналами `tests/results/Tnn.log` и итогом
  `tests/results/summary.json`.
- Эталоны (`tests/expected.json`) и таблицы требований (Oracle в оснастке) заданы независимо от испытуемой онтологии:
  эталоны записаны скриптом `make_expected.py` из `ontology_data.py` до запуска reasoner на финальной онтологии;
  Oracle — литеральные таблицы 1–3 и пунктов 4.4.x ТЗ.
- Запросы T05 выполняются в синтаксисе Manchester по локальным именам (как в DL Query Protégé) через
  `reasoner.getInstances(выражение, false)` HermiT; сравнивается точное равенство множеств.
- Отрицательные тесты T06–T09 работают на отдельных копиях `tests/negative/*.owl`, полученных из того же генератора
  (`build.sh --mutate`) минимальной правкой; каждый журнал называет файл копии и показывает разницу аксиом с финальной
  онтологией, затем проверяет откат (финальная онтология согласована и тестовых фактов не содержит).
- Каждое испытание ниже содержит исходные условия, действия, ожидаемый результат, фактический результат и статус.

## 3. Результаты испытаний

Сводка (из `tests/results/summary.json` и последней строки журналов):

| Тест | Что проверяется | Пункты ТЗ | Статус |
|---|---|---|---|
| T01 | Обязательные понятия, свойства; сверка описания, словаря и схем | 4.1.1–4.1.4 | ПРОЙДЕН |
| T02 | Состав сущностей, domain/range, OWL 2 DL, аннотации | 4.2.1–4.2.4; 4.4.1 | ПРОЙДЕН |
| T03 | Карточка полноты восьми моделей | 4.2.5; 4.4.4–4.4.5 | ПРОЙДЕН |
| T04 | Согласованность и выполнимость классов (HermiT) | 4.4.2; 4.4.6 | ПРОЙДЕН |
| T05 | Восемь контрольных запросов DL Query, точные наборы | 4.3; 4.4.3 | ПРОЙДЕН |
| T06 | Отрицательный: индивид в ActiveCooling и PassiveCooling | 4.4.2; 4.4.6 | ПРОЙДЕН |
| T07 | Отрицательный: модель с двумя GPU (exactly 1) | 4.4.4; 4.4.7 | ПРОЙДЕН |
| T08 | Отрицательный: отрицательный объём integer при range positiveInteger | 4.2.3 | ПРОЙДЕН |
| T09 | Отрицательный: у модели удалено hasMemory (открытый мир) | 4.4.5; 4.4.7 | ПРОЙДЕН |
| T10 | Сохранение, повторное открытие, повтор T04/T05 | 4.5.1; 4.5.3; 4.6.3 | ПРОЙДЕН |
| T11 | Состав поставки, версии среды, README, протокол | 4.5.2; 4.6.1–4.6.4; 5 | ПРОЙДЕН |

### T01. Обязательные понятия, свойства; сверка описания, словаря и схем

- **Пункты ТЗ:** 4.1.1–4.1.4
- **Исходные условия:** `ontology/videocard.owl` (SHA-256 в README); ТЗ, таблицы 1–3, рис. 1–2 (приложение 1 ТЗ).
- **Действия:** автоматически: проверка по IRI наличия 13 + 2 классов, 10 объектных и 7 свойств данных; вручную: сверка описания, словаря и обеих диаграмм (`docs/ontology_description.md`, раздел 12).
- **Критерий успешности (таблица 6 ТЗ):** границы заданы; все обязательные понятия определены; схемы согласованы с таблицами 1–3; указаны источники.
- **Ожидаемый результат:** 15/15 классов, 10/10 объектных свойств, 7/7 свойств данных; чек-лист ручной сверки заполнен.

**Фактический результат** (из `tests/results/T01.log`, без изменений):

```text
== T01 required classes and properties (automatic part) ==
  [PASS] required classes declared: VideoCardModel, ModelComponent, GPUModel, MemoryConfiguration, CoolingSystem, ActiveCooling, PassiveCooling, Manufacturer, ConnectionInterface, VideoOutput, MemoryType, GPUArchitecture, Purpose, CardWith8GBMemory, CardWithActiveCooling (15/15)
  [PASS] required object properties declared: usesGPU, hasMemory, hasCooling, hasInterface, hasVideoOutput, producedByManufacturer, gpuProducedBy, hasArchitecture, hasMemoryType, hasPurpose (10/10)
  [PASS] required data properties declared: name, volumeGiB, busWidthBit, frequencyMHz, powerW, lengthMM, fanCount (7/7)

Status: AUTOMATIC PART PASS. The manual reconciliation of the description, vocabulary and both diagrams (4.1.1-4.1.4) is recorded in docs/ontology_description.md (written in Task 7) and is not evaluated here.
T01: PASS
```

**Ручная часть** выполнена по `docs/ontology_description.md`, раздел 12: границы, термины, определения, единицы — готовы; обе диаграммы просмотрены по изображениям, отмечены расхождения типов `int`/`integer` с таблицей 3 и метки «вентиляторы» (подробно — разделы «Критические замечания» и 12.4 описания); неполнота диаграмм относительно таблиц 1–2 объявлена подписями рисунков. Источники для реальных моделей не требуются (данные вымышлены, отступление принято решением заказчика). Статус ниже относится к автоматической части; ручная часть пройдена с перечисленными замечаниями.

**Статус: ПРОЙДЕН**


### T02. Состав сущностей, domain/range, OWL 2 DL, аннотации

- **Пункты ТЗ:** 4.2.1–4.2.4; 4.4.1
- **Исходные условия:** `ontology/videocard.owl` (SHA-256 в README).
- **Действия:** открыть файл (OWL API), проверить профиль OWL 2 DL, состав сущностей, domain/range, ограничения, метки и комментарии.
- **Критерий успешности (таблица 6 ТЗ):** все обязательные классы и свойства присутствуют; domain/range корректны; OWL 2 DL; есть метки и определения.
- **Ожидаемый результат:** 26 проверок PASS; 0 нарушений OWL 2 DL; 13 + 2 классов, 10 + 7 свойств, 41 индивид; domain/range 20/20 и 13/13; 5/5/1 ограничений; 32/32 пары непересекаемости; одна аксиома DifferentIndividuals на все 41 индивид.

**Фактический результат** (из `tests/results/T02.log`, без изменений):

```text
== T02 ontology structure, OWL 2 DL profile, annotations ==
  [PASS] file ontology/videocard.owl parses
axiom count: 472
  [PASS] OWL2DLProfile reports no violations (0 found)
  [PASS] no owl:imports declarations
  [PASS] ontology IRI
  [PASS] version IRI
entity counts: classes=15, object properties=10, data properties=7, individuals=41
  classes (15): ActiveCooling, CardWith8GBMemory, CardWithActiveCooling, ConnectionInterface, CoolingSystem, GPUArchitecture, GPUModel, Manufacturer, MemoryConfiguration, MemoryType, ModelComponent, PassiveCooling, Purpose, VideoCardModel, VideoOutput
  object properties (10): gpuProducedBy, hasArchitecture, hasCooling, hasInterface, hasMemory, hasMemoryType, hasPurpose, hasVideoOutput, producedByManufacturer, usesGPU
  data properties (7): busWidthBit, fanCount, frequencyMHz, lengthMM, name, powerW, volumeGiB
  individuals (41): Arch_A1, Arch_A2, Arch_A3, Cooling_Active_2fan, Cooling_Active_3fan, Cooling_Passive, DVI, DisplayPort, GDDR5, GDDR6, GDDR6X, GPU_G1, GPU_G2, GPU_G3, GPU_G4, GPU_G5, Gaming, HDMI, Mem_12GiB_GDDR6, Mem_16GiB_GDDR6, Mem_24GiB_GDDR6X, Mem_2GiB_GDDR5, Mem_4GiB_GDDR5, Mem_6GiB_GDDR6, Mem_8GiB_GDDR6, Office, P1, P2, PCIe_3_0_x16, PCIe_4_0_x16, PCIe_5_0_x16, U01, U02, U03, U04, U05, U06, U07, U08, VGA, Workstation
  [PASS] classes in signature are exactly the 13 + 2 required
  [PASS] object properties in signature are exactly the 10 required
  [PASS] data properties in signature are exactly the 7 required
  [PASS] individuals include U01..U08
  [PASS] every user entity lives in the single namespace https://example.org/ontologies/videocard#
  [PASS] asserted class hierarchy (5/5)
  [PASS] domain and range of the 10 object properties exactly as in Table 2 (20/20)
  [PASS] no object property is functional
  [PASS] name has exactly one domain axiom: ObjectUnionOf of the 8 classes
  [PASS] domain and range of the 7 data properties as in Table 3 (decimal > 0 = minExclusive 0) (13/13)
  [PASS] functional data properties are exactly the six numeric ones
  [PASS] every class, property and individual has an rdfs:label@ru and an rdfs:comment@ru (73/73)
  [PASS] VideoCardModel: 5 ExactCardinality(1) and 5 AllValuesFrom restrictions (10/10)
  [PASS] VideoCardModel: MinCardinality(1) hasVideoOutput
  [PASS] VideoCardModel carries exactly 5 exact / 5 only / 1 min restrictions (found 5/5/1)
  [PASS] asserted DisjointClasses for the required 4.4.2 pairs (8 top-level, 3 component kinds, Active/Passive) (32/32)
  [PASS] CardWith8GBMemory == VideoCardModel and hasMemory some (volumeGiB some xsd:integer[>= 8])
  [PASS] CardWithActiveCooling == VideoCardModel and hasCooling some ActiveCooling
  [PASS] exactly one DifferentIndividuals/AllDifferent axiom
  [PASS] the DifferentIndividuals axiom covers all 41 named individuals
  [PASS] no SameIndividual axioms
T02: PASS
```

**Статус: ПРОЙДЕН**


### T03. Карточка полноты восьми моделей

- **Пункты ТЗ:** 4.2.5; 4.4.4–4.4.5
- **Исходные условия:** `ontology/videocard.owl` (SHA-256 в README).
- **Действия:** построить карточку полноты по явно записанным аксиомам U01–U08 (без reasoner).
- **Критерий успешности (таблица 6 ТЗ):** в каждой карточке есть обязательные связи; пять единичных связей заданы ровно одним значением; видеовыходов не менее одного.
- **Ожидаемый результат:** 8 моделей × 12 столбцов полны: по 1 значению в usesGPU, hasMemory, hasCooling, hasInterface, producedByManufacturer, powerW, lengthMM, volumeGiB, busWidthBit, frequencyMHz, fanCount и 2 значения hasVideoOutput.

**Фактический результат** (из `tests/results/T03.log`, без изменений):

```text
== T03 completeness card of U01..U08 (asserted axioms only) ==
Completeness card (cell = number of asserted values; '*' marks a violation; '-' = component not reachable through a single link)
  model usesGPU hasMemory hasCooling hasInterface producedByManufacturer hasVideoOutput powerW lengthMM volumeGiB busWidthBit frequencyMHz fanCount
  U01         1         1          1            1                      1              2      1        1         1           1            1        1
  U02         1         1          1            1                      1              2      1        1         1           1            1        1
  U03         1         1          1            1                      1              2      1        1         1           1            1        1
  U04         1         1          1            1                      1              2      1        1         1           1            1        1
  U05         1         1          1            1                      1              2      1        1         1           1            1        1
  U06         1         1          1            1                      1              2      1        1         1           1            1        1
  U07         1         1          1            1                      1              2      1        1         1           1            1        1
  U08         1         1          1            1                      1              2      1        1         1           1            1        1

Rule: exactly 1 value for usesGPU, hasMemory, hasCooling, hasInterface, producedByManufacturer; >= 1 for hasVideoOutput; exactly 1 for powerW, lengthMM (model), volumeGiB, busWidthBit (memory), frequencyMHz (GPU), fanCount (cooling).
  [PASS] every model U01..U08 is complete (0 problem(s))
T03: PASS
```

**Статус: ПРОЙДЕН**


### T04. Согласованность и выполнимость классов (HermiT)

- **Пункты ТЗ:** 4.4.2; 4.4.6
- **Исходные условия:** `ontology/videocard.owl` (SHA-256 в README); reasoner HermiT (jar 1.4.3.456).
- **Действия:** запустить HermiT на финальной версии: isConsistent, список неудовлетворимых классов, isSatisfiable по каждому классу, выводимость непересекаемости.
- **Критерий успешности (таблица 6 ТЗ):** онтология согласована; ни один именованный пользовательский класс не выведен подклассом owl:Nothing.
- **Ожидаемый результат:** isConsistent = true; единственный неудовлетворимый класс — owl:Nothing; 16/16 классов выполнимы (15 + owl:Thing); 32/32 пары непересекаемости выводятся.

**Фактический результат** (из `tests/results/T04.log`, без изменений):

```text
== T04 HermiT consistency and class satisfiability ==
reasoner: HermiT 1.4.1.432 (self-reported; jar version 1.4.3.456)
  [PASS] ontology is consistent (isConsistent)
unsatisfiable classes (equivalent to owl:Nothing): [owl:Nothing]
  [PASS] the only unsatisfiable class is owl:Nothing
per-class isSatisfiable: ActiveCooling=sat, CardWith8GBMemory=sat, CardWithActiveCooling=sat, ConnectionInterface=sat, CoolingSystem=sat, GPUArchitecture=sat, GPUModel=sat, Manufacturer=sat, MemoryConfiguration=sat, MemoryType=sat, ModelComponent=sat, PassiveCooling=sat, Purpose=sat, VideoCardModel=sat, VideoOutput=sat, owl:Thing=sat
  [PASS] every named class is individually satisfiable (16/16)
  [PASS] reasoner entails disjointness of the required 4.4.2 pairs (32/32)
T04: PASS
```

Примечание: `Reasoner.getReasonerVersion()` в этом jar возвращает устаревшую константу 1.4.1.432; фактическая версия reasoner — по jar 1.4.3.456 (см. раздел «Среда» и «Дефекты»).

**Статус: ПРОЙДЕН**


### T05. Восемь контрольных запросов DL Query, точные наборы

- **Пункты ТЗ:** 4.3; 4.4.3
- **Исходные условия:** `ontology/videocard.owl` (SHA-256 в README); эталоны `tests/expected.json`, записанные до запуска reasoner.
- **Действия:** выполнить восемь запросов (для вопросов с аргументом — по каждому аргументу), сравнить точные наборы IRI с эталоном, проверить отсутствие ручных ClassAssertion в определяемые классы.
- **Критерий успешности (таблица 6 ТЗ):** все наборы совпадают с эталоном; принадлежность двум определяемым классам получена выводом, а не ручным назначением.
- **Ожидаемый результат:** точное равенство множеств для всех запросов (39/39 проверок) и ноль ClassAssertion в CardWith8GBMemory и CardWithActiveCooling. Полный журнал с ожидаемыми и фактическими наборами для каждого вопроса:

**Фактический результат** (из `tests/results/T05.log`, без изменений):

```text
== T05 eight DL queries vs tests/expected.json ==
  [PASS] no ClassAssertion axiom for CardWith8GBMemory (found 0); membership must be inferred
  [PASS] no ClassAssertion axiom for CardWithActiveCooling (found 0); membership must be inferred
  [PASS] ontology is consistent (queries are meaningful)
  [PASS] Q1: expected.json covers exactly the arguments [P1, P2]
Q1 [P1]
    query:    VideoCardModel and producedByManufacturer value P1
    expected: [U01, U02, U05, U08]
    actual:   [U01, U02, U05, U08]
  [PASS] Q1 [P1] exact set equality
Q1 [P2]
    query:    VideoCardModel and producedByManufacturer value P2
    expected: [U03, U04, U06, U07]
    actual:   [U03, U04, U06, U07]
  [PASS] Q1 [P2] exact set equality
  [PASS] Models produced by a given manufacturer: representative P1 has positive example U01 (member) and negative example U03 (non-member)
  [PASS] Q2: expected.json covers exactly the arguments [GPU_G1, GPU_G2, GPU_G3, GPU_G4, GPU_G5]
Q2 [GPU_G1]
    query:    VideoCardModel and usesGPU value GPU_G1
    expected: [U01, U08]
    actual:   [U01, U08]
  [PASS] Q2 [GPU_G1] exact set equality
Q2 [GPU_G2]
    query:    VideoCardModel and usesGPU value GPU_G2
    expected: [U02, U05]
    actual:   [U02, U05]
  [PASS] Q2 [GPU_G2] exact set equality
Q2 [GPU_G3]
    query:    VideoCardModel and usesGPU value GPU_G3
    expected: [U03, U06]
    actual:   [U03, U06]
  [PASS] Q2 [GPU_G3] exact set equality
Q2 [GPU_G4]
    query:    VideoCardModel and usesGPU value GPU_G4
    expected: [U04]
    actual:   [U04]
  [PASS] Q2 [GPU_G4] exact set equality
Q2 [GPU_G5]
    query:    VideoCardModel and usesGPU value GPU_G5
    expected: [U07]
    actual:   [U07]
  [PASS] Q2 [GPU_G5] exact set equality
  [PASS] Models using a given GPU: representative GPU_G3 has positive example U03 (member) and negative example U01 (non-member)
  [PASS] Q4: expected.json covers exactly the arguments [GDDR5, GDDR6, GDDR6X]
Q4 [GDDR5]
    query:    VideoCardModel and hasMemory some (hasMemoryType value GDDR5)
    expected: [U01, U08]
    actual:   [U01, U08]
  [PASS] Q4 [GDDR5] exact set equality
Q4 [GDDR6]
    query:    VideoCardModel and hasMemory some (hasMemoryType value GDDR6)
    expected: [U02, U03, U04, U05, U06]
    actual:   [U02, U03, U04, U05, U06]
  [PASS] Q4 [GDDR6] exact set equality
Q4 [GDDR6X]
    query:    VideoCardModel and hasMemory some (hasMemoryType value GDDR6X)
    expected: [U07]
    actual:   [U07]
  [PASS] Q4 [GDDR6X] exact set equality
  [PASS] Models with a given memory type: representative GDDR6 has positive example U02 (member) and negative example U01 (non-member)
  [PASS] Q6: expected.json covers exactly the arguments [DVI, DisplayPort, HDMI, VGA]
Q6 [DVI]
    query:    VideoCardModel and hasVideoOutput value DVI
    expected: [U05, U06, U08]
    actual:   [U05, U06, U08]
  [PASS] Q6 [DVI] exact set equality
Q6 [DisplayPort]
    query:    VideoCardModel and hasVideoOutput value DisplayPort
    expected: [U02, U03, U04, U07]
    actual:   [U02, U03, U04, U07]
  [PASS] Q6 [DisplayPort] exact set equality
Q6 [HDMI]
    query:    VideoCardModel and hasVideoOutput value HDMI
    expected: [U01, U02, U03, U04, U05, U06, U07]
    actual:   [U01, U02, U03, U04, U05, U06, U07]
  [PASS] Q6 [HDMI] exact set equality
Q6 [VGA]
    query:    VideoCardModel and hasVideoOutput value VGA
    expected: [U01, U08]
    actual:   [U01, U08]
  [PASS] Q6 [VGA] exact set equality
  [PASS] Models having a given video output: representative DVI has positive example U05 (member) and negative example U01 (non-member)
  [PASS] Q7: expected.json covers exactly the arguments [PCIe_3_0_x16, PCIe_4_0_x16, PCIe_5_0_x16]
Q7 [PCIe_3_0_x16]
    query:    VideoCardModel and hasInterface value PCIe_3_0_x16
    expected: [U01, U05, U06, U08]
    actual:   [U01, U05, U06, U08]
  [PASS] Q7 [PCIe_3_0_x16] exact set equality
Q7 [PCIe_4_0_x16]
    query:    VideoCardModel and hasInterface value PCIe_4_0_x16
    expected: [U02, U03, U04]
    actual:   [U02, U03, U04]
  [PASS] Q7 [PCIe_4_0_x16] exact set equality
Q7 [PCIe_5_0_x16]
    query:    VideoCardModel and hasInterface value PCIe_5_0_x16
    expected: [U07]
    actual:   [U07]
  [PASS] Q7 [PCIe_5_0_x16] exact set equality
  [PASS] Models with a given connection interface: representative PCIe_4_0_x16 has positive example U02 (member) and negative example U01 (non-member)
  [PASS] Q3: expected.json has a non-empty list
Q3 (defined classes)
    query:    CardWith8GBMemory
    expected: [U02, U03, U04, U06, U07]
    actual:   [U02, U03, U04, U06, U07]
  [PASS] Q3 (defined classes) exact set equality
Q3 (raw cross-check)
    query:    VideoCardModel and hasMemory some (volumeGiB some xsd:integer[>= 8])
    expected: [U02, U03, U04, U06, U07]
    actual:   [U02, U03, U04, U06, U07]
  [PASS] Q3 (raw cross-check) exact set equality
  [PASS] Q5: expected.json has a non-empty list
Q5 (defined classes)
    query:    CardWithActiveCooling
    expected: [U02, U03, U04, U05, U07]
    actual:   [U02, U03, U04, U05, U07]
  [PASS] Q5 (defined classes) exact set equality
Q5 (raw cross-check)
    query:    VideoCardModel and hasCooling some ActiveCooling
    expected: [U02, U03, U04, U05, U07]
    actual:   [U02, U03, U04, U05, U07]
  [PASS] Q5 (raw cross-check) exact set equality
  [PASS] Q8: expected.json has a non-empty list
Q8 (defined classes)
    query:    CardWith8GBMemory and CardWithActiveCooling
    expected: [U02, U03, U04, U07]
    actual:   [U02, U03, U04, U07]
  [PASS] Q8 (defined classes) exact set equality
Q8 (raw cross-check)
    query:    VideoCardModel and hasMemory some (volumeGiB some xsd:integer[>= 8]) and hasCooling some ActiveCooling
    expected: [U02, U03, U04, U07]
    actual:   [U02, U03, U04, U07]
  [PASS] Q8 (raw cross-check) exact set equality
T05: PASS
```

**Статус: ПРОЙДЕН**


### T06. Отрицательный: индивид в ActiveCooling и PassiveCooling

- **Пункты ТЗ:** 4.4.2; 4.4.6
- **Исходные условия:** тестовая копия `tests/negative/T06_active_and_passive.owl` (отличается от финальной ровно одной аксиомой) и финальная онтология.
- **Действия:** в копии отнести индивид `Cooling_Active_2fan` к ActiveCooling и PassiveCooling; повторить вывод; проверить финальную онтологию.
- **Критерий успешности (таблица 6 ТЗ):** reasoner сообщает несогласованность копии; финальная модель согласована, тестовых аксиом в ней нет.
- **Ожидаемый результат:** копия: isConsistent = false; финальная: isConsistent = true, `Cooling_Active_2fan` не PassiveCooling.

**Фактический результат** (из `tests/results/T06.log`, без изменений):

```text
== T06 negative: individual in ActiveCooling and PassiveCooling ==
defect copy: tests/negative/T06_active_and_passive.owl
  [PASS] defect copy file exists

-- the copy differs from ontology/videocard.owl only by the intended mutation
    + ClassAssertion(<https://example.org/ontologies/videocard#PassiveCooling> <https://example.org/ontologies/videocard#Cooling_Active_2fan>)
  [PASS] axioms only in the copy (+1)
  [PASS] axioms only in the final ontology (-0)

-- defect copy
  [PASS] Cooling_Active_2fan is asserted ActiveCooling and PassiveCooling in the copy
  expected: inconsistent=true (ActiveCooling and PassiveCooling are disjoint)
    HermiT 1.4.3.456 isConsistent = false
  [PASS] HermiT reports the copy inconsistent (negative control: the reasoner detects inconsistency)

-- rollback: ontology/videocard.owl
  expected: consistent=true
    HermiT 1.4.3.456 isConsistent = true
  [PASS] HermiT reports the final ontology consistent
  [PASS] Cooling_Active_2fan is not asserted PassiveCooling in the final ontology
  [PASS] Cooling_Active_2fan is still asserted ActiveCooling in the final ontology
  [PASS] no individual is asserted both ActiveCooling and PassiveCooling in the final ontology
T06: PASS
```

**Статус: ПРОЙДЕН**


### T07. Отрицательный: модель с двумя GPU (exactly 1)

- **Пункты ТЗ:** 4.4.4; 4.4.7
- **Исходные условия:** тестовая копия `tests/negative/T07_two_gpus.owl` и финальная онтология.
- **Действия:** в копии связать U01 вторым GPU (`GPU_G2`) при уже различных GPU (DifferentIndividuals); повторить вывод.
- **Критерий успешности (таблица 6 ТЗ):** из-за exactly 1 reasoner обнаруживает несогласованность; после отката финальная версия согласована.
- **Ожидаемый результат:** копия: isConsistent = false; финальная: isConsistent = true, у каждой модели ровно один usesGPU.

**Фактический результат** (из `tests/results/T07.log`, без изменений):

```text
== T07 negative: model linked to two different GPUs (usesGPU exactly 1) ==
defect copy: tests/negative/T07_two_gpus.owl
  [PASS] defect copy file exists

-- the copy differs from ontology/videocard.owl only by the intended mutation
    + ObjectPropertyAssertion(<https://example.org/ontologies/videocard#usesGPU> <https://example.org/ontologies/videocard#U01> <https://example.org/ontologies/videocard#GPU_G2>)
  [PASS] axioms only in the copy (+1)
  [PASS] axioms only in the final ontology (-0)

-- defect copy
  [PASS] U01 usesGPU values in the copy
  expected: inconsistent=true (usesGPU exactly 1 on VideoCardModel, GPUs pairwise different)
    HermiT 1.4.3.456 isConsistent = false
  [PASS] HermiT reports the copy inconsistent

-- rollback: ontology/videocard.owl
  expected: consistent=true
    HermiT 1.4.3.456 isConsistent = true
  [PASS] HermiT reports the final ontology consistent
  [PASS] U01 usesGPU values in the final ontology
  [PASS] every model has exactly one asserted usesGPU value in the final ontology
T07: PASS
```

**Статус: ПРОЙДЕН**


### T08. Отрицательный: отрицательный объём integer при range positiveInteger

- **Пункты ТЗ:** 4.2.3
- **Исходные условия:** тестовая копия `tests/negative/T08_negative_volume.owl` и финальная онтология.
- **Действия:** в копии заменить volumeGiB у `Mem_4GiB_GDDR5` значением -8 типа xsd:integer (range — positiveInteger); повторить вывод; дополнительно — вариант без range-аксиомы в памяти.
- **Критерий успешности (таблица 6 ТЗ):** reasoner выявляет несовместимое с диапазоном значение; тестового факта в финальном файле нет.
- **Ожидаемый результат:** копия: isConsistent = false (причина — range, подтверждено вариантом без range-аксиомы: consistent); финальная: isConsistent = true, значение 4 типа xsd:positiveInteger.

**Фактический результат** (из `tests/results/T08.log`, без изменений):

```text
== T08 negative: negative volumeGiB typed xsd:integer vs range xsd:positiveInteger ==
defect copy: tests/negative/T08_negative_volume.owl
  [PASS] defect copy file exists

-- the copy differs from ontology/videocard.owl only by the intended mutation
    - DataPropertyAssertion(<https://example.org/ontologies/videocard#volumeGiB> <https://example.org/ontologies/videocard#Mem_4GiB_GDDR5> "4"^^xsd:positiveInteger)
    + DataPropertyAssertion(<https://example.org/ontologies/videocard#volumeGiB> <https://example.org/ontologies/videocard#Mem_4GiB_GDDR5> "-8"^^xsd:integer)
  [PASS] axioms only in the copy (+1)
  [PASS] axioms only in the final ontology (-1)

-- defect copy
  volumeGiB of Mem_4GiB_GDDR5 in the copy: ["-8"^^xsd:integer]
  [PASS] exactly one volumeGiB value (replaced, not added: functionality is not violated)
  expected: inconsistent=true (value -8 is not in the range xsd:positiveInteger)
    HermiT 1.4.3.456 isConsistent = false
  [PASS] HermiT reports the copy inconsistent
  [PASS] the copy has one DataPropertyRange axiom for volumeGiB
  in-memory variant without the volumeGiB range axiom (not written to disk):
    HermiT 1.4.3.456 isConsistent = true
  [PASS] without the range axiom HermiT finds the variant consistent: the range axiom is the only cause

-- rollback: ontology/videocard.owl
  expected: consistent=true
    HermiT 1.4.3.456 isConsistent = true
  [PASS] HermiT reports the final ontology consistent
  volumeGiB of Mem_4GiB_GDDR5 in the final ontology: ["4"^^xsd:positiveInteger]
  [PASS] Mem_4GiB_GDDR5 volumeGiB in the final ontology is the original positive value
  [PASS] no negative or non-positiveInteger volumeGiB literal anywhere in the final ontology
T08: PASS
```

**Статус: ПРОЙДЕН**


### T09. Отрицательный: у модели удалено hasMemory (открытый мир)

- **Пункты ТЗ:** 4.4.5; 4.4.7
- **Исходные условия:** тестовая копия `tests/negative/T09_missing_hasMemory.owl` и финальная онтология.
- **Действия:** в копии удалить связь hasMemory у U05; проверить reasoner и карточку полноты.
- **Критерий успешности (таблица 6 ТЗ):** карточка фиксирует пропуск; согласованность reasoner сама по себе не засчитывается как полнота; связь в финальном файле восстановлена.
- **Ожидаемый результат:** копия: isConsistent = true (открытый мир), карточка отмечает U05 hasMemory `0*`; финальная: согласована, карточка без замечаний.

**Фактический результат** (из `tests/results/T09.log`, без изменений):

```text
== T09 negative: model without hasMemory (open world vs completeness card) ==
defect copy: tests/negative/T09_missing_hasMemory.owl
  [PASS] defect copy file exists

-- the copy differs from ontology/videocard.owl only by the intended mutation
    - ObjectPropertyAssertion(<https://example.org/ontologies/videocard#hasMemory> <https://example.org/ontologies/videocard#U05> <https://example.org/ontologies/videocard#Mem_6GiB_GDDR6>)
  [PASS] axioms only in the copy (+0)
  [PASS] axioms only in the final ontology (-1)

-- defect copy
  expected: consistent=true (open world: U05 has some unknown memory configuration)
    HermiT 1.4.3.456 isConsistent = true
  [PASS] HermiT still reports the copy consistent (consistency is not completeness)
Completeness card (cell = number of asserted values; '*' marks a violation; '-' = component not reachable through a single link)
  model usesGPU hasMemory hasCooling hasInterface producedByManufacturer hasVideoOutput powerW lengthMM volumeGiB busWidthBit frequencyMHz fanCount
  U01         1         1          1            1                      1              2      1        1         1           1            1        1
  U02         1         1          1            1                      1              2      1        1         1           1            1        1
  U03         1         1          1            1                      1              2      1        1         1           1            1        1
  U04         1         1          1            1                      1              2      1        1         1           1            1        1
  U05         1        0*          1            1                      1              2      1        1         -           -            1        1
  U06         1         1          1            1                      1              2      1        1         1           1            1        1
  U07         1         1          1            1                      1              2      1        1         1           1            1        1
  U08         1         1          1            1                      1              2      1        1         1           1            1        1
  card problem: U05 hasMemory: 0 asserted value(s), expected 1
  [PASS] the card reports exactly one problem
  [PASS] the problem is (U05, hasMemory, actual 0, expected 1)

-- rollback: ontology/videocard.owl
  expected: consistent=true, completeness card without problems
    HermiT 1.4.3.456 isConsistent = true
  [PASS] HermiT reports the final ontology consistent
  [PASS] U05 hasMemory Mem_6GiB_GDDR6 is asserted in the final ontology
  [PASS] the card of the final ontology has zero problems
T09: PASS
```

**Статус: ПРОЙДЕН**


### T10. Сохранение, повторное открытие, повтор T04/T05

- **Пункты ТЗ:** 4.5.1; 4.5.3; 4.6.3
- **Исходные условия:** `ontology/videocard.owl` (SHA-256 в README).
- **Действия:** сохранить финальный OWL (OWL API, RDF/XML) в `tests/results/T10_resaved.owl`, загрузить заново, сравнить сущности, аксиомы, IRI, метки; повторить логику T04 и T05 на перезагруженной копии.
- **Критерий успешности (таблица 6 ТЗ):** нет ошибок открытия и недоступных импортов; сущности и аксиомы сохранены; результаты T04 и T05 воспроизводятся.
- **Ожидаемый результат:** числа сущностей и аксиом равны до и после, 472 аксиомы идентичны, метки ru сохранены, T04 и T05 воспроизведены.

**Фактический результат** (из `tests/results/T10.log`, без изменений):

```text
== T10 RDF/XML save and reload round trip ==
  [PASS] videocard.owl loads (missing imports = THROW_EXCEPTION)
saved: tests/results/T10_resaved.owl (64776 bytes, RDF/XML)
  [PASS] re-saved file loads (missing imports = THROW_EXCEPTION)
  [PASS] re-saved file is valid UTF-8
  [PASS] XML declaration is present and declares no encoding other than UTF-8 (no BOM)
  [PASS] re-saved file has ru labels (>0)
  [PASS] every ru rdfs:label appears verbatim in the re-saved file (73 labels)
entities classes: before=16 after=16
  [PASS] entity count equal: classes (16)
entities object properties: before=10 after=10
  [PASS] entity count equal: object properties (10)
entities data properties: before=7 after=7
  [PASS] entity count equal: data properties (7)
entities annotation properties: before=2 after=2
  [PASS] entity count equal: annotation properties (2)
entities named individuals: before=41 after=41
  [PASS] entity count equal: named individuals (41)
axioms (logical + declarations + annotation assertions): before=472 after=472
  [PASS] axiom sets are equal (472 axioms)
  [PASS] ontology annotations are equal
  [PASS] ontology IRI equal
  [PASS] version IRI equal
  [PASS] no imports in either copy
-- T04 logic on the reloaded copy --
reasoner: HermiT 1.4.1.432 (self-reported; jar version 1.4.3.456)
  [PASS] ontology is consistent (isConsistent)
unsatisfiable classes (equivalent to owl:Nothing): [owl:Nothing]
  [PASS] the only unsatisfiable class is owl:Nothing
per-class isSatisfiable: ActiveCooling=sat, CardWith8GBMemory=sat, CardWithActiveCooling=sat, ConnectionInterface=sat, CoolingSystem=sat, GPUArchitecture=sat, GPUModel=sat, Manufacturer=sat, MemoryConfiguration=sat, MemoryType=sat, ModelComponent=sat, PassiveCooling=sat, Purpose=sat, VideoCardModel=sat, VideoOutput=sat, owl:Thing=sat
  [PASS] every named class is individually satisfiable (16/16)
  [PASS] reasoner entails disjointness of the required 4.4.2 pairs (32/32)
[... строки журнала T05-части (повтор запросов на перезагруженной копии, 39 проверок PASS, 0 FAIL, наборы идентичны журналу T05 выше) опущены; полный текст — tests/results/T10.log ...]
T10: PASS
```

Примечание: сохранение и повторное открытие выполнены программно (OWL API); повтор в Protégé выполняется пользователем (см. README). Файл `tests/results/T10_resaved.owl` — рабочая копия, в комплект не входит.

**Статус: ПРОЙДЕН**


### T11. Состав поставки, версии среды, README, протокол

- **Пункты ТЗ:** 4.5.2; 4.6.1–4.6.4; 5
- **Исходные условия:** полная папка поставки; журналы T01–T10 того же запуска.
- **Действия:** проверить наличие обязательных файлов и каталогов, журналы T01–T10, тестовые копии (отличаются от финальной по SHA-256, нет посторонних .owl), README (версия, run_tests.sh, SHA-256 равен фактическому), версии среды, `docs/test_protocol.md` (упоминание T01–T11, версии OWL API/HermiT/Java), непустое `docs/ontology_description.md`.
- **Критерий успешности (таблица 6 ТЗ):** передан полный комплект, включая обе схемы; каждый тест имеет фактический результат; тестовые копии отделены от финальной онтологии.
- **Ожидаемый результат:** все автоматические проверки PASS. Критерий «включая обе схемы» выполняется только ссылкой: схемы находятся в приложении 1 ТЗ и по решению заказчика в комплект поставки не входят (см. «Критические замечания», п. 4).

**Фактический результат** (из `tests/results/T11.log`, без изменений):

```text
== T11 delivered folder structure and consistency ==
  [PASS] path exists: ontology/videocard.owl
  [PASS] path exists: ontology/src/build_ontology.py
  [PASS] path exists: ontology/src/ontology_data.py
  [PASS] path exists: ontology/src/build.sh
  [PASS] path exists: docs/ontology_description.md
  [PASS] path exists: docs/test_protocol.md
  [PASS] path exists: README.md
  [PASS] path exists: tests/run_tests.sh
  [PASS] path exists: tests/expected.json
  [PASS] path exists: tests/harness/fetch_libs.sh
  [PASS] path exists: tests/harness/src
  [PASS] path exists: tests/negative/T06_active_and_passive.owl
  [PASS] path exists: tests/negative/T07_two_gpus.owl
  [PASS] path exists: tests/negative/T08_negative_volume.owl
  [PASS] path exists: tests/negative/T09_missing_hasMemory.owl
  [PASS] path exists: tests/results
  [PASS] tests/harness/src contains Java sources
  [PASS] results log T01.log ends with 'T01: PASS'
  [PASS] results log T02.log ends with 'T02: PASS'
  [PASS] results log T03.log ends with 'T03: PASS'
  [PASS] results log T04.log ends with 'T04: PASS'
  [PASS] results log T05.log ends with 'T05: PASS'
  [PASS] results log T06.log ends with 'T06: PASS'
  [PASS] results log T07.log ends with 'T07: PASS'
  [PASS] results log T08.log ends with 'T08: PASS'
  [PASS] results log T09.log ends with 'T09: PASS'
  [PASS] results log T10.log ends with 'T10: PASS'
  [PASS] no .owl files besides videocard.owl, tests/negative/*.owl and the T10 re-saved copy
  [PASS] each negative copy exists and differs from videocard.owl (SHA-256) (4/4)
  [PASS] README.md contains version string 1.0.0
  [PASS] README.md mentions run_tests.sh
  [PASS] README.md contains 'SHA-256' followed by a 64-hex digest
  [PASS] README.md SHA-256 equals the actual SHA-256 of ontology/videocard.owl
runtime: OWL API 4.5.29, HermiT jar 1.4.3.456, Java 17.0.2
  [PASS] runtime OWL API is the pinned 4.5.29
  [PASS] runtime HermiT jar is the pinned 1.4.3.456
  [PASS] Java version is available (17.0.2)
  [PASS] T04.log records the HermiT jar version 1.4.3.456
  [PASS] fetch_libs.sh header pins OWL API 4.5.29
  [PASS] fetch_libs.sh header pins HermiT 1.4.3.456
  [PASS] docs/test_protocol.md mentions T01
  [PASS] docs/test_protocol.md mentions T02
  [PASS] docs/test_protocol.md mentions T03
  [PASS] docs/test_protocol.md mentions T04
  [PASS] docs/test_protocol.md mentions T05
  [PASS] docs/test_protocol.md mentions T06
  [PASS] docs/test_protocol.md mentions T07
  [PASS] docs/test_protocol.md mentions T08
  [PASS] docs/test_protocol.md mentions T09
  [PASS] docs/test_protocol.md mentions T10
  [PASS] docs/test_protocol.md mentions T11
  [PASS] docs/test_protocol.md records the tool versions (OWL API 4.5.29, HermiT 1.4.3.456, Java)
  [PASS] docs/ontology_description.md is non-empty
T11: PASS
```

**Статус: ПРОЙДЕН**


## 4. Снимки экрана Protégé (предоставляет пользователь)

Раздел 5 ТЗ требует снимки экрана или экспорт результатов в протоколе. Ниже места-заполнители; в автоматическом прогоне
они не создаются.

- [СКРИНШОТ: Protégé 5.6.9, меню Reasoner → HermiT выбран, reasoner запущен (Start reasoner)]
- [СКРИНШОТ: результат классификации в Protégé — Inferred class hierarchy, 0 unsatisfiable classes (только owl:Nothing)]
- [СКРИНШОТ: DL Query, вопрос 3 — запрос `CardWith8GBMemory`, Instances: U02, U03, U04, U06, U07]
- [СКРИНШОТ: DL Query, вопрос 5 — запрос `CardWithActiveCooling`, Instances: U02, U03, U04, U05, U07]
- [СКРИНШОТ: DL Query, вопрос 8 — запрос `CardWith8GBMemory and CardWithActiveCooling`, Instances: U02, U03, U04, U07]
- [СКРИНШОТ (по желанию): DL Query, вопросы 1, 2, 4, 6, 7 — запросы из README, эталоны из `tests/expected.json`]

## 5. Критические замечания к ТЗ

1. **Типы на UML и в таблице 3.** На рис. 1 «ширина шины» и «вентиляторы» показаны как `int`, «объём» — как `integer`, а
   таблица 3 требует `xsd:positiveInteger` для объёма и ширины шины и `xsd:nonNegativeInteger` для числа вентиляторов.
   Реализовано по таблице 3 (`volumeGiB`, `busWidthBit` — positiveInteger; `fanCount` — nonNegativeInteger). Кроме того, метка
   «вентиляторы» на рис. 1 отличается от «число вентиляторов» в таблице 3.
2. **Эталоны для вопросов 2, 6 и 7.** ТЗ задаёт эталонные наборы только для вопросов 3, 5 и 8 (раздел 8.2); для
   остальных поручает тестировщику зафиксировать связи GPU, интерфейсов и видеовыходов до запуска. Эталоны для вопросов 2, 6 и 7
   не заданы ТЗ и определены учебным набором (`tests/expected.json`, `docs/ontology_description.md`, раздел 10); эталоны вопросов
   1 и 4 следуют из таблицы 5 ТЗ.
3. **Снимки экрана Protégé** (reasoner HermiT, результат классификации, DL Query для вопросов 3, 5, 8) должен предоставить
   пользователь; автоматический прогон их не создаёт (раздел 4).
4. **Диаграммы и критерий T11 «включая обе схемы».** Рис. 1 (UML) и рис. 2 (IDEF5) находятся в приложении 1 ТЗ и по решению
   заказчика не входят в этот комплект поставки; критерий T11 «обе схемы» выполняется только ссылкой на ТЗ. Исходные
   файлы диаграмм (раздел 5 ТЗ, п. 7) также не поставляются.
5. **Источники сведений (п. 4.1.4).** Источник и дата обращения требуются для фактов о реальных моделях; в учебном наборе
   все значения вымышлены («учебная модель»), поэтому источников нет (отступление принято решением заказчика).
6. **Неполнота диаграмм.** Рис. 1 и рис. 2 показывают 7 из 13 классов и 6 из 10 объектных свойств; подписи рисунков
   объявляют это «основным составом» (подробности — `docs/ontology_description.md`, раздел 12).

## 6. Дефекты

**Дефекты финальной онтологии:** испытаниями T01–T11 не выявлено (все журналы заканчиваются строкой `Tnn: PASS`).
Намеренные противоречия присутствуют только в тестовых копиях `tests/negative/` и не входят в финальную онтологию
(проверено T06–T09 и T11).

**Исправленные до реализации отклонения плана:** в рабочем плане указывалось 12 классов, 9 объектных свойств и
7 классов в области определения `name`; таблицы 1–3 ТЗ задают 13, 10 и 8, реализовано по ТЗ.

**Наблюдения по средствам испытаний** (на результаты испытаний не повлияли):

- `Reasoner.getReasonerVersion()` HermiT 1.4.3.456 возвращает устаревшую константу 1.4.1.432; оснастка печатает её рядом с
  версией jar, версия запускаемого reasoner определяется по jar (1.4.3.456).
- В classpath оснастки (`tests/harness/lib/*`) присутствуют jar-файлы с дублирующимися классами (commons-logging и
  jcl-over-slf4j, httpclient и httpclient-osgi, и др.); порядок загрузки не определён, на результаты испытаний не повлияло.
- `ConvertFss` открывает выходной файл до сохранения; при ошибке конвертации он может остаться усечённым (в штатном режиме
  не проявляется: `build.sh` воспроизводит `videocard.owl` побайтно).
- Проверка версий в T11 читает закрепление из комментария-заголовка `fetch_libs.sh`; проверка контрольной суммы README
  засчитывает любое вхождение «SHA-256» с корректным дайджестом в пределах 200 символов.
