# Сверка реализации с техническим заданием

Документ показывает, какая часть программы выполняет каждый проверяемый пункт
технического задания (ТЗ) и чем это подтверждено до передачи тестировщику.
Имена `tNN_…` — автоматические приёмочные тесты в `tests/test_acceptance.pl`.

| Пункт ТЗ | Требование | Реализация | Предварительная проверка |
|---|---|---|---|
| 5.1.1 | Начать осмотр и последовательно запросить сведения | `start/0`, `run_session/0`, `ask_questions/4` в `src/expert_system.pl` | `t01`, `tests/test_dialog.pl` |
| 5.1.2 | Не менее 15 признаков, включая 14 обязательных | 28 вопросов `domain:question/3`; за осмотр 25 (электро), 26 (дизель) или 27 (бензин, газ); соответствие обязательным признакам — в таблице ниже | `t02`, `tests/test_domain.pl` (число вопросов по типам топлива) |
| 5.1.3 | Проверять допустимость значения и повторять запрос | `domain:valid_value/2`, разбор в `parse_response/3`, повтор в `ask_question/2` | `t03`, `tests/test_domain.pl`, `tests/test_dialog.pl` |
| 5.1.4 | Ответы только в пределах текущего осмотра | Ядро `inference:evaluate_answers/2` ничего не хранит; хранилище `stored_answer/2` очищается до и после осмотра | `t09`, `tests/test_inference.pl` (очистка после корректного и ошибочного вызова) |
| 5.1.5 | Не менее 50 продукционных правил «если — то» | 52 факта `production_rule/5` (P01–P52) и 8 фактов `verdict_rule/4` (V01–V08) | `t04`, `tests/test_rules_structure.pl` |
| 5.1.6 | Непротиворечивые заключения | Полосы правил одного признака не пересекаются; в каждом состоянии осмотра срабатывает ровно одно правило заключения | `t05`, `t12` |
| 5.1.7 | Классификация: заключение, группа, критичность, действие | Поля `verdict`, `action`, `findings` (`group`, `severity`) отчёта | `t05`, тесты границ в `tests/test_rules_*.pl` |
| 5.1.8 | Вывести признаки и номера правил | Поле `evidence` находки, `print_finding/1`, `print_explanation/1` | `t06` |
| 5.1.9 | Диагностика неполных и противоречивых данных без аварии | Правила V07 и V08, `consistency:consistency_issues/2`, статусы `insufficient_data` и `contradiction` | `t07`, `tests/test_consistency.pl` |
| 5.1.10 | После осмотра выйти или начать новый | `ask_next_action/1`, цикл `inspection_loop/0` | `t09`, `tests/test_dialog.pl` |
| 5.1.11 | Классы заключения, группы, критичность, действия | Подписи классов в `src/domain.pl`, правила слоя 2 | `t05`, `tests/test_rules_structure.pl` |
| 5.2.1 | Контролировать допустимость вводимых данных | То же, что 5.1.3; для программного вызова — `domain:validate_answers/2` | `t03`, `tests/test_domain.pl` |
| 5.2.2 | Ошибочный и неполный ввод не вызывает аварию | Конец ввода в `ask_question/2`, статус `invalid_input` | `t07`, `tests/test_dialog.pl` (пустой ввод, конец ввода посреди осмотра) |
| 5.2.3 | Данные прошлого осмотра не влияют на новый | Очистка `clear_answers/0` до и после осмотра | `t09` |
| 5.2.4 | Выявлять противоречащие правила при тестировании | `tests/conflict_check.pl`: пары правил слоя 1 и все 32 состояния слоя 2 | `t12`, `tests/test_conflicts.pl`; результат — `docs/control_examples.md`, раздел 5 |
| 5.2.5 | Критическое несоответствие ведёт к «не допущен» | Правило V01 (не зависит от полноты данных) | `t08`, `tests/test_inference.pl` |
| 5.2.6 | Существенные — «допущен с замечаниями»; иначе «допущен» | Правила V02 и V03 | `t05`, `tests/test_inference.pl` |
| 5.3 | Локальная работа без сети | В программе нет сетевых вызовов | Просмотр исходного текста |
| 5.5.1 | Исходный текст в UTF-8 | `:- encoding(utf8).` первой строкой каждого `.pl` | `t10` |
| 5.5.2 | Контрольная версия — SWI-Prolog | SWI-Prolog 10.0.2 | `t10` (запуск основной команды в отдельном процессе) |
| 5.5.3 | Windows, Linux или macOS | Команда `swipl -q -s src/expert_system.pl -g start -t halt` не зависит от оболочки | Проверено на macOS; Windows и Linux проверяет тестировщик |
| 5.5.4 | Ввод с клавиатуры, вывод в текстовом виде | `read_line_to_string/2`, `format/2` | `t10`, `tests/test_dialog.pl` |
| 5.8.1 | Правила сгруппированы, пронумерованы, прокомментированы; факты и служебные предикаты не считаются | Заголовки групп `% P01–P10.` … в `src/knowledge_base.pl`; `inference:rule_count/1` считает только правила | `t04`, `tests/test_rules_structure.pl` |
| 5.8.2 | Связь ответов, правил и результата | Отчёт: признаки, правила слоя 1, правила слоя 2, заключение | `t06` |
| 5.8.3 | Пороги отдельной группой фактов с источником | `src/thresholds.pl`, `threshold/5` | `t11`, `tests/test_thresholds.pl` |
| 5.8.4 | Оговорка о справочном характере в заключении | Последняя строка `print_report/1` | `t11` |
| 6.1 | Комментарии к основным предикатам и группам правил | Комментарий модуля в каждом файле, `%!`-описания, заголовки групп | `t13` |
| 6.2 | Комплект документации | ТЗ, отчёт (`docs/report_draft.md`), руководство (`README.md`), таблица контрольных примеров (`docs/control_examples.md`) | `t13` |

