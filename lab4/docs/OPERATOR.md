# Руководство оператора

Команды выполняются из корня репозитория или распакованного канонического комплекта.
Нужны Python >=3.10 (в рабочей среде — Python 3.11), JDK 17 с java/javac,
Ollama 0.40.13 и локальные веса. Системный Python 3.9 не подходит.
JDK, Ollama, Protégé, Python-среда и веса в архив программы не входят.

## Установка и расположение файлов

В репозитории программа находится в lab4/optimizer, проверки — в lab4/tests,
материалы — в lab4/assessment, серии — в lab4/runs/series-v1. В каноническом
комплекте это optimizer, tests, docs/assessment и runs соответственно.
Команды `python -m lab4.optimizer` работают в обоих вариантах; в комплекте
совместимость обеспечивает namespace shim, без второй копии программы.

Если переносимый JDK установлен в рабочей директории, добавьте его в PATH;
иначе используйте установленный JDK 17. Пример для подготовленной macOS-среды:

```sh
export PATH="$PWD/.local-runtime/jdk-17.0.21+9/Contents/Home/bin:$HOME/.local/bin:$PATH"
python3.11 --version
java -version
javac -version
python3.11 -m venv .venv
. .venv/bin/activate
```

Определите пути через поставляемый модуль; далее эти переменные используются
одинаково в репозитории и каноническом комплекте:

```sh
task_optimizer_dir="$(python -c 'from lab4.optimizer.paths import OPTIMIZER; print(OPTIMIZER)')"
task_assessment_dir="$(python -c 'from lab4.optimizer.paths import ASSESSMENT; print(ASSESSMENT)')"
task_tests_dir="$(python -c 'from lab4.optimizer.paths import TESTS; print(TESTS)')"
task_harness_dir="$(python -c 'from lab4.optimizer.paths import HARNESS; print(HARNESS)')"
task_core="$(python -c 'from lab4.optimizer.paths import CORE; print(CORE)')"
task_requirements="$(python -c 'from lab4.optimizer.paths import REQUIREMENTS; print(REQUIREMENTS)')"
task_runs_dir="$(python -c 'from lab4.optimizer.paths import ROOT, IS_DELIVERY; print(ROOT / ("runs" if IS_DELIVERY else "lab4/runs/series-v1"))')"
task_debug_dir="$(python -c 'from lab4.optimizer.paths import ROOT, IS_DELIVERY; print(ROOT / ("runs/debug-100" if IS_DELIVERY else "lab4/runs/debug-100-v4"))')"
python -m pip install -r "$task_requirements"
python -m pip install -r "$task_optimizer_dir/requirements-embeddings.txt"
bash "$task_harness_dir/fetch_libs.sh"
python -m lab4.optimizer --help
python -m unittest discover -s "$task_tests_dir"
python "$task_assessment_dir/verify_reference.py"
```

requirements.txt закрепляет matplotlib для графиков; requirements-embeddings.txt —
SentenceTransformers, Transformers, PyTorch и зависимости embedding-сервера.
fetch_libs.sh требует сеть и проверяет SHA-1 закреплённых JAR: OWL API 4.5.29,
HermiT 1.4.3.456. Java-классы компилируются в отдельный временный каталог.

## Выбранные модели и локальные серверы

Генератор — qwen2.5-coder:7b через Ollama 0.40.13, loopback 11435.
Embedding — intfloat/multilingual-e5-large-instruct, полный SentenceTransformer
Transformer → mean Pooling → Normalize, revision
274baa43b0e13e37fafa6428dbc7938e62e5c439, устройство MPS, loopback 11437.
Фактические веса, версии и SHA-256 сохранены в
[evidence/context-e5-preflight/preflight.json](../assessment/evidence/context-e5-preflight/preflight.json).

В отдельном терминале из того же корня запустите установленный переносимый Ollama:

```sh
OLLAMA_HOST=127.0.0.1:11435 OLLAMA_MODELS="$PWD/.local-runtime/models" OLLAMA_NO_CLOUD=1 OLLAMA_NUM_PARALLEL=1 .local-runtime/ollama/ollama serve
```

Если выбранных весов ещё нет, отдельная команда для этого сервера:

```sh
OLLAMA_HOST=127.0.0.1:11435 .local-runtime/ollama/ollama pull qwen2.5-coder:7b
```

Скачивание тега не заменяет проверку фактического SHA-256. Конфигурация серии
закрепляет уже проверенный файл весов. Не меняйте веса, версии, backend, инструкции,
контекст или параметры между запусками одной серии.

В другом терминале с активированной .venv запустите E5. Это фактический профиль
выбранного сервера; при первом получении точного публичного snapshot добавьте
`--download`. Без этого флага сервер проверяет и загружает уже подготовленный
snapshot локально, без выполнения кода модели из Hub:

