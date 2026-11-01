# Описание онтологии VideoCardOntology v1.0.0

Документ описывает финальный файл `ontology/videocard.owl` (RDF/XML, UTF-8, OWL 2 DL) по пунктам 4.1.1–4.1.4,
4.2 и 4.4 технического задания. Все факты ниже взяты из генератора (`ontology/src/build_ontology.py`), набора данных
(`ontology/src/ontology_data.py`), эталонов (`tests/expected.json`) и журналов испытаний (`tests/results/`).

## 1. Идентификация онтологии (п. 4.4.1)

| Параметр | Значение |
|---|---|
| IRI онтологии | `https://example.org/ontologies/videocard` |
| Version IRI | `https://example.org/ontologies/videocard/1.0.0` |
| Пространство имён (единое для всех сущностей) | `https://example.org/ontologies/videocard#` (префикс `vc:`) |
| Версия | 1.0.0 |
| Файл | `ontology/videocard.owl`, RDF/XML, UTF-8, 64769 байт |
| Профиль | OWL 2 DL (проверено OWL API `OWL2DLProfile`: 0 нарушений, тест T02) |
| Внешние imports | отсутствуют |
| Сущности | классов 15 (13 + 2 определяемых), объектных свойств 10, свойств данных 7, индивидов 41 |
| Число аксиом (с объявлениями и аннотациями) | 472 |
| Аннотации ontology | `rdfs:label` «Онтология дискретных видеокарт»; `rdfs:comment` «Учебная онтология предметной области «Дискретные видеокарты», версия 1.0.0.» |
| SHA-256 файла | `d8ac600a45ce642deee38be726ae5d0d81f9e47967a9e1bb07a66b5005ae3661` |

Правила именования: технические идентификаторы на английском, без пробелов; классы — `UpperCamelCase`, свойства — `lowerCamelCase`,
модели — идентификаторы вида `U01`; в именах числовых свойств указана единица
(`volumeGiB`, `busWidthBit`, `frequencyMHz`, `powerW`, `lengthMM`). Справочные индивиды именуются по виду и значению
(`GPU_G3`, `Arch_A2`, `Mem_8GiB_GDDR6`, `PCIe_4_0_x16`, `Cooling_Active_2fan`). Русские названия с пробелами хранятся
только в аннотациях `rdfs:label` (язык `ru`); на каждую пользовательскую сущность (классы, свойства, индивиды —
всего 73) заданы `rdfs:label@ru` и `rdfs:comment@ru` (тест T02: 73/73). Синонимы отдельными классами не заводились.

## 2. Границы предметной области (п. 4.1.1, раздел 3.3 ТЗ, п. 4.4.4)

**Единица описания** — модель видеокарты (класс `VideoCardModel`), а не отдельный экземпляр с серийным номером.
Индивиды связанных классов представляют модели GPU, конфигурации памяти, варианты охлаждения, стандарты интерфейсов,
организации-производители, виды видеовыходов, типы памяти, архитектуры и назначения. Состояние конкретного устройства
в онтологии не моделируется.

**В области (внутри границ):**

- дискретные видеокарты для персональных компьютеров, описываемые на уровне модели;
- связи модели: GPU, конфигурация видеопамяти, система охлаждения, интерфейс подключения, видеовыходы (не менее
  одного), производитель, назначение;
- характеристики: название; объём и ширина шины памяти; частота GPU; заявленная мощность платы; длина платы; число
  вентиляторов;
- логический вывод: принадлежность моделей определяемым классам «Карта с памятью от 8 ГиБ» и «Карта с активным
  охлаждением» и поиск моделей по признакам (восемь контрольных вопросов ТЗ).

**Вне области (не моделируется):**

- встроенные графические ядра, серверные ускорители, драйверы, ремонт, цены, результаты игровых тестов и
  рекомендации о покупке (раздел 3.3 ТЗ);
- многопроцессорные (несколько GPU на плате) и иные специальные видеокарты: ограничения `exactly 1` для GPU, памяти,
  охлаждения, интерфейса и производителя и `min 1` для видеовыходов относятся к области проекта и не претендуют на их
  охват (п. 4.4.4 ТЗ). Модель с двумя GPU по построению противоречит онтологии (тест T07);
- назначение видеокарты хранится как справочный признак (`hasPurpose`) и не выводится из объёма памяти;
- ценовые, временные и рыночные сведения, состояние и износ конкретных устройств.

**Открытый мир (п. 4.4.7).** Отсутствие связи не доказывает её невозможность; domain и range участвуют в выводе типов и не
заменяют проверку полноты, которая выполняется отдельно по карточке полноты (раздел 11, тесты T03 и T09). Различные IRI не
считаются различными объектами автоматически: все 41 именованный индивид объявлены различными одной аксиомой
`DifferentIndividuals`.

**Отсутствующее значение** не заменяется нулём и не считается отрицательным фактом (п. 4.1.4): у каждой модели и
компонента числовые атрибуты заданы одним значением. Значение `fanCount = 0` у пассивного охлаждения — реальное значение
(вентиляторов нет), а не заменитель отсутствующего.

## 3. Достоверность данных и статус учебного набора (п. 4.1.4)

Весь набор данных — учебный. Каждый индивид онтологии (41 индивид) принадлежит учебному набору; реальные факты о
конкретных изделиях в онтологии не утверждаются.

- Восемь моделей U01–U08 — вымышленные «учебные модели»: у каждой в `rdfs:comment` стоит пометка «учебная модель»
  (например, «Видеокарта U01 — учебная модель.»). Значения таблицы 5 ТЗ (память, вид охлаждения, тип памяти,
  производитель) заданы ТЗ как обозначения контрольных моделей, а не характеристики коммерческих изделий.
- Остальные значения (GPU G1–G5 и их частоты, архитектуры A1–A3, ширина шины, мощность и длина плат, состав
  видеовыходов и интерфейсов, назначения) — вымышленные учебные данные. Производители P1 и P2, GPU, архитектуры и
  конфигурации памяти прямо помечены в `rdfs:comment` как условные/учебные данные.
- Требование п. 4.1.4 указывать источник и дату обращения «для каждого факта о реальной модели» не применимо:
  реальных моделей в наборе нет. Это отступление принято решением заказчика (значения вымышлены); соответствующие пункты
  чек-листа сверки T01 (раздел 12) отмечены как не выполненные по этой причине.

## 4. Глоссарий