## Обязательные признаки п. 5.1.2 ТЗ

| № | Обязательный признак | Ключи признаков |
|---:|---|---|
| 1 | Категория транспортного средства | `category` |
| 2 | Год выпуска | `year` |
| 3 | Эффективность рабочей тормозной системы | `brake_force`, `brake_imbalance` |
| 4 | Работоспособность стояночной тормозной системы | `parking_brake` |
| 5 | Герметичность тормозного привода | `brake_leak` |
| 6 | Суммарный люфт рулевого управления | `steering_play`, `steering_joints` |
| 7 | Исправность и регулировка внешних световых приборов | `headlights`, `headlight_aim`, `signal_lights`, `reflectors` |
| 8 | Глубина протектора и состояние шин | `tread_depth`, `tire_condition`, `wheel_fasteners` |
| 9 | Состояние ветрового стекла и приборов обзора | `windshield`, `mirrors` |
| 10 | Работоспособность стеклоочистителей | `wipers` |
| 11 | Отработавшие газы либо дымность | `co`, `ch`, `smoke` |
| 12 | Исправность ремней безопасности | `seat_belts` |
| 13 | Наличие обязательной комплектации | `first_aid_kit`, `fire_extinguisher`, `warning_triangle` |
| 14 | Несущие элементы и утечки эксплуатационных жидкостей | `structure`, `fluid_leaks` |

## Приёмочные испытания таблицы 2 ТЗ

| Испытание | Пункты ТЗ | Автоматический тест |
|---:|---|---|
| 1 | 5.1.1, 5.5.2 | `t01_first_question_is_printed` |
| 2 | 5.1.2 | `t02_at_least_fifteen_features_are_accepted_and_used` |
| 3 | 5.1.3, 5.2.1 | `t03_invalid_values_are_rejected_and_inspection_continues` |
| 4 | 5.1.5, 5.8.1 | `t04_rule_count_is_at_least_fifty_and_excludes_facts` |
| 5 | 5.1.6, 5.1.7, 5.1.11, 5.2.6 | `t05_four_sets_cover_all_verdicts_severities_and_classes` |
| 6 | 5.1.8, 5.8.2 | `t06_explanation_lists_features_and_rule_numbers` |
| 7 | 5.1.9, 5.2.2 | `t07_incomplete_and_contradictory_data_are_diagnosed` |
| 8 | 5.2.5 | `t08_single_critical_finding_gives_not_admitted` |
| 9 | 5.1.4, 5.1.10, 5.2.3 | `t09_second_inspection_does_not_see_the_first` |
| 10 | 5.5.1–5.5.4 | `t10_sources_are_utf8_and_the_start_command_works` |
| 11 | 5.8.3, 5.8.4 | `t11_thresholds_have_sources_and_reports_carry_the_notice` |
| 12 | 5.2.4 | `t12_no_rules_give_mutually_exclusive_outcomes` |
| 13 | 6.1, 6.2 | `t13_…` в `tests/test_docs.pl` |

Автоматические тесты не заменяют приёмочные испытания: их проводит
тестировщик по `docs/control_examples.md` и `docs/tester_handoff.md`.