```sh
python -m lab4.optimizer.embedding_server \
  --repo intfloat/multilingual-e5-large-instruct \
  --revision 274baa43b0e13e37fafa6428dbc7938e62e5c439 \
  --snapshot "$PWD/.local-runtime/hf/snapshots/e5-274baa43b0e13e37fafa6428dbc7938e62e5c439" \
  --cache "$PWD/.local-runtime/hf/cache" \
  --device mps --host 127.0.0.1 --port 11437
```

Дождитесь сообщения `status=ready`. Snapshot и cache должны находиться внутри
.local-runtime/hf и быть разными каталогами. Происхождение файлов закрепляется
в .embedding-snapshot.json; изменённый snapshot не допускается. Сам сервер не
добавляет инструкций к текстам. Оптимизатор одинаково преобразует каждый текст:
`Instruct: Retrieve semantically similar text.\nQuery: <текст>`, где `\n` — перевод строки.
Не меняйте эту инструкцию отдельно для разных пар или сущностей.

## Повторная подготовка и debug

Рабочая калибровка использует [concept_pairs_context.csv](../assessment/concept_pairs_context.csv),
а независимая контрольная выборка — [concept_pairs_holdout.csv](../assessment/concept_pairs_holdout.csv).
Их происхождение и фиксированная STS-инструкция описаны в
[E5_INFERENCE_PROTOCOL.json](../assessment/E5_INFERENCE_PROTOCOL.json) и
[CONTEXT_PREREGISTRATION.json](../assessment/CONTEXT_PREREGISTRATION.json).
Первоначальные короткие concept_pairs.csv и неудачные preflight сохраняются
как история диагностики; они не подменяют выбранные наборы.

Для новой проверки выберите новые output/evidence. Пример создаёт отдельные
пути с меткой времени и не изменяет series-v1.yaml:

```sh
task_check_tag="recheck-$(date +%Y%m%d-%H%M%S)"
python -m lab4.optimizer.prepare \
  --endpoint http://127.0.0.1:11435 --model qwen2.5-coder:7b \
  --models-dir "$PWD/.local-runtime/models" \
  --embedding-model intfloat/multilingual-e5-large-instruct \
  --embedding-backend sentence-transformers \
  --embedding-endpoint http://127.0.0.1:11437 \
  --embedding-revision 274baa43b0e13e37fafa6428dbc7938e62e5c439 \
  --embedding-instruction 'Retrieve semantically similar text.' \
  --pairs "$task_assessment_dir/concept_pairs_context.csv" \
  --holdout-pairs "$task_assessment_dir/concept_pairs_holdout.csv" \
  --output "$task_optimizer_dir/$task_check_tag.json" \
  --evidence-dir "$task_assessment_dir/evidence/$task_check_tag"
python -m lab4.optimizer run --phase debug \
  --config "$task_optimizer_dir/$task_check_tag.json" --mode model --seed 100 \
  --run-dir "$task_runs_dir/$task_check_tag-debug-100"
```

prepare сверяет Ollama manifest с весами и SentenceTransformer snapshot с
независимыми локальными SHA-256, получает фактические embeddings и формирует
inventory/entities из исходной онтологии. При наличии разделяющего интервала
калибровочных пар выбирается его середина; holdout проверяется при том же пороге
без перенастройки. Разметку предметно проверил ИИ; это отмечено в
[AI_REVIEW.md](../assessment/AI_REVIEW.md). Успешный preflight не устанавливает
acceptance_approved=true.

Debug: seed 100, 34 оценки — начальные 10 и три поколения по 8. Анализ различает
синтаксическую корректность первого ответа модели и валидность онтологии;
crossover в долю первых ответов не входит. Retry не исправляет первую неудачу.
Доставленный ответ done=true/done_reason=length проходит обычный разбор с максимум
тремя попытками; done=false — сервисная ошибка с сохранением raw и прерыванием.

## Зафиксированные серии, resume и replay

Выбранный файл [series-v1.yaml](../optimizer/series-v1.yaml) имеет SHA-256
`a39eec24440de1545432117db3d925c1d72da02222adb3e749dc30727e8d0ab4`.
В нём закреплены параметры, источники, хеши и порог дубликатов
0.960735025415394. Допуск Т04 зафиксирован в
[qualification-v4.json](../assessment/evidence/qualification-v4.json).
Это допуск к сериям, а не подтверждение достижения всех требований ТЗ.
Фактический статус и ограничения — в [ACCEPTANCE_STATUS.md](ACCEPTANCE_STATUS.md).

