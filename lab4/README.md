# VideoCardOntology-NN

Лабораторная работа №4: эволюционное улучшение онтологии видеокарт с нейросетевой
мутацией и сравнением со случайным контрольным генератором. Комплект содержит
исходную онтологию 1.0.0, итоговую 2.0.0, программу, конфигурацию, полные журналы,
испытания и документацию. Экспертную проверку изменений выполнил ИИ по поручению
пользователя; её решения приведены отдельно от результатов автоматического поиска.

- [Техническое задание](tz_videokarta_lr4_nn_v1.0.docx).
- [Методика оценки](assessment/METHODOLOGY.md).
- [Описание программы и полный шаблон запроса](docs/PROGRAM.md).
- [Руководство оператора](docs/OPERATOR.md).
- [Пошаговая инструкция для демонстрации](docs/DEMO.md).
- [Сокращённый Word-отчёт с метриками ТЗ 1.3](docs/otchet_lr4_videocard_nn_v1.3_short.docx).
- [Реализация ТЗ 1.3 и состояние её запусков](optimizer_v13/README.md).
- [Отчёт об экспериментах](docs/EXPERIMENTS.md).
- [Итоговая онтология и экспертные решения](docs/ONTOLOGY.md).
- [Протокол испытаний](docs/ACCEPTANCE_STATUS.md).
- [Исходный RDF/XML](../lab2/ontology/videocard.owl) и [итоговый RDF/XML](ontology/videocard.owl).

## Установка

Нужны Python 3.10+ и JDK 17 с java/javac в PATH. Команды выполняются из корня
репозитория или распакованного канонического комплекта. JDK, Protégé, Ollama,
веса моделей и JAR в архив не входят; версии и установка описаны в руководстве.
Для тестов и воспроизведения сохранённых результатов серверы моделей не нужны.

```sh
python3.11 -m venv .venv
. .venv/bin/activate
task_requirements="$(python -c 'from lab4.optimizer.paths import REQUIREMENTS; print(REQUIREMENTS)')"
task_optimizer="$(python -c 'from lab4.optimizer.paths import OPTIMIZER; print(OPTIMIZER)')"
task_harness="$(python -c 'from lab4.optimizer.paths import HARNESS; print(HARNESS)')"
task_tests="$(python -c 'from lab4.optimizer.paths import TESTS; print(TESTS)')"
python -m pip install -r "$task_requirements" -r "$task_optimizer/requirements-embeddings.txt"
bash "$task_harness/fetch_libs.sh"
python -m unittest discover -s "$task_tests"
python -m lab4.assessment.verify_reference
```

## Воспроизведение

Команда восстанавливает лучшего кандидата из исходного ядра и сохранённой дельты,
затем сверяет множество аксиом и F. Нейросетевые модели не вызываются.

```sh
task_runs="$(python -c 'from lab4.optimizer.paths import ROOT, IS_DELIVERY; print(ROOT / ("runs" if IS_DELIVERY else "lab4/runs/series-v1"))')"
task_best="$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["best"]["id"])' "$task_runs/model-102/checkpoint.json")"
python -m lab4.optimizer replay --run-dir "$task_runs/model-102" --candidate "$task_best"
```

Replay воспроизводит сохранённого кандидата поиска. Итоговая версия 2.0.0
содержит только принятые экспертной проверкой изменения; её полный состав и
повторная валидация приведены в описании онтологии.

Локальные T04–T10 ЛР2 для итогового файла:

```sh
task_final="$(python -c 'from lab4.optimizer.paths import ROOT, IS_DELIVERY; print(ROOT / ("ontology/2.0.0/videocard.owl" if IS_DELIVERY else "lab4/ontology/videocard.owl"))')"
python -m lab4.optimizer.release --ontology "$task_final" \
  --evidence-dir "${TMPDIR:-/tmp}/videocard-final-check-$(date +%Y%m%d-%H%M%S)"
```

Графики, CSV и сравнение Манна—Уитни находятся в отчёте. Проверка настоящим
Protégé и официальным локальным OOPS REST подтверждается отдельными
доказательствами протокола. Контрольные суммы файлов архива перечислены в
DELIVERY_MANIFEST.json; исходная онтология и журналы при упаковке не меняются.