| Термин | Определение |
|---|---|
| Дискретная видеокарта | Отдельная плата расширения с собственным графическим процессором и видеопамятью, подключаемая к компьютеру через интерфейс (в отличие от встроенного графического ядра). |
| Модель видеокарты | Тип изделия (`VideoCardModel`) как единица описания; не конкретный экземпляр с серийным номером. |
| GPU (графический процессор) | Процессор, выполняющий графические вычисления; в онтологии — класс `GPUModel`. |
| Конфигурация видеопамяти | Сочетание типа, объёма и ширины шины памяти (`MemoryConfiguration`). |
| Система охлаждения | Вариант охлаждения модели (`CoolingSystem`): активное (с вентилятором) или пассивное (без вентилятора). |
| Активное / пассивное охлаждение | Подклассы `ActiveCooling` / `PassiveCooling`; взаимно не пересекаются. |
| Интерфейс подключения | Стандарт подключения видеокарты к компьютеру, например PCIe 4.0 x16. |
| Видеовыход | Поддерживаемый моделью тип интерфейса вывода изображения (HDMI, DisplayPort, DVI, VGA). |
| Тип памяти | Технология видеопамяти (GDDR5, GDDR6, GDDR6X). |
| Архитектура GPU | Условная архитектура графического процессора (A1–A3 в учебном наборе). |
| Назначение | Заявленная область использования модели (офис, игры, рабочая станция); справочный признак. |
| Производитель | Организация, выпускающая модель видеокарты или модель GPU (P1, P2). |
| ГиБ | Гибибайт (2^30 байт); единица объёма видеопамяти. |
| Заявленная мощность, Вт | Заявленная мощность модели платы; не равнозначна рекомендуемой мощности блока питания компьютера (п. 4.2.3 ТЗ). |
| Учебная модель | Вымышленная модель из набора U01–U08, помеченная в `rdfs:comment` пометкой «учебная модель». |
| Класс, индивид | Понятие и его представитель в OWL; индивиды — U01–U08 и справочные индивиды (GPU, память и т. д.). |
| Объектное свойство | Связь между индивидами (`usesGPU`, `hasMemory` …); для каждого заданы domain и range. |
| Свойство данных | Связь индивида со значением типа XSD (`name`, `volumeGiB` …). |
| Определяемый класс | Класс с аксиомой эквивалентности (`CardWith8GBMemory`, `CardWithActiveCooling`); его члены выводит reasoner, они не назначаются вручную. |
| Открытый мир | Допущение OWL: отсутствие утверждения не означает его ложность (п. 4.4.7). |
| Reasoner / HermiT | Программа логического вывода; HermiT — основной reasoner проекта (п. 4.4.6). |
| DL Query | Вкладка Protégé для выполнения запросов-классовых выражений после запуска reasoner. |
| Карточка полноты | Таблица числа явно записанных значений по каждой модели; проверяет полноту заполнения (п. 4.2.5, 4.4.4–4.4.5), чего не делает reasoner. |

## 5. Классы (таблица 1 ТЗ и п. 4.4.3)

Тринадцать обязательных классов (определения — по таблице 1 ТЗ; в определениях подклассов названия классов взяты в кавычки «») и два определяемых класса:

| № | Русская метка | IRI (локальное имя) | Определение (rdfs:comment) | Прямой суперкласс |
|---|---|---|---|---|
| 1 | Модель видеокарты | `VideoCardModel` | Модель дискретной видеокарты; основной объект описания. | — |
| 2 | Компонент модели | `ModelComponent` | Общий класс для модели GPU, конфигурации видеопамяти и системы охлаждения. | — |
| 3 | Модель GPU | `GPUModel` | Модель графического процессора; подкласс «Компонент модели». | `ModelComponent` |
| 4 | Конфигурация видеопамяти | `MemoryConfiguration` | Тип, объём и организация памяти; подкласс «Компонент модели». | `ModelComponent` |
| 5 | Система охлаждения | `CoolingSystem` | Вариант охлаждения модели карты; подкласс «Компонент модели». | `ModelComponent` |
| 6 | Активное охлаждение | `ActiveCooling` | Подкласс «Система охлаждения»; охлаждение с вентилятором. | `CoolingSystem` |
| 7 | Пассивное охлаждение | `PassiveCooling` | Подкласс «Система охлаждения»; охлаждение без вентилятора. | `CoolingSystem` |
| 8 | Производитель | `Manufacturer` | Организация, выпускающая модель видеокарты или модель GPU. | — |
| 9 | Интерфейс подключения | `ConnectionInterface` | Стандарт подключения видеокарты к компьютеру. | — |
| 10 | Видеовыход | `VideoOutput` | Поддерживаемый моделью тип интерфейса вывода изображения. | — |
| 11 | Тип памяти | `MemoryType` | Технология видеопамяти, например GDDR6. | — |
| 12 | Архитектура GPU | `GPUArchitecture` | Архитектура графического процессора. | — |
| 13 | Назначение | `Purpose` | Заявленная область использования модели видеокарты. | — |

Определяемые классы:

| № | Русская метка | IRI | Определение (rdfs:comment) | Формальное определение (аксиома EquivalentClasses) |
|---|---|---|---|---|
| 14 | Карта с памятью от 8 ГиБ | `CardWith8GBMemory` | Определяемый класс: модель видеокарты, у которой конфигурация памяти имеет объём не менее 8 ГиБ. Принадлежность выводится reasoner. | `VideoCardModel and hasMemory some (volumeGiB some xsd:integer[>= 8])` |
| 15 | Карта с активным охлаждением | `CardWithActiveCooling` | Определяемый класс: модель видеокарты, у которой система охлаждения является активной. Принадлежность выводится reasoner. | `VideoCardModel and hasCooling some ActiveCooling` |

Иерархия (утверждённая): `GPUModel`, `MemoryConfiguration`, `CoolingSystem` ⊑ `ModelComponent`;
`ActiveCooling`, `PassiveCooling` ⊑ `CoolingSystem`. Остальные классы — корневые. Определяемые классы выводятся
reasoner как подклассы `VideoCardModel`.

## 6. Объектные свойства (таблица 2 ТЗ)