Нужны model seeds 101–105 и control seeds 201–205, по 170 оценок каждый:
10 начальных + 20 × 8. Один процесс на каталог; запуск требует нового run-dir.
Один и тот же frozen config используется для обеих серий. Для повторения в новых
каталогах, после квалификации выбранного окружения:

```sh
task_repeat_runs="$task_runs_dir/repeat-$(date +%Y%m%d-%H%M%S)"
for task_seed in 101 102 103 104 105; do
  python -m lab4.optimizer run --phase main --config "$task_optimizer_dir/series-v1.yaml" \
    --mode model --seed "$task_seed" --run-dir "$task_repeat_runs/model-$task_seed" || break
done
for task_seed in 201 202 203 204 205; do
  python -m lab4.optimizer run --phase main --config "$task_optimizer_dir/series-v1.yaml" \
    --mode control --seed "$task_seed" --run-dir "$task_repeat_runs/control-$task_seed" || break
done
```

Для прерванного сохранённого запуска сначала остановите прежний процесс и
устраните сервисную причину, затем используйте resume на том же каталоге:

```sh
python -m lab4.optimizer resume --run-dir "$task_runs_dir/model-101"
```

Resume берёт фазу и config из metadata, восстанавливает целое поколение и RNG,
архивирует незавершённый хвост в audit-*.jsonl. Сохраняйте config.yaml,
metadata/metadata.sha256, evaluations.jsonl, checkpoint, timing, interruptions
и audit-файлы вместе; не исправляйте журнал вручную. Проверяются SHA-256 JAR.

Replay не требует Ollama, E5, весов или вызова ML. Возьмите реальный ID лучшего
кандидата из checkpoint/analysis; здесь он автоматически читается из checkpoint:

```sh
task_best_id="$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["best"]["id"])' "$task_runs_dir/model-101/checkpoint.json")"
python -m lab4.optimizer replay --run-dir "$task_runs_dir/model-101" --candidate "$task_best_id"
```

Аудит-хвост адресуется как `audit-<32 hex>:ID`. Replay сверяет аксиомы и F;
exit 1 означает расхождение, exit 2 — ошибку. Для полного анализа после завершения
всех десяти запусков выберите новый каталог отчёта:

```sh
task_analysis_output="$(mktemp -d "${TMPDIR:-/tmp}/videocard-analysis.XXXXXX")"
python -m lab4.optimizer.analysis \
  "$task_runs_dir"/model-10[1-5] "$task_runs_dir"/control-20[1-5] \
  --output "$task_analysis_output" --replay --series
```

Анализатор проверяет бюджеты и журнал, монотонность лучших F, replay, целевые F,
медианы, точный односторонний Mann—Whitney и фактическое время каждой серии.
Результаты: analysis.json, CSV и PNG. Debug не входит в серию. Для проверки
производительности всей серии по п. 4.8.2 используется сумма active_seconds
сохранённых сессий; календарный интервал приводится отдельно без изменения.
Прогноз debug не заменяет фактическое измерение.

Из завершённого анализа десяти запусков можно сформировать отдельный отчёт:

```sh
python -m lab4.scripts.report --analysis "$task_analysis_output/analysis.json" \
  --output "$task_analysis_output/EXPERIMENTS.md"
```

Генератор отчёта сверяет числа с журналами, ссылается на существующие PNG/CSV,
не вызывает модели и не заменяет уже существующий output. При переносе источников
передайте --project-root и при необходимости --runs-root с каталогами десяти запусков.
Отчёт о сериях не является решением о выпуске финальной онтологии.

## Локальная приёмка и ручная проверка

Для каждой проверяемой онтологии используется изолированный wrapper, который
не меняет исходную онтологию и не обращается к моделям. Пример для исходника:

```sh
python -m lab4.optimizer.release --ontology "$task_core" \
  --evidence-dir "$task_assessment_dir/evidence/local-acceptance-$(date +%Y%m%d-%H%M%S)"
```

Для финальной онтологии передайте её фактический путь через --ontology и новый
каталог evidence. Wrapper выполняет локальные проверки harness T04–T10:
HermiT, восемь групп вопросов, четыре отрицательные копии и roundtrip.
Сохраняет acceptance.json и отдельные логи. Это локальная приёмка движком;
она не закрывает автоматически испытания Т01–Т12 ЛР4, экспертное решение,
Protégé или OOPS!. Не называйте технический экспорт версии 2.0.0 принятым финалом.

