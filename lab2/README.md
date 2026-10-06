# VideoCardOntology v1.0.0

Учебная OWL 2 DL онтология предметной области «Дискретные видеокарты»: модели видеокарт, их GPU,
конфигурации видеопамяти, охлаждение, интерфейсы подключения, видеовыходы, производители, назначения.
Версия **1.0.0**. Формат файла: RDF/XML, UTF-8 (`ontology/videocard.owl`). Основной reasoner — HermiT.
Проект выполнен по техническому заданию «Онтология предметной области Видеокарта» (далее ТЗ).

- IRI онтологии: `https://example.org/ontologies/videocard`
- Version IRI: `https://example.org/ontologies/videocard/1.0.0`
- Пространство имён (префикс `vc:`): `https://example.org/ontologies/videocard#`
- Состав: 13 классов по таблице 1 ТЗ + 2 определяемых класса, 10 объектных свойств, 7 свойств данных,
  41 именованный индивид (8 учебных моделей U01–U08 и справочные индивиды); всего аксиом: 472.

Все значения учебного набора вымышленные («учебная модель»); данные о реальных изделиях не используются.

## Контрольная сумма

SHA-256 (ontology/videocard.owl): d8ac600a45ce642deee38be726ae5d0d81f9e47967a9e1bb07a66b5005ae3661

Пересчитать: `shasum -a 256 ontology/videocard.owl` (macOS) или `sha256sum ontology/videocard.owl` (Linux);
результат должен совпасть со строкой выше. Это же значение печатается заголовком запуска тестов
(`tests/results/run_tests.log`), а тест T11 проверяет, что оно совпадает с указанным в этом файле.

## Структура комплекта

```text
VideoCardOntology_v1.0.0/
├── README.md                      этот файл
├── ontology/
│   ├── videocard.owl              финальная онтология (RDF/XML, UTF-8)
│   └── src/
│       ├── ontology_data.py       учебный набор данных (U01–U08 и справочные индивиды)
│       ├── build_ontology.py      генератор онтологии (OWL Functional Syntax; ключ --mutate для отрицательных копий)
│       ├── make_expected.py       генератор эталонных ответов tests/expected.json
│       └── build.sh               сборка videocard.owl и отрицательных копий
├── docs/
│   ├── ontology_description.md    описание онтологии: границы, словарь, классы, свойства, аксиомы, набор данных
│   └── test_protocol.md           протокол испытаний T01–T11
└── tests/
    ├── run_tests.sh               единая точка запуска всех испытаний
    ├── expected.json              эталонные ответы на 8 контрольных вопросов
    ├── harness/                   тестовая оснастка на Java (OWL API + HermiT)
    │   ├── fetch_libs.sh          загрузка закреплённых jar-файлов из Maven Central
    │   ├── convert.sh             конвертация Functional Syntax в RDF/XML
    │   └── src/                   исходный код испытаний T01–T11
    ├── negative/                  тестовые копии с намеренными дефектами (T06–T09), НЕ финальная версия
    └── results/                   журналы последнего запуска (T01.log … T11.log, summary.json, run_tests.log)
```

Каталоги `tests/harness/lib/` (jar-файлы) и `tests/harness/out/` (скомпилированные классы) создаются при запуске
и в комплект не входят.

## Запуск испытаний без Protégé (headless)

Требования: Java 17+ (в `PATH`), `curl`, `bash`; для пересборки онтологии дополнительно Python 3 (только стандартная
библиотека). Maven не нужен.

```bash
bash tests/run_tests.sh
```

Скрипт при первом запуске скачивает закреплённые jar-файлы (OWL API 4.5.29, HermiT 1.4.3.456 и зависимости) из
Maven Central в `tests/harness/lib/` (нужен доступ в Интернет; каждый файл проверяется по SHA-1 с Maven Central),
компилирует оснастку и выполняет группы T01–T11. Журналы пишутся в `tests/results/`. Код возврата 0 означает,
что все группы T01–T11 пройдены. При повторных запусках сеть не нужна. Скрипт можно запускать из любого каталога.