| № | Русская метка | IRI | Определение (rdfs:comment) | Область определения (domain) | Область значений (range) | Функциональное |
|---|---|---|---|---|---|---|
| 1 | использует GPU | `usesGPU` | Связывает модель видеокарты с используемой моделью GPU. | Модель видеокарты (`VideoCardModel`) | Модель GPU (`GPUModel`) | нет |
| 2 | имеет память | `hasMemory` | Связывает модель видеокарты с конфигурацией видеопамяти. | Модель видеокарты (`VideoCardModel`) | Конфигурация видеопамяти (`MemoryConfiguration`) | нет |
| 3 | имеет охлаждение | `hasCooling` | Связывает модель видеокарты с системой охлаждения. | Модель видеокарты (`VideoCardModel`) | Система охлаждения (`CoolingSystem`) | нет |
| 4 | имеет интерфейс | `hasInterface` | Связывает модель видеокарты с интерфейсом подключения. | Модель видеокарты (`VideoCardModel`) | Интерфейс подключения (`ConnectionInterface`) | нет |
| 5 | имеет видеовыход | `hasVideoOutput` | Связывает модель видеокарты с поддерживаемым видеовыходом. | Модель видеокарты (`VideoCardModel`) | Видеовыход (`VideoOutput`) | нет |
| 6 | выпущена производителем | `producedByManufacturer` | Связывает модель видеокарты с производителем. | Модель видеокарты (`VideoCardModel`) | Производитель (`Manufacturer`) | нет |
| 7 | GPU выпущен производителем | `gpuProducedBy` | Связывает модель GPU с производителем. | Модель GPU (`GPUModel`) | Производитель (`Manufacturer`) | нет |
| 8 | имеет архитектуру | `hasArchitecture` | Связывает модель GPU с архитектурой GPU. | Модель GPU (`GPUModel`) | Архитектура GPU (`GPUArchitecture`) | нет |
| 9 | имеет тип памяти | `hasMemoryType` | Связывает конфигурацию видеопамяти с типом памяти. | Конфигурация видеопамяти (`MemoryConfiguration`) | Тип памяти (`MemoryType`) | нет |
| 10 | имеет назначение | `hasPurpose` | Связывает модель видеокарты с назначением. | Модель видеокарты (`VideoCardModel`) | Назначение (`Purpose`) | нет |

Объектные свойства не объявлены функциональными; ограничения числа связей заданы аксиомами на классе
`VideoCardModel` (раздел 9.3).

## 7. Свойства данных и единицы измерения (таблица 3 ТЗ, п. 4.2.3–4.2.4)

| № | Русская метка | IRI | Определение (rdfs:comment) | Область определения (domain) | Тип (range) | Единица | Функциональное |
|---|---|---|---|---|---|---|---|
| 1 | название | `name` | Название сущности (строка, единица отсутствует). | ОДНО объединение классов (ObjectUnionOf): Модель видеокарты ∪ Модель GPU ∪ Производитель ∪ Интерфейс подключения ∪ Видеовыход ∪ Тип памяти ∪ Архитектура GPU ∪ Назначение | `xsd:string` | единица отсутствует | нет |
| 2 | объём, ГиБ | `volumeGiB` | Объём видеопамяти в ГиБ. | Конфигурация видеопамяти (`MemoryConfiguration`) | `xsd:positiveInteger` | ГиБ | да |
| 3 | ширина шины, бит | `busWidthBit` | Ширина шины памяти в битах. | Конфигурация видеопамяти (`MemoryConfiguration`) | `xsd:positiveInteger` | бит | да |
| 4 | частота, МГц | `frequencyMHz` | Частота модели GPU в МГц (десятичное число больше 0). | Модель GPU (`GPUModel`) | `xsd:decimal`, значение > 0 (DatatypeRestriction `xsd:decimal` `xsd:minExclusive` 0) | МГц | да |
| 5 | мощность, Вт | `powerW` | Заявленная мощность модели платы в Вт (не рекомендуемая мощность блока питания); десятичное число больше 0. | Модель видеокарты (`VideoCardModel`) | `xsd:decimal`, значение > 0 (DatatypeRestriction `xsd:decimal` `xsd:minExclusive` 0) | Вт | да |
| 6 | длина, мм | `lengthMM` | Длина платы в мм (десятичное число больше 0). | Модель видеокарты (`VideoCardModel`) | `xsd:decimal`, значение > 0 (DatatypeRestriction `xsd:decimal` `xsd:minExclusive` 0) | мм | да |
| 7 | число вентиляторов | `fanCount` | Число вентиляторов системы охлаждения, шт. | Система охлаждения (`CoolingSystem`) | `xsd:nonNegativeInteger` | шт. | да |

- Область определения `name` задана ОДНОЙ аксиомой `DataPropertyDomain` с объединением восьми классов
  (п. 4.2.4); `ModelComponent`, `MemoryConfiguration` и `CoolingSystem` в нём отсутствуют.
- «Десятичное число > 0» реализовано как `DatatypeRestriction(xsd:decimal xsd:minExclusive "0"^^xsd:decimal)`.
- Шесть числовых свойств функциональны (одно значение на индивид); `name` не функционально.
- Числа `frequencyMHz`, `powerW`, `lengthMM` записаны литералами `xsd:decimal`; `volumeGiB`, `busWidthBit` —
  `xsd:positiveInteger`; `fanCount` — `xsd:nonNegativeInteger`.

## 8. Соответствие русских меток и IRI (п. 4.4.1)

В ТЗ и на диаграммах используются русские метки с пробелами; технические IRI заданы без пробелов. Соответствие
фиксируется таблицей (метка совпадает с названием в таблицах 1–3 ТЗ и со значением `rdfs:label@ru` сущности):