Protégé 5.6.9 подготовлен в .local-runtime/protege-5.6.9/Protege-5.6.9/run.sh.
Исходная онтология проверена в настоящем GUI: метрики, HermiT, все параметры
запросов, отрицательные копии и RDF/XML roundtrip. Текущее подтверждение —
[evidence.json](../assessment/evidence/protege-gui-baseline-trial-6/evidence.json).
[Воспроизводимый helper](../assessment/evidence/protege-api/README.md) запускает
новый неизменённый Protégé с отдельным профилем, работает через публичные API
его EditorKit и штатные Swing-контролы DL Query, сохраняет только собственные окна.
Его успешный запуск — отдельное доказательство; одного старта приложения недостаточно.

```sh
python "$task_assessment_dir/evidence/protege-api/run_acceptance_gui.py" \
  --ontology "$task_core" \
  --expected "$(python -c 'from lab4.optimizer.paths import EXPECTED; print(EXPECTED)')" \
  --protege "$PWD/.local-runtime/protege-5.6.9/Protege-5.6.9" \
  --jdk "$PWD/.local-runtime/jdk-17.0.21+9/Contents/Home" \
  --output "$task_assessment_dir/evidence/protege-check-$(date +%Y%m%d-%H%M%S)" --launch
```

Для итоговой версии замените --ontology её фактическим путём. Сверьте все поля
и `all_collector_checks_passed` в evidence.json и просмотрите снимки. Одиночный
complete.txt не означает прохождения испытаний. Для ручной демонстрации также
откройте обе версии по отдельности, выберите HermiT и выполните Start reasoner.

Эталон ответов — tests/expected.json канонического комплекта или
[lab2/tests/expected.json](../../lab2/tests/expected.json) репозитория.
Он содержит восемь групп, а не восемь единственных запросов. В Protégé проверьте
все перечисленные параметры, сравнивая точные множества U01–U08:

| Группа | Смысл и параметры |
|---|---|
| Q1 | Производитель: P1, P2 |
| Q2 | GPU: GPU_G1, GPU_G2, GPU_G3, GPU_G4, GPU_G5 |
| Q3 | CardWith8GBMemory, без аргумента |
| Q4 | Тип памяти: GDDR5, GDDR6, GDDR6X |
| Q5 | CardWithActiveCooling, без аргумента |
| Q6 | Видеовыход: DVI, DisplayPort, HDMI, VGA |
| Q7 | Интерфейс: PCIe_3_0_x16, PCIe_4_0_x16, PCIe_5_0_x16 |
| Q8 | CardWith8GBMemory AND CardWithActiveCooling, без аргумента |

T09 harness из ЛР2 проверяет полноту при открытом мире: после удаления у U05
утверждения hasMemory HermiT должен сохранить согласованность, а карточка
полноты — отметить ровно U05/hasMemory/actual 0/expected 1. В исходнике и финале
утверждение должно присутствовать, карточка — быть без ошибок. Этот T09 не
следует путать со статистическим Т09 протокола ЛР4; согласованность сама по себе
не доказывает полноту учебных данных.

Публичный OOPS REST не ответил. Исходник однократно проверен локальным
официальным OOPS REST из неизменённых upstream-исходников после 12 успешных
эталонных REST-проверок. [Сравнение](../assessment/evidence/oops-baseline-reference/comparison.json)
фиксирует 10 совпавших P13 и дополнительный P04; Q0 и F не меняются.
Локальный официальный OOPS и собственные проверки программы различаются;
локальный результат не выдаётся за ответ публичного endpoint. Результат финала
и точные границы проверки сверяйте с протоколом.

## Архив и проверка на распакованной копии

Рабочие материалы и принятый канонический комплект различаются. Для рабочих
материалов репозитория используется lab4/scripts/package.py; он сохраняет
предыдущие исходники и журналы. Канонический lab4/scripts/delivery.py допускает
сборку только после явного accepted manifest и проверок приёмки; наличие ZIP
само по себе не подтверждает успех. При сборке сверяются безопасные имена,
контрольные суммы и CRC; веса, исполняемые среды, кеши и JAR исключаются.
Manifest явно задаёт `performance_clock`: `active_sessions` для измерения
производительности по активному времени программы либо `series_wall_clock`
для календарного интервала. Оба исходных показателя сохраняются в комплекте;
неполные или некорректные временные данные не подтверждают критерий.
Manifest может перечислять `assessment_evidence`: выбранные файлы и каталоги
внутри assessment/evidence. Это сокращает комплект без удаления исторических
журналов из репозитория. Ссылки на исключённые существующие материалы блокируют
сборку; они не перенаправляются на одноимённый другой результат.

Распакуйте комплект в новый каталог, установите зависимости первым блоком,
выполните тесты, проверку эталонов и replay сохранённых лучших кандидатов.
Запуск серверов требуется только для новых вычислений. Экспертное решение,
результаты Protégé/OOPS! и испытания Т01–Т12 должны быть подтверждены отдельно.
