# Руководство оператора

Все команды ниже выполняются из корня репозитория. Python >=3.10, Java JDK 17
(нужны java и javac в PATH). В зафиксированной среде Python 3.11 доступен как
`/opt/homebrew/bin/python3.11`; системный python3 версии 3.9 не подходит.
Для поиска сторонние Python-пакеты не требуются; для CLI анализа нужен matplotlib
(установите в выбранную среду: `python3.11 -m pip install matplotlib`); search.yaml использует JSON-подмножество YAML.

```sh
python3.11 --version
java -version
javac -version
bash lab2/tests/harness/fetch_libs.sh
python3.11 -m lab4.optimizer --help
python3.11 -m lab4.optimizer.analysis --help
python3.11 -m unittest discover -s lab4/tests
python3.11 lab4/assessment/verify_reference.py
```

fetch_libs.sh при отсутствии JAR требует сеть; он проверяет закреплённые SHA-1.
Используются OWL API 4.5.29 и HermiT 1.4.3.456. Java-классы optimizer компилируются
автоматически в системный временный каталог. Запись в этот каталог и каталог
журналов должна быть разрешена. Исходник lab2/ontology/videocard.owl проверяется
по SHA-256 и не перезаписывается. Protégé нужен для ручной приёмки, а не для CLI.

## Подключение моделей

Поддержан Ollama HTTP API: /api/generate и /api/embed, по умолчанию
http://127.0.0.1:11434. Установите сервер и выбранные локальные LLM/embedding-модель
отдельно; конкретная модель для приёмки пока не утверждена. Подробнее [MODELS.md](../optimizer/MODELS.md).
Проверьте доступность API, версии и фактические SHA-256 весов. Подтвердите русский
язык, контекст >=32000, RAM/VRAM, 20 пар concept_pairs.csv с аналитиком, порог 0.90,
отладочный запуск и Т04. Запрос num_ctx=32768 сам по себе контекст не подтверждает.

Скопируйте optimizer/search.yaml в отдельный JSON/YAML-файл и добавьте объект
services со следующими обязательными ключами (точный контракт — runtime.build_runtime):
model, embedding_model, model_sha256, embedding_sha256, server_version,
acceptance_approved, inventory, entities. endpoint необязателен.
inventory — объект с массивами classes, object_properties, data_properties,
содержащими OWL Functional Syntax ссылки: например,
`<https://example.org/ontologies/videocard#GPUModel>` либо `:GPUModel`.
ControlGenerator вставляет эти строки в аксиомы напрямую, поэтому полный IRI
без угловых скобок здесь недопустим. entities — полная таблица существующих
сущностей с iri, category (Class/ObjectProperty/DataProperty), label, comment;
entities.iri содержит обычный полный IRI без угловых скобок, например
`https://example.org/ontologies/videocard#GPUModel`. Неполная таблица
делает семантическую проверку неполной. acceptance_approved=true устанавливается
оператором только после фактического согласования; код не подтверждает Т04 автоматически.
Пустые или вымышленные хеши использовать нельзя. Оба режима требуют manifest:
контрольный режим не вызывает LLM, но использует реальную embedding-проверку.

## Запуск и восстановление

Следующие команды — инструкция для подготовленной среды с согласованным
services в /private/tmp/videocard-services.json; они не являются журналом выполненной серии.

```sh
python3.11 -m lab4.optimizer run --config /private/tmp/videocard-services.json --mode model --seed 101 --run-dir runs/model-101
python3.11 -m lab4.optimizer run --config /private/tmp/videocard-services.json --mode control --seed 201 --run-dir runs/control-201
python3.11 -m lab4.optimizer resume --run-dir runs/model-101
python3.11 -m lab4.optimizer replay --run-dir runs/model-101 --candidate 1
python3.11 -m lab4.optimizer.analysis runs/model-101 --output /private/tmp/videocard-analysis --replay
```

run-dir должен быть новым; один процесс на каталог. При interruption исправьте
доступ к сервису и выполните resume. Возобновление возвращается к целому поколению;
незавершённый хвост сохраняется в audit-*.jsonl. Для него replay принимает
`--candidate audit-<32 hex>:ID`. Для лучшего кандидата берите ID из результата run
или analysis; пример 1 лишь показывает синтаксис. replay не обращается к моделям,
сравнивает аксиомы и F с журналом; exit 1 означает расхождение, exit 2 — ошибку.

Для полной серии нужны model seeds 101–105 и control 201–205. Передайте все десять
каталогов analysis с --replay --series; glob допустим лишь если выбирает ровно
требуемые каталоги. Результаты analysis.json, CSV и PNG сохраняются в --output.
CLI не выполняет экспертное согласование или GUI-проверки.

## Ограничения и данные

Полная оценка — 170 кандидатов в запуске, 20 поколений после начальной популяции.
Служебные ошибки прерывают запуск; не подменяйте их невалидными кандидатами.
Сохраняйте config.yaml, metadata.json, evaluations.jsonl, checkpoints и audit-файлы
вместе: произвольное редактирование нарушает воспроизводимость. Названия файлов
контрольных точек уточняются по journal.py. Журналы содержат полный контекст и ответы
модели, их размер и допустимость передачи нужно учитывать при сдаче.
Восстановление проверяет закреплённые зависимости. Архивирование только lab4
теряет lab2 и не обеспечивает повторную установку. Реальное время серии, результаты
моделей, веб-OOPS!, решения эксперта и Protégé пока НЕ ВЫПОЛНЕНЫ.