| Вид | Русская метка | Локальное имя (IRI-фрагмент) | Полный IRI |
|---|---|---|---|
| класс | Модель видеокарты | `VideoCardModel` | `https://example.org/ontologies/videocard#VideoCardModel` |
| класс | Компонент модели | `ModelComponent` | `https://example.org/ontologies/videocard#ModelComponent` |
| класс | Модель GPU | `GPUModel` | `https://example.org/ontologies/videocard#GPUModel` |
| класс | Конфигурация видеопамяти | `MemoryConfiguration` | `https://example.org/ontologies/videocard#MemoryConfiguration` |
| класс | Система охлаждения | `CoolingSystem` | `https://example.org/ontologies/videocard#CoolingSystem` |
| класс | Активное охлаждение | `ActiveCooling` | `https://example.org/ontologies/videocard#ActiveCooling` |
| класс | Пассивное охлаждение | `PassiveCooling` | `https://example.org/ontologies/videocard#PassiveCooling` |
| класс | Производитель | `Manufacturer` | `https://example.org/ontologies/videocard#Manufacturer` |
| класс | Интерфейс подключения | `ConnectionInterface` | `https://example.org/ontologies/videocard#ConnectionInterface` |
| класс | Видеовыход | `VideoOutput` | `https://example.org/ontologies/videocard#VideoOutput` |
| класс | Тип памяти | `MemoryType` | `https://example.org/ontologies/videocard#MemoryType` |
| класс | Архитектура GPU | `GPUArchitecture` | `https://example.org/ontologies/videocard#GPUArchitecture` |
| класс | Назначение | `Purpose` | `https://example.org/ontologies/videocard#Purpose` |
| определяемый класс | Карта с памятью от 8 ГиБ | `CardWith8GBMemory` | `https://example.org/ontologies/videocard#CardWith8GBMemory` |
| определяемый класс | Карта с активным охлаждением | `CardWithActiveCooling` | `https://example.org/ontologies/videocard#CardWithActiveCooling` |
| объектное свойство | использует GPU | `usesGPU` | `https://example.org/ontologies/videocard#usesGPU` |
| объектное свойство | имеет память | `hasMemory` | `https://example.org/ontologies/videocard#hasMemory` |
| объектное свойство | имеет охлаждение | `hasCooling` | `https://example.org/ontologies/videocard#hasCooling` |
| объектное свойство | имеет интерфейс | `hasInterface` | `https://example.org/ontologies/videocard#hasInterface` |
| объектное свойство | имеет видеовыход | `hasVideoOutput` | `https://example.org/ontologies/videocard#hasVideoOutput` |
| объектное свойство | выпущена производителем | `producedByManufacturer` | `https://example.org/ontologies/videocard#producedByManufacturer` |
| объектное свойство | GPU выпущен производителем | `gpuProducedBy` | `https://example.org/ontologies/videocard#gpuProducedBy` |
| объектное свойство | имеет архитектуру | `hasArchitecture` | `https://example.org/ontologies/videocard#hasArchitecture` |
| объектное свойство | имеет тип памяти | `hasMemoryType` | `https://example.org/ontologies/videocard#hasMemoryType` |
| объектное свойство | имеет назначение | `hasPurpose` | `https://example.org/ontologies/videocard#hasPurpose` |
| свойство данных | название | `name` | `https://example.org/ontologies/videocard#name` |
| свойство данных | объём, ГиБ | `volumeGiB` | `https://example.org/ontologies/videocard#volumeGiB` |
| свойство данных | ширина шины, бит | `busWidthBit` | `https://example.org/ontologies/videocard#busWidthBit` |
| свойство данных | частота, МГц | `frequencyMHz` | `https://example.org/ontologies/videocard#frequencyMHz` |
| свойство данных | мощность, Вт | `powerW` | `https://example.org/ontologies/videocard#powerW` |
| свойство данных | длина, мм | `lengthMM` | `https://example.org/ontologies/videocard#lengthMM` |
| свойство данных | число вентиляторов | `fanCount` | `https://example.org/ontologies/videocard#fanCount` |

## 9. Аксиомы (сводка)

### 9.1. Иерархия и непересекаемость (п. 4.4.2)

- `SubClassOf`: `GPUModel`, `MemoryConfiguration`, `CoolingSystem` → `ModelComponent`; `ActiveCooling`, `PassiveCooling` → `CoolingSystem`.
- `DisjointClasses` попарно для восьми корневых классов: `VideoCardModel`, `ModelComponent`, `Manufacturer`,
  `ConnectionInterface`, `VideoOutput`, `MemoryType`, `GPUArchitecture`, `Purpose` (28 пар).
- `DisjointClasses(GPUModel MemoryConfiguration CoolingSystem)` (3 пары).
- `DisjointClasses(ActiveCooling PassiveCooling)` (1 пара).
- Итого 32 пары; наличие их в онтологии (тест T02) и выводимость reasoner (тест T04) проверены 32/32.

### 9.2. Domain и range

Для каждого из 10 объектных свойств заданы `ObjectPropertyDomain` и `ObjectPropertyRange` (таблица раздела 6; тест T02: 20/20).
Для свойств данных заданы `DataPropertyDomain` и `DataPropertyRange` (раздел 7; тест T02: 13/13).

### 9.3. Ограничения на `VideoCardModel` (п. 4.4.4–4.4.5)

- `SubClassOf(VideoCardModel ObjectExactCardinality(1 P))` для P ∈ {`usesGPU`, `hasMemory`, `hasCooling`,
  `hasInterface`, `producedByManufacturer`};
- `SubClassOf(VideoCardModel ObjectAllValuesFrom(P C))` для тех же пяти свойств с классами-диапазонами `GPUModel`,
  `MemoryConfiguration`, `CoolingSystem`, `ConnectionInterface`, `Manufacturer`;
- `SubClassOf(VideoCardModel ObjectMinCardinality(1 hasVideoOutput))`.

Тест T02: 5 exact / 5 only / 1 min. Эти ограничения не охватывают многопроцессорные и специальные карты (раздел 2).

### 9.4. Определяемые классы (п. 4.4.3)

- `CardWith8GBMemory ≡ VideoCardModel and hasMemory some (volumeGiB some xsd:integer[>= 8])`;
- `CardWithActiveCooling ≡ VideoCardModel and hasCooling some ActiveCooling`.

Ни для одного индивида `ClassAssertion` в эти два класса не записан (проверяется тестом T05); принадлежность выводится
reasoner.

### 9.5. Функциональность и различие индивидов

- `FunctionalDataProperty`: `volumeGiB`, `busWidthBit`, `frequencyMHz`, `powerW`, `lengthMM`, `fanCount`
  (ровно шесть; тест T02). Объектные свойства не функциональны.
- Одна аксиома `DifferentIndividuals` по всем 41 именованным индивидам (п. 4.4.7); `SameIndividual` в онтологии нет.
- Аннотации: `rdfs:label@ru` и `rdfs:comment@ru` на каждой пользовательской сущности (73/73).

## 10. Учебный набор данных (п. 4.2.5, таблица 5 ТЗ)

Все индивиды вымышленные («учебная модель», раздел 3). Каждая модель U01–U08 имеет название (`name`), GPU,
конфигурацию памяти, охлаждение, интерфейс, производителя, назначение и два видеовыхода; связанные индивиды
используются совместно (например, `Mem_8GiB_GDDR6` — у U02 и U06; `GPU_G2` — у U02 и U05; `GPU_G3` — у U03 и U06;
`GPU_G1` — у U01 и U08).

### 10.1. Модели U01–U08: связи