Результаты последнего запуска: `tests/results/*.log`, `tests/results/summary.json`; разбор — в
`docs/test_protocol.md`.

## Пересборка онтологии и отрицательных копий

```bash
bash ontology/src/build.sh               # ontology/videocard.owl
bash ontology/src/build.sh --negatives   # tests/negative/T06..T09 (четыре тестовые копии)
bash ontology/src/build.sh --mutate T06  # одна копия (T06|T07|T08|T09)
```

Сборка детерминирована: повторная сборка даёт тот же `videocard.owl` (SHA-256 выше). Данные учебного набора лежат в
`ontology/src/ontology_data.py`; изменение данных требует пересборки, перегенерации `tests/expected.json`
(`python3 ontology/src/make_expected.py`) и обновления контрольной суммы в этом файле.

## Открытие в Protégé Desktop 5.6.9

Контрольная среда по ТЗ: Protégé Desktop 5.6.9 (или более новая стабильная) с reasoner HermiT. Снимки экрана
Protégé в этом комплекте — места-заполнители в `docs/test_protocol.md`; их предоставляет пользователь.

1. File → Open… → `ontology/videocard.owl`. Ошибок открытия и запросов на загрузку внешних онтологий быть не должно
   (imports отсутствуют).
2. Reasoner → HermiT → Start reasoner. Если классификация не выполнилась сама, выберите Reasoner → Synchronize reasoner.
   Ожидается: онтология согласована, в Inferred class hierarchy нет нерешаемых классов, кроме `owl:Nothing`.
3. Вкладка DL Query (при отсутствии: Window → Tabs → DL Query). Введите запрос в поле Query (class expression),
   отметьте Instances (и при желании Subclasses/Equivalent classes), нажмите Execute.
4. Имена в запросах — локальные имена IRI (`P1`, `GPU_G3`, `GDDR6`…), как в таблице ниже. Если в Protégé включено
   отображение сущностей по `rdfs:label`, в ответе вместо `U01` будет русская метка («Видеокарта U01»).
5. Принадлежность классам `CardWith8GBMemory` и `CardWithActiveCooling` выводится reasoner; вручную эти классы
   индивидам не назначаются.

Восемь контрольных вопросов ТЗ (п. 4.3) и точные запросы (те же, что выполняет тест T05):

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

Для вопросов 3, 5 и 8 тест T05 проверяет также эквивалентный «сырой» запрос без определяемых классов:

| № | Запрос в DL Query (эквивалентный «сырой» запрос) | Эталон |
|---|---|---|
| Q3 | `VideoCardModel and hasMemory some (volumeGiB some xsd:integer[>= 8])` | {U02, U03, U04, U06, U07} |
| Q5 | `VideoCardModel and hasCooling some ActiveCooling` | {U02, U03, U04, U05, U07} |
| Q8 | `VideoCardModel and hasMemory some (volumeGiB some xsd:integer[>= 8]) and hasCooling some ActiveCooling` | {U02, U03, U04, U07} |

## Документация

- `docs/ontology_description.md` — границы области, глоссарий, таблицы классов и свойств (русская метка ↔ IRI ↔
  определение ↔ domain/range), аксиомы, IRI, полный учебный набор, карточка полноты, сверка T01.
- `docs/test_protocol.md` — среда и версии, методика, T01–T11 (ожидаемые и фактические результаты, статус),
  критические замечания к ТЗ, дефекты.

## Ограничения поставки

- Схемы UML (рис. 1) и IDEF5 (рис. 2) находятся в приложении 1 ТЗ и в состав этого комплекта не входят (решение
  заказчика); сверка с ними выполнена вручную и записана в `docs/ontology_description.md`.
- Снимки экрана Protégé предоставляются пользователем (см. места-заполнители в протоколе).
- Файлы в `tests/negative/` — намеренно противоречивые тестовые копии; финальная онтология — только
  `ontology/videocard.owl`.