| Модель | usesGPU | hasMemory | hasCooling | hasInterface | producedByManufacturer | hasVideoOutput | hasPurpose |
|---|---|---|---|---|---|---|---|
| U01 | GPU_G1 | Mem_4GiB_GDDR5 | Cooling_Passive | PCIe_3_0_x16 | P1 | HDMI, VGA | Office |
| U02 | GPU_G2 | Mem_8GiB_GDDR6 | Cooling_Active_2fan | PCIe_4_0_x16 | P1 | HDMI, DisplayPort | Gaming |
| U03 | GPU_G3 | Mem_12GiB_GDDR6 | Cooling_Active_2fan | PCIe_4_0_x16 | P2 | HDMI, DisplayPort | Gaming |
| U04 | GPU_G4 | Mem_16GiB_GDDR6 | Cooling_Active_3fan | PCIe_4_0_x16 | P2 | HDMI, DisplayPort | Workstation |
| U05 | GPU_G2 | Mem_6GiB_GDDR6 | Cooling_Active_2fan | PCIe_3_0_x16 | P1 | HDMI, DVI | Office |
| U06 | GPU_G3 | Mem_8GiB_GDDR6 | Cooling_Passive | PCIe_3_0_x16 | P2 | HDMI, DVI | Office |
| U07 | GPU_G5 | Mem_24GiB_GDDR6X | Cooling_Active_3fan | PCIe_5_0_x16 | P2 | DisplayPort, HDMI | Workstation |
| U08 | GPU_G1 | Mem_2GiB_GDDR5 | Cooling_Passive | PCIe_3_0_x16 | P1 | VGA, DVI | Office |

### 10.2. Модели U01–U08: числовые атрибуты и значения связанных компонентов

(`volumeGiB`, `busWidthBit` и тип памяти — у конфигурации памяти модели; `frequencyMHz` — у её GPU; `fanCount` — у
системы охлаждения; единицы: ГиБ, бит, МГц, Вт, мм, шт.)

| Модель | name | powerW, Вт | lengthMM, мм | volumeGiB, ГиБ | busWidthBit, бит | Тип памяти | frequencyMHz, МГц | fanCount, шт. | Вид охлаждения |
|---|---|---|---|---|---|---|---|---|---|
| U01 | U01 | 40 | 160 | 4 | 128 | GDDR5 | 900 | 0 | PassiveCooling |
| U02 | U02 | 150 | 240 | 8 | 256 | GDDR6 | 1200 | 2 | ActiveCooling |
| U03 | U03 | 185 | 265 | 12 | 192 | GDDR6 | 1500 | 2 | ActiveCooling |
| U04 | U04 | 260 | 310 | 16 | 256 | GDDR6 | 1800 | 3 | ActiveCooling |
| U05 | U05 | 120 | 220 | 6 | 192 | GDDR6 | 1200 | 2 | ActiveCooling |
| U06 | U06 | 75 | 200 | 8 | 256 | GDDR6 | 1500 | 0 | PassiveCooling |
| U07 | U07 | 350 | 336 | 24 | 384 | GDDR6X | 2200 | 3 | ActiveCooling |
| U08 | U08 | 30 | 145 | 2 | 64 | GDDR5 | 900 | 0 | PassiveCooling |

### 10.3. Сверка с таблицей 5 ТЗ

| Модель | Память, ГиБ | Охлаждение | Тип памяти | Производитель | Совпадение с таблицей 5 ТЗ |
|---|---|---|---|---|---|
| U01 | 4 | пассивное | GDDR5 | P1 | [x] |
| U02 | 8 | активное | GDDR6 | P1 | [x] |
| U03 | 12 | активное | GDDR6 | P2 | [x] |
| U04 | 16 | активное | GDDR6 | P2 | [x] |
| U05 | 6 | активное | GDDR6 | P1 | [x] |
| U06 | 8 | пассивное | GDDR6 | P2 | [x] |
| U07 | 24 | активное | GDDR6X | P2 | [x] |
| U08 | 2 | пассивное | GDDR5 | P1 | [x] |

### 10.4. Справочные индивиды

Справочные индивиды — все именованные индивиды, кроме восьми моделей (33 индивида).

**Производители** (2)

| IRI | Класс | rdfs:label (ru) | name |
|---|---|---|---|
| P1 | Manufacturer | Производитель P1 | P1 |
| P2 | Manufacturer | Производитель P2 | P2 |

**Архитектуры GPU** (3)

| IRI | Класс | rdfs:label (ru) | name |
|---|---|---|---|
| Arch_A1 | GPUArchitecture | Архитектура A1 | A1 |
| Arch_A2 | GPUArchitecture | Архитектура A2 | A2 |
| Arch_A3 | GPUArchitecture | Архитектура A3 | A3 |

**Модели GPU** (5)

| IRI | Класс | rdfs:label (ru) | name | frequencyMHz | hasArchitecture | gpuProducedBy |
|---|---|---|---|---|---|---|
| GPU_G1 | GPUModel | Графический процессор G1 | G1 | 900 | Arch_A1 | P1 |
| GPU_G2 | GPUModel | Графический процессор G2 | G2 | 1200 | Arch_A1 | P1 |
| GPU_G3 | GPUModel | Графический процессор G3 | G3 | 1500 | Arch_A2 | P2 |
| GPU_G4 | GPUModel | Графический процессор G4 | G4 | 1800 | Arch_A2 | P2 |
| GPU_G5 | GPUModel | Графический процессор G5 | G5 | 2200 | Arch_A3 | P2 |

**Конфигурации видеопамяти** (7)

| IRI | Класс | rdfs:label (ru) | volumeGiB | busWidthBit | hasMemoryType |
|---|---|---|---|---|---|
| Mem_2GiB_GDDR5 | MemoryConfiguration | Конфигурация памяти 2 ГиБ GDDR5 | 2 | 64 | GDDR5 |
| Mem_4GiB_GDDR5 | MemoryConfiguration | Конфигурация памяти 4 ГиБ GDDR5 | 4 | 128 | GDDR5 |
| Mem_6GiB_GDDR6 | MemoryConfiguration | Конфигурация памяти 6 ГиБ GDDR6 | 6 | 192 | GDDR6 |
| Mem_8GiB_GDDR6 | MemoryConfiguration | Конфигурация памяти 8 ГиБ GDDR6 | 8 | 256 | GDDR6 |
| Mem_12GiB_GDDR6 | MemoryConfiguration | Конфигурация памяти 12 ГиБ GDDR6 | 12 | 192 | GDDR6 |
| Mem_16GiB_GDDR6 | MemoryConfiguration | Конфигурация памяти 16 ГиБ GDDR6 | 16 | 256 | GDDR6 |
| Mem_24GiB_GDDR6X | MemoryConfiguration | Конфигурация памяти 24 ГиБ GDDR6X | 24 | 384 | GDDR6X |

**Системы охлаждения** (3)

| IRI | Класс | rdfs:label (ru) | fanCount |
|---|---|---|---|
| Cooling_Passive | PassiveCooling | Пассивное охлаждение | 0 |
| Cooling_Active_2fan | ActiveCooling | Активное охлаждение, 2 вентилятора | 2 |
| Cooling_Active_3fan | ActiveCooling | Активное охлаждение, 3 вентилятора | 3 |

**Интерфейсы подключения** (3)

| IRI | Класс | rdfs:label (ru) | name |
|---|---|---|---|
| PCIe_3_0_x16 | ConnectionInterface | PCIe 3.0 x16 | PCIe 3.0 x16 |
| PCIe_4_0_x16 | ConnectionInterface | PCIe 4.0 x16 | PCIe 4.0 x16 |
| PCIe_5_0_x16 | ConnectionInterface | PCIe 5.0 x16 | PCIe 5.0 x16 |

**Видеовыходы** (4)

| IRI | Класс | rdfs:label (ru) | name |
|---|---|---|---|
| HDMI | VideoOutput | HDMI | HDMI |
| DisplayPort | VideoOutput | DisplayPort | DisplayPort |
| DVI | VideoOutput | DVI | DVI |
| VGA | VideoOutput | VGA | VGA |

**Типы памяти** (3)

| IRI | Класс | rdfs:label (ru) | name |
|---|---|---|---|
| GDDR5 | MemoryType | GDDR5 | GDDR5 |
| GDDR6 | MemoryType | GDDR6 | GDDR6 |
| GDDR6X | MemoryType | GDDR6X | GDDR6X |

**Назначения** (3)

| IRI | Класс | rdfs:label (ru) | name |
|---|---|---|---|
| Office | Purpose | Офисное назначение | Office |
| Gaming | Purpose | Игровое назначение | Gaming |
| Workstation | Purpose | Рабочая станция | Workstation |

### 10.5. Контрольные вопросы и эталонные ответы (п. 4.3, раздел 5 п. 6 ТЗ)

Эталоны зафиксированы в `tests/expected.json` до первого запуска reasoner на финальной онтологии
(`ontology/src/make_expected.py` строит их из `ontology_data.py`). Запросы выполняются на вкладке DL Query после запуска
HermiT; запросы записаны с локальными именами IRI, поэтому в Protégé перед вводом нужно выбрать отображение
сущностей по короткому имени IRI (View → Render by entity IRI short name (Id)), иначе парсер DL Query, работающий через
активный способ отображения, при отображении по `rdfs:label` их не разберёт (при сохранённом отображении по меткам
пишите русские метки, с кавычками там, где есть пробелы). Нами это в Protégé не проверялось: Protégé не запускался.
Для вопросов 3, 5 и 8 используются определяемые классы (в T05 дополнительно сверяется «сырой» запрос).
Для вопросов 2, 6 и 7 ТЗ эталонов не задаёт (п. 8.2 поручает тестировщику зафиксировать их до запуска); они определены
учебным набором.

| № | Вопрос | Запрос в DL Query | Эталон (из `tests/expected.json`) |
|---|---|---|---|
| Q1 | Модели, выпущенные выбранным производителем | `VideoCardModel and producedByManufacturer value P1` | {U01, U02, U05, U08} |
| Q1 | Модели, выпущенные выбранным производителем | `VideoCardModel and producedByManufacturer value P2` | {U03, U04, U06, U07} |
| Q2 | Модели, использующие выбранную модель GPU | `VideoCardModel and usesGPU value GPU_G1` | {U01, U08} |
| Q2 | Модели, использующие выбранную модель GPU | `VideoCardModel and usesGPU value GPU_G2` | {U02, U05} |
| Q2 | Модели, использующие выбранную модель GPU | `VideoCardModel and usesGPU value GPU_G3` | {U03, U06} |
| Q2 | Модели, использующие выбранную модель GPU | `VideoCardModel and usesGPU value GPU_G4` | {U04} |
| Q2 | Модели, использующие выбранную модель GPU | `VideoCardModel and usesGPU value GPU_G5` | {U07} |
| Q3 | Модели с видеопамятью не менее 8 ГиБ | `CardWith8GBMemory` | {U02, U03, U04, U06, U07} |
| Q4 | Модели с заданным типом видеопамяти | `VideoCardModel and hasMemory some (hasMemoryType value GDDR5)` | {U01, U08} |
| Q4 | Модели с заданным типом видеопамяти | `VideoCardModel and hasMemory some (hasMemoryType value GDDR6)` | {U02, U03, U04, U05, U06} |
| Q4 | Модели с заданным типом видеопамяти | `VideoCardModel and hasMemory some (hasMemoryType value GDDR6X)` | {U07} |
| Q5 | Модели с активным охлаждением | `CardWithActiveCooling` | {U02, U03, U04, U05, U07} |
| Q6 | Модели, поддерживающие выбранный видеовыход | `VideoCardModel and hasVideoOutput value DVI` | {U05, U06, U08} |
| Q6 | Модели, поддерживающие выбранный видеовыход | `VideoCardModel and hasVideoOutput value DisplayPort` | {U02, U03, U04, U07} |
| Q6 | Модели, поддерживающие выбранный видеовыход | `VideoCardModel and hasVideoOutput value HDMI` | {U01, U02, U03, U04, U05, U06, U07} |
| Q6 | Модели, поддерживающие выбранный видеовыход | `VideoCardModel and hasVideoOutput value VGA` | {U01, U08} |
| Q7 | Модели с выбранным интерфейсом подключения | `VideoCardModel and hasInterface value PCIe_3_0_x16` | {U01, U05, U06, U08} |
| Q7 | Модели с выбранным интерфейсом подключения | `VideoCardModel and hasInterface value PCIe_4_0_x16` | {U02, U03, U04} |
| Q7 | Модели с выбранным интерфейсом подключения | `VideoCardModel and hasInterface value PCIe_5_0_x16` | {U07} |
| Q8 | Модели с памятью не менее 8 ГиБ и активным охлаждением | `CardWith8GBMemory and CardWithActiveCooling` | {U02, U03, U04, U07} |

«Сырые» запросы, проверяемые T05 для вопросов 3, 5 и 8 (результат совпадает с запросом по определяемому классу):

| № | Запрос в DL Query (эквивалентный «сырой» запрос) | Эталон |
|---|---|---|
| Q3 | `VideoCardModel and hasMemory some (volumeGiB some xsd:integer[>= 8])` | {U02, U03, U04, U06, U07} |
| Q5 | `VideoCardModel and hasCooling some ActiveCooling` | {U02, U03, U04, U05, U07} |
| Q8 | `VideoCardModel and hasMemory some (volumeGiB some xsd:integer[>= 8]) and hasCooling some ActiveCooling` | {U02, U03, U04, U07} |

Для каждого вопроса есть положительный и отрицательный пример (`expected.json`: `positive_example` / `negative_example`;
проверяется тестом T05, например для Q1 при аргументе P1: U01 — член набора, U03 — нет).

## 11. Карточка полноты (п. 4.2.5, 4.4.4–4.4.5; тест T03)

Карточка строится по явно записанным аксиомам (reasoner не используется). Ячейка — число явно записанных значений;
`*` помечает нарушение, `-` — компонент недостижим по одной связи. Первым столбцом атрибутов идёт `name` (название,
п. 4.2.5): ровно одно значение типа `xsd:string`. Отдельной проверкой тест T03 убеждается, что у каждой из моделей
U01–U08 есть `rdfs:comment` с пометкой «учебная модель» (список моделей и сама фраза заданы в оснастке, не берутся из
онтологии). Копия из `tests/results/T03.log` без изменений:

```text
Completeness card (cell = number of asserted values; '*' marks a violation; '-' = component not reachable through a single link)
  model usesGPU hasMemory hasCooling hasInterface producedByManufacturer hasVideoOutput name powerW lengthMM volumeGiB busWidthBit frequencyMHz fanCount
  U01         1         1          1            1                      1              2    1      1        1         1           1            1        1
  U02         1         1          1            1                      1              2    1      1        1         1           1            1        1
  U03         1         1          1            1                      1              2    1      1        1         1           1            1        1
  U04         1         1          1            1                      1              2    1      1        1         1           1            1        1
  U05         1         1          1            1                      1              2    1      1        1         1           1            1        1
  U06         1         1          1            1                      1              2    1      1        1         1           1            1        1
  U07         1         1          1            1                      1              2    1      1        1         1           1            1        1
  U08         1         1          1            1                      1              2    1      1        1         1           1            1        1
```

Rule: exactly 1 value for usesGPU, hasMemory, hasCooling, hasInterface, producedByManufacturer; >= 1 for hasVideoOutput; exactly 1 for name (xsd:string), powerW, lengthMM (model), volumeGiB, busWidthBit (memory), frequencyMHz (GPU), fanCount (cooling).

Результат: все восемь моделей полны (0 нарушений), пометка «учебная модель» есть у 8 из 8. Для отрицательного теста T09 карточка той же формы на тестовой
копии показывает `0*` у U05 по `hasMemory` (см. `docs/test_protocol.md`, T09).

## 12. Сверка T01 (п. 4.1.1–4.1.4): описание, словарь, таблицы 1–3 и обе диаграммы

Ручная часть теста T01 (таблица 6 ТЗ: «Сопоставить описание области, словарь и обе диаграммы»). Автоматическая часть
(наличие 13 + 2 классов, 10 + 7 свойств) — в `tests/results/T01.log`. Диаграммы — рис. 1 (UML) и рис. 2 (IDEF5)
приложения 1 ТЗ (страницы 21–22 файла `tz_videokarta_ontology_v1.4.pdf`); оба изображения просмотрены. Отметка `[x]`
ставится только там, где пункт проверен по тексту ТЗ, данным онтологии или изображению диаграммы; `[ ]` означает
расхождение, отступление или отсутствие элемента на диаграмме.

### 12.1. Описание, словарь, источники (п. 4.1.1–4.1.4)

- [x] 4.1.1 Границы предметной области заданы (раздел 2 этого документа).
- [x] 4.1.1 Перечень терминов, определения понятий, отношения, атрибуты и единицы измерения даны (разделы 4–7).
- [x] 4.1.2 Для каждого из 13 обязательных понятий указаны русское наименование, IRI и определение (раздел 5; все 15
  классов с метками и определениями: T02, 73/73).
- [x] 4.1.2 Синонимы дублирующих классов не создают: в онтологии ровно 13 + 2 классов (T02).
- [x] 4.1.3 Описание и онтология используют один словарь: русские метки таблиц 1–3 ТЗ равны `rdfs:label@ru` в онтологии
  (раздел 8); определения классов совпадают с таблицей 1 ТЗ.
- [x] 4.1.4 Учебные модели имеют явную аннотацию о учебном назначении: в `rdfs:comment` каждой из U01–U08 стоит
  «учебная модель» (8 из 8; проверяется тестом T03).
- [x] 4.1.4 Отсутствующее значение не заменено нулём: числовые атрибуты всех моделей заданы по одному значению
  (карточка полноты, раздел 11); `fanCount = 0` у пассивного охлаждения — реальное значение.
- [ ] 4.1.1/4.1.4 Источники сведений и даты обращения для реальных моделей: не применимо; значения вымышлены, отступление
  принято решением заказчика (раздел 3). Пункт критерия T01 «указаны источники» тем самым не выполняется в
  буквальной форме.

### 12.2. UML-диаграмма классов (рис. 1) ↔ таблицы 1–3

На рис. 1 изображено семь классов, шесть ассоциаций и их кратности.

| Элемент рис. 1 | Реализация / таблица ТЗ | Отметка |
|---|---|---|
| Класс «Производитель» | `Manufacturer` (таблица 1) | [x] |
| Класс «Модель GPU» | `GPUModel` (таблица 1) | [x] |
| Класс «Конфигурация видеопамяти» | `MemoryConfiguration` (таблица 1) | [x] |
| Класс «Модель видеокарты» | `VideoCardModel` (таблица 1) | [x] |
| Класс «Система охлаждения» | `CoolingSystem` (таблица 1) | [x] |
| Класс «Интерфейс подключения» | `ConnectionInterface` (таблица 1) | [x] |
| Класс «Видеовыход» | `VideoOutput` (таблица 1) | [x] |
| Производитель: «название : string» | `name`, `xsd:string` (таблица 3) | [x] |
| Модель GPU: «название : string» | `name`, `xsd:string` | [x] |
| Модель GPU: «частота : decimal» | `frequencyMHz`, `xsd:decimal` (> 0, МГц; ограничение «> 0» и единица на рисунке не показаны, единицы заданы подписью «в таблице 3») | [x] |
| Модель видеокарты: «название : string» | `name`, `xsd:string` | [x] |
| Модель видеокарты: «мощность : decimal» | `powerW`, `xsd:decimal` (> 0, Вт) | [x] |
| Модель видеокарты: «длина : decimal» | `lengthMM`, `xsd:decimal` (> 0, мм) | [x] |
| Интерфейс подключения: «название : string» | `name`, `xsd:string` | [x] |
| Видеовыход: «название : string» | `name`, `xsd:string` | [x] |
| Конфигурация видеопамяти и Система охлаждения без атрибута «название» | `name` не определено для `MemoryConfiguration`, `CoolingSystem` (объединение из п. 4.2.4) | [x] |
| Конфигурация видеопамяти: «объём : integer» | `volumeGiB`, `xsd:positiveInteger` (таблица 3): на диаграмме `integer` | [ ] расхождение типа (см. 12.4, п. 1) |
| Конфигурация видеопамяти: «ширина шины : int» | `busWidthBit`, `xsd:positiveInteger`: на диаграмме `int` | [ ] расхождение типа (см. 12.4, п. 1) |
| Система охлаждения: «вентиляторы : int» | `fanCount`, `xsd:nonNegativeInteger`: на диаграмме `int` и имя «вентиляторы» вместо «число вентиляторов» | [ ] расхождение типа и метки (см. 12.4, п. 1, 2) |
| Ассоциация «использует GPU», кратность 1 у «Модели GPU» | `usesGPU` (таблица 2), `exactly 1` (п. 4.4.4) | [x] |
| Ассоциация «имеет память», кратность 1 у «Конфигурации видеопамяти» | `hasMemory`, `exactly 1` | [x] |
| Ассоциация «имеет охлаждение», кратность 1 у «Системы охлаждения» | `hasCooling`, `exactly 1` | [x] |
| Ассоциация «имеет интерфейс», кратность 1 у «Интерфейса подключения» | `hasInterface`, `exactly 1` | [x] |
| Ассоциация «выпущена производителем», кратность 1 у «Производителя» | `producedByManufacturer`, `exactly 1` | [x] |
| Ассоциация «имеет видеовыход», кратность 1..* у «Видеовыхода» | `hasVideoOutput`, `min 1` | [x] |
| Кратность 0..* у «Модели видеокарты» на каждой из шести ассоциаций | Верхняя граница числа моделей у связанного объекта в онтологии не ограничена (ограничений на обратные связи нет) | [x] |
| Названия шести ассоциаций | Совпадают с метками объектных свойств таблицы 2 ТЗ и `rdfs:label@ru` | [x] |
| Классы «Компонент модели», «Активное охлаждение», «Пассивное охлаждение», «Тип памяти», «Архитектура GPU», «Назначение» | Есть в таблице 1 и онтологии, на рис. 1 не показаны (подпись: «Схема отражает основной состав; полный словарь задан таблицей 1») | [ ] не отображено на схеме |
| Свойства «GPU выпущен производителем», «имеет архитектуру», «имеет тип памяти», «имеет назначение» | Есть в таблице 2 и онтологии, на рис. 1 не показаны | [ ] не отображено на схеме |

### 12.3. IDEF5-схема (рис. 2) ↔ таблицы 1–2

На рис. 2 изображено семь кругов (видов сущностей) и шесть подписанных стрелок, направленных от «Модели видеокарты» к
связанному объекту.

| Элемент рис. 2 | Реализация / таблица ТЗ | Отметка |
|---|---|---|
| Круги: «Модель видеокарты», «Модель GPU», «Конфигурация видеопамяти», «Система охлаждения», «Интерфейс подключения», «Видеовыход», «Производитель» | Семь классов таблицы 1 (те же названия, что на рис. 1) | [x] |
| Стрелка «использует GPU» → «Модель GPU» | `usesGPU`: `VideoCardModel` → `GPUModel` | [x] |
| Стрелка «имеет память» → «Конфигурация видеопамяти» | `hasMemory`: `VideoCardModel` → `MemoryConfiguration` | [x] |
| Стрелка «имеет охлаждение» → «Система охлаждения» | `hasCooling`: `VideoCardModel` → `CoolingSystem` | [x] |
| Стрелка «имеет интерфейс» → «Интерфейс подключения» | `hasInterface`: `VideoCardModel` → `ConnectionInterface` | [x] |
| Стрелка «имеет видеовыход» → «Видеовыход» | `hasVideoOutput`: `VideoCardModel` → `VideoOutput` | [x] |
| Стрелка «выпущена производителем» → «Производитель» | `producedByManufacturer`: `VideoCardModel` → `Manufacturer` | [x] |
| Направление стрелок «от модели видеокарты к связанному объекту» (подпись рис. 2) | Совпадает с domain → range таблицы 2 для всех шести показанных свойств | [x] |
| Отношения «GPU выпущен производителем», «имеет архитектуру», «имеет тип памяти», «имеет назначение» | Есть в таблице 2 и онтологии, на рис. 2 не показаны; подпись говорит лишь, что показанные имена соответствуют таблице 2 | [ ] не отображено на схеме |
| Круги «Компонент модели», «Активное охлаждение», «Пассивное охлаждение», «Тип памяти», «Архитектура GPU», «Назначение» | Есть в таблице 1 и онтологии, на рис. 2 не показаны (по подписи стрелки — не отношения наследования) | [ ] не отображено на схеме |

### 12.4. Замечания сверки

1. **Типы чисел.** На рис. 1 «объём» подписан `integer`, «ширина шины» и «вентиляторы» — `int` (в самой диаграмме
   `integer` и `int` смешаны). Таблица 3 ТЗ требует `xsd:positiveInteger` для объёма и ширины шины и
   `xsd:nonNegativeInteger` для числа вентиляторов. Реализовано по таблице 3 (п. 4.2.3 ТЗ называет таблицу 3
   источником типов). Формально диаграмма и таблица 3 различаются; рекомендуется исправить подписи типов на рис. 1.
2. **Метка атрибута.** На рис. 1 атрибут системы охлаждения назван «вентиляторы», в таблице 3 — «число
   вентиляторов»; в онтологии метка «число вентиляторов» (по таблице 3).
3. **Неполнота диаграмм.** Рис. 1 и рис. 2 показывают 7 из 13 классов и 6 из 10 объектных свойств. Недостающие
   элементы (шесть классов и четыре свойства из списков выше) не противоречат диаграммам: подпись рис. 1 объявляет
   «основной состав», а полный словарь отнесён к таблице 1. Критерий T01 «схемы согласованы с таблицами 1–3»
   подтверждён для отображённого подмножества; противоречий в названиях, направлениях и кратностях не найдено.
4. **Что не проверялось.** Исходники диаграмм в комплект не включены (решение заказчика): диаграммы находятся
   только в приложении 1 ТЗ.

**Итог ручной сверки T01:** описание, границы, словарь и таблицы 1–3 согласованы с онтологией; обе диаграммы сверены по
изображениям, противоречий в именах, направлениях и кратностях нет; отмечены расхождения 1–2 (нотация типов, метка) и
неполнота диаграмм (3); требование об источниках для реальных моделей снято решением заказчика.
