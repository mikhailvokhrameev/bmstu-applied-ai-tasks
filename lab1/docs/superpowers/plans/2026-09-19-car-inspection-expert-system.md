# Экспертная система технического осмотра автомобилей — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Учебная экспертная система на SWI-Prolog: по ответам об автомобиле выдаёт заключение о допуске, перечень несоответствий (группа, критичность), рекомендуемое действие и объяснение с номерами правил.

**Architecture:** Двухслойный вывод. Слой 1 — 52 правила «признаки → несоответствие» (P01–P52); в каждом заданы группа, критичность и текст. Слой 2 — 8 правил «набор степеней критичности → заключение и действие» (V01–V08), взаимоисключающих по построению. Условия правил ссылаются на именованные пороги из `thresholds.pl`; значение выбирается по категории ТС (или по году выпуска для CO/CH). Движок чистый (работает над списком пар `Ключ-Значение`), динамическое хранилище ответов нужно только диалогу и очищается до и после осмотра.

**Tech Stack:** SWI-Prolog 10.0.2 (модули, dict, plunit). Python/`python-docx` — только для необязательной генерации `.docx` (в систему не входит).

**Spec:** `docs/superpowers/specs/2026-09-19-car-inspection-expert-system-design.md`
(источник требований: `docs/tz_car_inspection_v1.0.docx`; референс структуры: `example/`)

## Global Constraints

Каждая задача неявно включает этот раздел.

- SWI-Prolog, контрольная версия 10.0.2; программа запускается в Windows, Linux, macOS (п. 5.5.2–5.5.3 ТЗ).
- Все `.pl` в кодировке UTF-8; первой строкой каждого файла `:- encoding(utf8).` (п. 5.5.1 ТЗ).
- Основная команда запуска, не зависящая от оболочки: `swipl -q -s src/expert_system.pl -g start -t halt`.
- Не менее 50 пронумерованных продукционных правил, ориентир 60: слой 1 — 52 (P01–P52), слой 2 — 8 (V01–V08). Факты, пороги, подписи и служебные предикаты в подсчёт не входят (п. 5.8.1 ТЗ).
- 28 входных признаков; за один осмотр спрашивается 25 (электро), 26 (дизель) или 27 (бензин, газ).
- Ответы «неизвестно», «не знаю», `unknown`, `?` разрешены для всех признаков, **кроме** категории ТС, года выпуска и типа топлива — их запрос повторяется.
- Классы результатов (тексты дословно из п. 5.1.11 ТЗ):
  - заключение: «допущен к эксплуатации» / «допущен с замечаниями, требуется повторный осмотр» / «не допущен к эксплуатации»;
  - группа: тормозная система; рулевое управление; внешние световые приборы и световозвращатели; шины и колёса; приборы обзора и стеклоочистители; экологические показатели; прочие элементы конструкции и обязательная комплектация;
  - критичность: критическая / существенная / незначительная;
  - действие: эксплуатация разрешена / устранить несоответствия до повторного осмотра / эксплуатация запрещена.
- Критическое несоответствие ведёт к «не допущен» даже при неполных данных (п. 5.2.5). Существенные без критических — «допущен с замечаниями»; иначе «допущен» (п. 5.2.6). Критических нет, но есть неизвестные признаки — заключение о допуске не выдаётся (статус `insufficient_data`).
- Пороги — только в `src/thresholds.pl`, факты `threshold(Имя, Категория, Значение, Единица, Источник)`, источник в каждом факте и в комментарии (п. 5.8.3). Значения по памяти, не сверены с ТР ТС 018/2011 (прил. 8) и ГОСТ 33997-2016 — в комментарии помечено, что их подтверждает команда на этапе 2 ТЗ.
- Оговорка «результат носит справочный характер и не заменяет технический осмотр, проводимый аккредитованным оператором» печатается в конце любого отчёта (п. 5.8.4).
- Шкала критичности — решение команды, не норма закона.
- Не входит в первую версию (YAGNI): шарниры рулевого привода отдельно от общего признака, гидроусилитель, ABS, прицепы, периодичность осмотра.
- Python-окружение (`.venv`, `python-docx`) в саму систему не входит.

## Отступления от спеки (решены при планировании)

1. **Противоречие «год выпуска позже 2026» не реализуется.** Допустимый диапазон года 1950…2026 уже отклоняет такой ввод на этапе проверки допустимости. Пятое противоречие заменено на «электромобиль + утечка топлива». Итого пять условий (`src/consistency.pl`).
2. **Пороги «запас» и «доля от предела» хранятся готовыми значениями.** Например, `brake_force_warn` = 0,64 для M1 (0,59 + запас 0,05), `co_warn` = 3,15 (90 % от 3,5). Так условия правил остаются сравнениями «значение и порог», без арифметики. Исходное правило вывода записано в комментарии и в источнике факта.
3. **Разнесение по модулям.** Проверка допустимости ввода (`validate_answers/2`) лежит в `domain.pl`, противоречия входа — в `consistency.pl`, вывод — в `inference.pl`, печать объяснения — в `expert_system.pl`. В спеке проверка данных, противоречия и вывод перечислены в одном `inference.pl`.
4. **Слой 2 стоит в `knowledge_base.pl` выше слоя 1**, чтобы факты `production_rule/5` шли подряд и наращивались по группам без директив `discontiguous`.
5. **Имена признаков и значений — латинские атомы** (`brake_force`, `not_working`); русские подписи хранятся в `domain.pl`.

## Структура файлов

```
src/domain.pl          28 признаков, допустимые значения и диапазоны, русские подписи, validate_answers/2
src/thresholds.pl      threshold/5 с источниками (п. 5.8.3), threshold_value/3
src/consistency.pl     consistency_issues/2 — противоречия во входных данных
src/knowledge_base.pl  слой 2 (V01–V08) и слой 1 (P01–P52), сгруппированные, с комментариями
src/inference.pl       inspect_answers/2, evaluate_answers/2, хранилище ответов, подсчёт правил
src/expert_system.pl   диалог, печать отчёта, start/0, show_rule_count/0
tests/                 plunit: fixtures.pl (наборы данных), test_*.pl, conflict_check.pl, all.pl
scripts/               run.sh, run_tests.sh, control_table.sh
docs/                  модель классификации, контрольные примеры, сверка с ТЗ, передача тестировщику, черновик отчёта
README.md              руководство по запуску и проведению осмотра
```

Тесты запускаются командой `swipl -q -s tests/all.pl -g run_tests -t halt` (скрипт `scripts/run_tests.sh`). Признак успеха: код возврата 0, в выводе все N тестов помечены `passed`, строк `failed` и `ERROR` нет (в терминале с TTY plunit дополнительно печатает итог `All N tests passed`).

---

### Task 1: Каркас проекта и скрипты запуска

**Files:**
- Modify: `.gitignore`
- Create: `scripts/run.sh`, `scripts/run_tests.sh`, `tests/all.pl`

**Interfaces:**
- Produces: `tests/all.pl` — точка входа тестов; каждая следующая задача дописывает в него строку `:- consult(test_<имя>).`

- [ ] **Step 1: Дополнить `.gitignore`**

В корне остались временные файлы Word (`docs/~$_car_inspection_v1.0.docx`) и `.DS_Store`; в коммит их брать нельзя.

**Дописать в конец `.gitignore`:**
```
# macOS / Word
.DS_Store
~$*
```

- [ ] **Step 2: Создать скрипты запуска**

**Создать `scripts/run.sh`:**
```sh
#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec swipl -q -s "$SCRIPT_DIR/../src/expert_system.pl" -g start -t halt
```

**Создать `scripts/run_tests.sh`:**
```sh
#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec swipl -q -s "$SCRIPT_DIR/../tests/all.pl" -g run_tests -t halt
```

- [ ] **Step 3: Создать точку входа тестов**

**Создать `tests/all.pl`:**
```prolog
:- encoding(utf8).

% Точка входа автоматических проверок. Каждый файл test_*.pl объявляет
% свой блок plunit; run_tests/0 запускает все загруженные блоки.
:- use_module(library(plunit)).
```

- [ ] **Step 4: Проверить, что скрипт запускается**

```sh
chmod +x scripts/run.sh scripts/run_tests.sh
./scripts/run_tests.sh; echo "exit=$?"
```

Expected: `exit=0`, сообщений `FAILED` или `ERROR` нет (тестов пока нет).

- [ ] **Step 5: Commit**

Первый коммит в репозитории: вместе с каркасом фиксируем уже лежащие в корне материалы (спека, ТЗ, референс).

```bash
git status --short
git add .gitignore .python-version pyproject.toml uv.lock README.md src/lab1 docs/tz_car_inspection_v1.0.docx docs/superpowers example scripts tests
git commit -m "chore: project skeleton, run scripts, spec and reference materials"
```

`git status --short` до коммита не должен показывать `.DS_Store` и `docs/~$_car_inspection_v1.0.docx` как добавляемые.

---

### Task 2: Предметная модель (`domain.pl`)

**Files:**
- Create: `src/domain.pl`
- Create: `tests/test_domain.pl`
- Modify: `tests/all.pl`

**Interfaces:**
- Produces (все из модуля `domain`):
  - `question(Key, Prompt:string, Kind)` — 28 фактов в порядке диалога; `Kind` = `choice([Value,…])` | `int_range(Min,Max)` | `num_range(Min,Max)`.
  - `known_question_key(+Key)`; `required_key(?Key)` (`category`, `year`, `fuel`).
  - `fuel_specific(?Key, ?Fuels)` (`co`, `ch` → `[petrol, gas]`; `smoke` → `[diesel]`); `question_applies(+Key, +Fuel)` — `Fuel` атом (`petrol|diesel|gas|electric|none`).
  - `valid_value(+Key, +Value)`; `validate_answers(+Answers, -Errors:list(string))`.
  - `answer_hint(+Key, -Hint:string)`; `key_label(+Key, -Text)`; `value_label(?Key, ?Value, ?Text)`; `value_text(+Key, +Value, -Text:string)`.
  - `group_label/2`, `severity_label/2`, `verdict_label/2`, `action_label/2` — русские подписи классов.
- Атомы классов: группы `brakes, steering, lighting, tires, visibility, ecology, other`; критичность `critical, major, minor`; заключения `not_admitted, admitted_with_remarks, admitted`; действия `prohibited, fix_before_reinspection, allowed`.

- [ ] **Step 1: Написать падающие тесты**

**Создать `tests/test_domain.pl`:**
```prolog
:- encoding(utf8).

:- use_module('../src/domain').

:- begin_tests(domain).

test(at_least_fifteen_questions) :-
    findall(Key, question(Key, _, _), Keys),
    length(Keys, Count),
    assertion(Count >= 15).

test(twenty_eight_questions_in_total) :-
    findall(Key, question(Key, _, _), Keys),
    length(Keys, Count),
    assertion(Count =:= 28),
    sort(Keys, Unique),
    assertion(length(Unique, 28)).

test(inspection_size_depends_on_fuel) :-
    forall(member(Fuel-Expected, [electric-25, diesel-26, petrol-27, gas-27]),
           (   findall(Key, (question(Key, _, _), question_applies(Key, Fuel)), Keys),
               length(Keys, Count),
               assertion(Count =:= Expected)
           )).

test(mandatory_features_are_covered) :-
    forall(member(Key, [category, year, brake_force, parking_brake, brake_leak,
                        steering_play, headlights, headlight_aim, tread_depth,
                        tire_condition, windshield, mirrors, wipers, co, smoke,
                        seat_belts, first_aid_kit, fire_extinguisher,
                        warning_triangle, structure, fluid_leaks]),
           assertion(known_question_key(Key))).

test(choice_value_is_accepted) :-
    assertion(valid_value(parking_brake, weak)).

test(value_outside_choice_is_rejected) :-
    assertion(\+ valid_value(parking_brake, broken)).

test(number_in_range_is_accepted) :-
    assertion(valid_value(brake_force, 0.8)),
    assertion(valid_value(brake_force, 0)),
    assertion(valid_value(brake_force, 1.2)).

test(number_out_of_range_is_rejected) :-
    assertion(\+ valid_value(brake_force, 1.3)),
    assertion(\+ valid_value(brake_force, -0.1)),
    assertion(\+ valid_value(tread_depth, 16)).

test(text_is_not_a_number) :-
    assertion(\+ valid_value(steering_play, abc)).

test(year_is_integer_in_range) :-
    assertion(valid_value(year, 2010)),
    assertion(\+ valid_value(year, 1949)),
    assertion(\+ valid_value(year, 2027)),
    assertion(\+ valid_value(year, 2010.5)).

test(unknown_is_allowed_except_required_keys) :-
    assertion(valid_value(brake_force, unknown)),
    assertion(valid_value(parking_brake, unknown)),
    assertion(\+ valid_value(category, unknown)),
    assertion(\+ valid_value(year, unknown)),
    assertion(\+ valid_value(fuel, unknown)).

test(hints_list_labels_and_unknown) :-
    answer_hint(parking_brake, H1),
    assertion(H1 == "удерживает / слабо / не удерживает / неизвестно"),
    answer_hint(fuel, H2),
    assertion(H2 == "бензин / дизель / газ / электро"),
    answer_hint(brake_force, H3),
    assertion(H3 == "число от 0 до 1.2 / неизвестно"),
    answer_hint(year, H4),
    assertion(H4 == "целое число от 1950 до 2026").

test(value_text_uses_label_or_number) :-
    value_text(parking_brake, weak, T1),
    assertion(T1 == "слабо"),
    value_text(brake_force, 0.8, T2),
    assertion(T2 == "0.8"),
    value_text(first_aid_kit, yes, T3),
    assertion(T3 == "да").

test(validate_accepts_partial_list_with_required_keys) :-
    validate_answers([category-m1, year-2015, fuel-petrol], Errors),
    assertion(Errors == []).

test(validate_reports_unknown_key) :-
    validate_answers([category-m1, year-2015, fuel-petrol, colour-red], Errors),
    assertion(length(Errors, 1)).

test(validate_reports_bad_value_and_out_of_range) :-
    validate_answers([category-m1, year-2015, fuel-petrol,
                      brake_force-9, parking_brake-broken], Errors),
    assertion(length(Errors, 2)).

test(validate_reports_duplicate_key_once) :-
    validate_answers([category-m1, year-2015, fuel-petrol,
                      brake_leak-tight, brake_leak-major], Errors),
    assertion(length(Errors, 1)).

test(validate_reports_missing_required_key) :-
    validate_answers([category-m1, year-2015], Errors),
    assertion(length(Errors, 1)).

test(validate_rejects_unknown_for_required_key) :-
    validate_answers([category-unknown, year-2015, fuel-petrol], Errors),
    assertion(length(Errors, 1)).

test(validate_reports_non_pair_and_non_list) :-
    validate_answers([category-m1, year-2015, fuel-petrol, oops], E1),
    assertion(length(E1, 1)),
    validate_answers(not_a_list, E2),
    assertion(length(E2, 1)).

:- end_tests(domain).
```

**Дописать в конец `tests/all.pl`:**
```prolog
:- consult(test_domain).
```

- [ ] **Step 2: Запустить тесты, убедиться, что падают**

Run: `./scripts/run_tests.sh`
Expected: ошибка загрузки — `source_sink '../src/domain' does not exist` (модуля ещё нет).

- [ ] **Step 3: Реализовать `src/domain.pl`**

**Создать `src/domain.pl`:**
```prolog
:- encoding(utf8).

:- module(domain, [
    question/3,
    known_question_key/1,
    required_key/1,
    fuel_specific/2,
    question_applies/2,
    valid_value/2,
    validate_answers/2,
    answer_hint/2,
    key_label/2,
    value_label/3,
    value_text/3,
    group_label/2,
    severity_label/2,
    verdict_label/2,
    action_label/2
]).

:- use_module(library(lists)).
:- use_module(library(apply)).

/** <module> Предметная модель экспертной системы технического осмотра

Модуль описывает входные признаки (28 штук), допустимые значения и диапазоны,
русские подписи для диалога и объяснений, а также проверку допустимости
данных, переданных программным вызовом (п. 5.1.3, 5.2.1 ТЗ).
*/

% Признаки перечислены в порядке диалога. Kind описывает допустимые значения:
%   choice(Values)      — одно из перечисленных значений;
%   int_range(Min,Max)  — целое число в пределах Min..Max включительно;
%   num_range(Min,Max)  — число в пределах Min..Max включительно.

% Общие сведения.
question(category, "Категория транспортного средства",
         choice([m1, m2_m3, n1, n2_n3])).
question(year, "Год выпуска", int_range(1950, 2026)).
question(fuel, "Тип топлива", choice([petrol, diesel, gas, electric])).

% Тормозная система.
question(brake_force, "Удельная тормозная сила рабочей тормозной системы",
         num_range(0, 1.2)).
question(brake_imbalance, "Неравномерность тормозных сил колёс оси, %",
         num_range(0, 100)).
question(parking_brake, "Стояночная тормозная система",
         choice([holds, weak, fails])).
question(brake_leak, "Герметичность тормозного привода",
         choice([tight, minor, major])).

% Рулевое управление.
question(steering_play, "Суммарный люфт рулевого управления, °",
         num_range(0, 90)).
question(steering_joints, "Шарниры и тяги рулевого привода",
         choice([ok, worn, broken])).

% Внешние световые приборы.
question(headlights, "Фары ближнего и дальнего света",
         choice([ok, one_faulty, not_working])).
question(headlight_aim, "Регулировка фар", choice([ok, misaligned])).
question(signal_lights, "Сигнальные фонари",
         choice([ok, partial, not_working])).
question(reflectors, "Световозвращатели", choice([present, missing])).

% Шины и колёса.
question(tread_depth, "Глубина протектора шин, мм", num_range(0, 15)).
question(tire_condition, "Состояние шин",
         choice([ok, damaged, cord_visible])).
question(wheel_fasteners, "Крепление колёс", choice([ok, missing])).

% Приборы обзора и стеклоочистители.
question(windshield, "Ветровое стекло",
         choice([intact, chips, driver_crack])).
question(wipers, "Стеклоочистители", choice([ok, worn, not_working])).
question(mirrors, "Зеркала заднего вида", choice([ok, damaged, missing])).

% Экологические показатели (спрашиваются по типу топлива).
question(co, "Содержание CO в отработавших газах, %", num_range(0, 10)).
question(ch, "Содержание CH в отработавших газах, ppm", num_range(0, 5000)).
question(smoke, "Дымность отработавших газов, 1/м", num_range(0, 10)).

% Прочие элементы конструкции и обязательная комплектация.
question(seat_belts, "Ремни безопасности", choice([ok, faulty, missing])).
question(first_aid_kit, "Аптечка", choice([yes, no])).
question(fire_extinguisher, "Огнетушитель", choice([yes, no])).
question(warning_triangle, "Знак аварийной остановки", choice([yes, no])).
question(structure, "Несущие элементы конструкции",
         choice([ok, corrosion, destroyed])).
question(fluid_leaks, "Утечки эксплуатационных жидкостей",
         choice([none, traces, dripping, fuel])).

known_question_key(Key) :-
    question(Key, _, _).

% От категории, года и типа топлива зависят пороги и набор вопросов, поэтому
% ответ «неизвестно» для них недопустим.
required_key(category).
required_key(year).
required_key(fuel).

% Признаки, которые спрашиваются только для указанных типов топлива.
fuel_specific(co, [petrol, gas]).
fuel_specific(ch, [petrol, gas]).
fuel_specific(smoke, [diesel]).

%! question_applies(+Key, +Fuel) is semidet.
%
%  Истинно, если признак Key нужно спрашивать при типе топлива Fuel.
question_applies(Key, Fuel) :-
    (   fuel_specific(Key, Fuels)
    ->  memberchk(Fuel, Fuels)
    ;   true
    ).

%! valid_value(+Key, +Value) is semidet.
valid_value(Key, unknown) :-
    known_question_key(Key),
    \+ required_key(Key).
valid_value(Key, Value) :-
    question(Key, _, Kind),
    valid_kind_value(Kind, Value).

valid_kind_value(choice(Allowed), Value) :-
    memberchk(Value, Allowed).
valid_kind_value(int_range(Min, Max), Value) :-
    integer(Value),
    Value >= Min,
    Value =< Max.
valid_kind_value(num_range(Min, Max), Value) :-
    number(Value),
    Value >= Min,
    Value =< Max.

%! validate_answers(+Answers, -Errors:list(string)) is det.
%
%  Проверка программного интерфейса до вывода: формат пар, известные
%  ключи, допустимость значений, повторы и наличие обязательных признаков.
validate_answers(Answers, Errors) :-
    (   is_list(Answers)
    ->  findall(Error, answer_error(Answers, Error), Raw),
        list_to_set(Raw, Errors)
    ;   Errors = ["Набор ответов должен быть списком пар Ключ-Значение."]
    ).

answer_error(Answers, Message) :-
    member(Item, Answers),
    \+ Item = _-_,
    format(string(Message), "Элемент ~q не является парой Ключ-Значение.", [Item]).
answer_error(Answers, Message) :-
    member(Key-_, Answers),
    \+ known_question_key(Key),
    format(string(Message), "Неизвестный входной признак: ~q.", [Key]).
answer_error(Answers, Message) :-
    member(Key-Value, Answers),
    known_question_key(Key),
    \+ valid_value(Key, Value),
    (   Value == unknown
    ->  format(string(Message),
               "Признак ~q обязателен: значение unknown недопустимо.", [Key])
    ;   format(string(Message),
               "Недопустимое значение ~q для признака ~q.", [Value, Key])
    ).
answer_error(Answers, Message) :-
    member(Key-_, Answers),
    include(pair_has_key(Key), Answers, Matches),
    length(Matches, Count),
    Count > 1,
    format(string(Message), "Признак ~q указан несколько раз.", [Key]).
answer_error(Answers, Message) :-
    required_key(Key),
    \+ memberchk(Key-_, Answers),
    format(string(Message), "Не указан обязательный признак ~q.", [Key]).

pair_has_key(Key, Key-_).

%! answer_hint(+Key, -Hint:string) is det.
%
%  Подсказка о допустимых ответах для диалога.
answer_hint(Key, Hint) :-
    question(Key, _, Kind),
    kind_hint(Key, Kind, Base),
    (   required_key(Key)
    ->  Hint = Base
    ;   string_concat(Base, " / неизвестно", Hint)
    ).

kind_hint(Key, choice(Values), Hint) :-
    maplist(value_text(Key), Values, Labels),
    atomic_list_concat(Labels, ' / ', Atom),
    atom_string(Atom, Hint).
kind_hint(_, int_range(Min, Max), Hint) :-
    format(string(Hint), "целое число от ~w до ~w", [Min, Max]).
kind_hint(_, num_range(Min, Max), Hint) :-
    format(string(Hint), "число от ~w до ~w", [Min, Max]).

%! key_label(+Key, -Text) is det.
%  Подпись признака в объяснениях совпадает с текстом вопроса.
key_label(Key, Text) :-
    question(Key, Text, _).

%! value_text(+Key, +Value, -Text:string) is det.
%  Русская подпись значения; для чисел и незнакомых значений — само значение.
value_text(Key, Value, Text) :-
    (   value_label(Key, Value, Label)
    ->  Text = Label
    ;   format(string(Text), "~w", [Value])
    ).

value_label(_, unknown, "неизвестно").
value_label(Key, yes, "да") :- yes_no_key(Key).
value_label(Key, no, "нет") :- yes_no_key(Key).
value_label(category, m1, "M1").
value_label(category, m2_m3, "M2-M3").
value_label(category, n1, "N1").
value_label(category, n2_n3, "N2-N3").
value_label(fuel, petrol, "бензин").
value_label(fuel, diesel, "дизель").
value_label(fuel, gas, "газ").
value_label(fuel, electric, "электро").
value_label(parking_brake, holds, "удерживает").
value_label(parking_brake, weak, "слабо").
value_label(parking_brake, fails, "не удерживает").
value_label(brake_leak, tight, "герметичен").
value_label(brake_leak, minor, "малая утечка").
value_label(brake_leak, major, "значительная утечка").
value_label(steering_joints, ok, "исправны").
value_label(steering_joints, worn, "изношены").
value_label(steering_joints, broken, "разрушены").
value_label(headlights, ok, "исправны").
value_label(headlights, one_faulty, "одна неисправна").
value_label(headlights, not_working, "не работают").
value_label(headlight_aim, ok, "в норме").
value_label(headlight_aim, misaligned, "нарушена").
value_label(signal_lights, ok, "исправны").
value_label(signal_lights, partial, "частично").
value_label(signal_lights, not_working, "не работают").
value_label(reflectors, present, "на месте").
value_label(reflectors, missing, "отсутствуют").
value_label(tire_condition, ok, "норма").
value_label(tire_condition, damaged, "повреждены").
value_label(tire_condition, cord_visible, "виден корд").
value_label(wheel_fasteners, ok, "в норме").
value_label(wheel_fasteners, missing, "нет крепёжных элементов").
value_label(windshield, intact, "целое").
value_label(windshield, chips, "сколы").
value_label(windshield, driver_crack, "трещина в зоне водителя").
value_label(wipers, ok, "исправны").
value_label(wipers, worn, "изношены").
value_label(wipers, not_working, "не работают").
value_label(mirrors, ok, "исправны").
value_label(mirrors, damaged, "повреждены").
value_label(mirrors, missing, "отсутствуют").
value_label(seat_belts, ok, "исправны").
value_label(seat_belts, faulty, "неисправны").
value_label(seat_belts, missing, "отсутствуют").
value_label(structure, ok, "норма").
value_label(structure, corrosion, "коррозия без потери несущей способности").
value_label(structure, destroyed, "разрушены").
value_label(fluid_leaks, none, "нет").
value_label(fluid_leaks, traces, "следы").
value_label(fluid_leaks, dripping, "капельные").
value_label(fluid_leaks, fuel, "топливо").

yes_no_key(first_aid_kit).
yes_no_key(fire_extinguisher).
yes_no_key(warning_triangle).

% Классы результата осмотра (п. 5.1.11 ТЗ).
group_label(brakes, "Тормозная система").
group_label(steering, "Рулевое управление").
group_label(lighting, "Внешние световые приборы и световозвращатели").
group_label(tires, "Шины и колёса").
group_label(visibility, "Приборы обзора и стеклоочистители").
group_label(ecology, "Экологические показатели").
group_label(other, "Прочие элементы конструкции и обязательная комплектация").

severity_label(critical, "критическая").
severity_label(major, "существенная").
severity_label(minor, "незначительная").

verdict_label(not_admitted, "не допущен к эксплуатации").
verdict_label(admitted_with_remarks,
              "допущен с замечаниями, требуется повторный осмотр").
verdict_label(admitted, "допущен к эксплуатации").

action_label(prohibited, "эксплуатация запрещена").
action_label(fix_before_reinspection,
             "устранить несоответствия до повторного осмотра").
action_label(allowed, "эксплуатация разрешена").
```

- [ ] **Step 4: Запустить тесты, убедиться, что проходят**

Run: `./scripts/run_tests.sh`
Expected: 20 тестов `passed` (последняя строка `[20/20] … passed`), код возврата 0.

- [ ] **Step 5: Commit**

```bash
git add src/domain.pl tests/test_domain.pl tests/all.pl
git commit -m "feat: domain model with 28 features, value validation and labels"
```

---

### Task 3: Пороги (`thresholds.pl`)

**Files:**
- Create: `src/thresholds.pl`
- Create: `tests/test_thresholds.pl`
- Modify: `tests/all.pl`

**Interfaces:**
- Produces (модуль `thresholds`):
  - `threshold(Name:atom, Column:atom, Value:number, Unit:string, Source:string)` — столбец: `m1|m2_m3|n1|n2_n3` (по категории ТС), `before_2000|from_2000` (по году выпуска), `any`.
  - `threshold_name(?Name)` — все различные имена, недетерминированно.
  - `threshold_value(+Name, +Columns:list, -Value)` — первый подходящий столбец из `Columns`. Вызывающий передаёт `[Категория, СтолбецГода, any]`.
  - `threshold_context_key(+Name, ?Key)` — `category` или `year`: какой ответ выбирает столбец порога (для `any` — нет).
- Имена порогов (используются правилами): `brake_force_min`, `brake_force_warn`, `brake_imbalance_warn`, `brake_imbalance_max`, `brake_imbalance_crit`, `steering_play_warn`, `steering_play_max`, `steering_play_crit`, `tread_min`, `tread_warn`, `co_max`, `co_warn`, `ch_max`, `ch_warn`, `smoke_max`, `smoke_warn`.

- [ ] **Step 1: Написать падающие тесты**

**Создать `tests/test_thresholds.pl`:**
```prolog
:- encoding(utf8).

:- use_module('../src/thresholds').

:- begin_tests(thresholds).

test(every_threshold_has_a_source) :-
    forall(threshold(_, _, _, _, Source),
           (   assertion(string(Source)),
               assertion(Source \== "")
           )).

test(every_threshold_is_a_number) :-
    forall(threshold(_, _, Value, _, _), assertion(number(Value))).

test(every_threshold_has_a_complete_column_set) :-
    forall(threshold_name(Name),
           (   findall(Column, threshold(Name, Column, _, _, _), Columns),
               assertion(   (   Columns == [m1, m2_m3, n1, n2_n3]
                            ;   Columns == [before_2000, from_2000]
                            ;   Columns == [any]
                            ))
           )).

test(sixteen_named_thresholds) :-
    findall(Name, threshold_name(Name), Names),
    length(Names, Count),
    assertion(Count =:= 16).

test(category_thresholds_follow_the_spec) :-
    threshold_value(brake_force_min, [m1, any], A),
    assertion(A =:= 0.59),
    threshold_value(brake_force_min, [n2_n3, any], B),
    assertion(B =:= 0.51),
    threshold_value(steering_play_max, [n2_n3, from_2000, any], C),
    assertion(C =:= 25),
    threshold_value(steering_play_crit, [m2_m3, any], D),
    assertion(D =:= 40),
    threshold_value(tread_min, [n2_n3, before_2000, any], E),
    assertion(E =:= 1.0).

test(year_column_selects_ecology_limits) :-
    threshold_value(co_max, [m1, before_2000, any], A),
    assertion(A =:= 3.5),
    threshold_value(co_max, [m1, from_2000, any], B),
    assertion(B =:= 0.5),
    threshold_value(ch_max, [n1, before_2000, any], C),
    assertion(C =:= 1200),
    threshold_value(ch_max, [n1, from_2000, any], D),
    assertion(D =:= 100).

test(category_independent_thresholds_use_any) :-
    threshold_value(brake_imbalance_max, [m1, from_2000, any], A),
    assertion(A =:= 20),
    threshold_value(smoke_max, [n2_n3, before_2000, any], B),
    assertion(B =:= 2.5).

test(context_key_tells_which_answer_selects_the_column) :-
    assertion(threshold_context_key(brake_force_min, category)),
    assertion(threshold_context_key(co_max, year)),
    assertion(\+ threshold_context_key(brake_imbalance_max, _)),
    assertion(\+ threshold_context_key(smoke_max, _)).

test(unknown_threshold_name_has_no_value) :-
    assertion(\+ threshold_value(no_such_threshold, [m1, any], _)).

:- end_tests(thresholds).
```

**Дописать в конец `tests/all.pl`:**
```prolog
:- consult(test_thresholds).
```

- [ ] **Step 2: Запустить тесты, убедиться, что падают**

Run: `./scripts/run_tests.sh`
Expected: ошибка загрузки — `source_sink '../src/thresholds' does not exist`.

- [ ] **Step 3: Реализовать `src/thresholds.pl`**

**Создать `src/thresholds.pl`:**
```prolog
:- encoding(utf8).

:- module(thresholds, [
    threshold/5,
    threshold_name/1,
    threshold_value/3,
    threshold_context_key/2
]).

/** <module> Пороговые значения контролируемых параметров (п. 5.8.3 ТЗ)

Все пороги, применяемые правилами базы знаний, собраны здесь отдельной
группой фактов threshold(Имя, Столбец, Значение, Единица, Источник).

Столбец выбирает значение:
  m1, m2_m3, n1, n2_n3 — по категории транспортного средства;
  before_2000, from_2000 — по году выпуска (год до 2000 / с 2000);
  any — не зависит ни от категории, ни от года.

ВАЖНО. Числа записаны по памяти и не сверены с оригиналами
ТР ТС 018/2011 (прил. 8) и ГОСТ 33997-2016. Значения, помеченные
«принято командой», — решение команды проекта. Все значения подтверждает
команда на этапе 2 ТЗ (анализ предметной области). Ошибка в числе меняет
результат осмотра, но не структуру системы.
*/

% --- Тормозная система -------------------------------------------------------

% Минимальная удельная тормозная сила рабочей тормозной системы.
threshold(brake_force_min, m1,    0.59, "отн. ед.", "ТР ТС 018/2011, прил. 8; ГОСТ 33997-2016").
threshold(brake_force_min, m2_m3, 0.51, "отн. ед.", "ТР ТС 018/2011, прил. 8; ГОСТ 33997-2016").
threshold(brake_force_min, n1,    0.51, "отн. ед.", "ТР ТС 018/2011, прил. 8; ГОСТ 33997-2016").
threshold(brake_force_min, n2_n3, 0.51, "отн. ед.", "ТР ТС 018/2011, прил. 8; ГОСТ 33997-2016").

% Верхняя граница зоны малого запаса тормозной силы: минимум + запас 0,05.
threshold(brake_force_warn, m1,    0.64, "отн. ед.", "принято командой: минимум + запас 0,05").
threshold(brake_force_warn, m2_m3, 0.56, "отн. ед.", "принято командой: минимум + запас 0,05").
threshold(brake_force_warn, n1,    0.56, "отн. ед.", "принято командой: минимум + запас 0,05").
threshold(brake_force_warn, n2_n3, 0.56, "отн. ед.", "принято командой: минимум + запас 0,05").

% Неравномерность тормозных сил колёс оси: предупреждение / допуск / критический предел.
threshold(brake_imbalance_warn, any, 15, "%", "принято командой").
threshold(brake_imbalance_max,  any, 20, "%", "ГОСТ 33997-2016").
threshold(brake_imbalance_crit, any, 30, "%", "принято командой").

% --- Рулевое управление ------------------------------------------------------

% Предупреждение о люфте: 80 % от предела.
threshold(steering_play_warn, m1,    8,  "°", "принято командой: 80 % от предела").
threshold(steering_play_warn, m2_m3, 16, "°", "принято командой: 80 % от предела").
threshold(steering_play_warn, n1,    8,  "°", "принято командой: 80 % от предела").
threshold(steering_play_warn, n2_n3, 20, "°", "принято командой: 80 % от предела").

% Предельный суммарный люфт рулевого управления.
threshold(steering_play_max, m1,    10, "°", "ТР ТС 018/2011, прил. 8").
threshold(steering_play_max, m2_m3, 20, "°", "ТР ТС 018/2011, прил. 8").
threshold(steering_play_max, n1,    10, "°", "ТР ТС 018/2011, прил. 8").
threshold(steering_play_max, n2_n3, 25, "°", "ТР ТС 018/2011, прил. 8").

% Критический люфт: двойной предел.
threshold(steering_play_crit, m1,    20, "°", "принято командой: двойной предел").
threshold(steering_play_crit, m2_m3, 40, "°", "принято командой: двойной предел").
threshold(steering_play_crit, n1,    20, "°", "принято командой: двойной предел").
threshold(steering_play_crit, n2_n3, 50, "°", "принято командой: двойной предел").

% --- Шины и колёса -----------------------------------------------------------

% Минимальная остаточная глубина рисунка протектора.
threshold(tread_min, m1,    1.6, "мм", "ТР ТС 018/2011, прил. 8").
threshold(tread_min, m2_m3, 2.0, "мм", "ТР ТС 018/2011, прил. 8").
threshold(tread_min, n1,    1.6, "мм", "ТР ТС 018/2011, прил. 8").
threshold(tread_min, n2_n3, 1.0, "мм", "ТР ТС 018/2011, прил. 8").

% Верхняя граница зоны малого запаса протектора: минимум + запас 1 мм.
threshold(tread_warn, m1,    2.6, "мм", "принято командой: минимум + запас 1 мм").
threshold(tread_warn, m2_m3, 3.0, "мм", "принято командой: минимум + запас 1 мм").
threshold(tread_warn, n1,    2.6, "мм", "принято командой: минимум + запас 1 мм").
threshold(tread_warn, n2_n3, 2.0, "мм", "принято командой: минимум + запас 1 мм").

% --- Экологические показатели ------------------------------------------------
% Пределы CO и CH выбирает год выпуска; дымность от года не зависит.

threshold(co_max,  before_2000, 3.5,  "%",   "ГОСТ 33997-2016").
threshold(co_max,  from_2000,   0.5,  "%",   "ГОСТ 33997-2016").
threshold(co_warn, before_2000, 3.15, "%",   "принято командой: 90 % от предела").
threshold(co_warn, from_2000,   0.45, "%",   "принято командой: 90 % от предела").
threshold(ch_max,  before_2000, 1200, "ppm", "ГОСТ 33997-2016").
threshold(ch_max,  from_2000,   100,  "ppm", "ГОСТ 33997-2016").
threshold(ch_warn, before_2000, 1080, "ppm", "принято командой: 90 % от предела").
threshold(ch_warn, from_2000,   90,   "ppm", "принято командой: 90 % от предела").
threshold(smoke_max,  any, 2.5,  "1/м", "ГОСТ 33997-2016").
threshold(smoke_warn, any, 2.25, "1/м", "принято командой: 90 % от предела").

%! threshold_name(?Name) is nondet.
threshold_name(Name) :-
    setof(N, C^V^U^S^threshold(N, C, V, U, S), Names),
    member(Name, Names).

%! threshold_value(+Name, +Columns:list, -Value) is semidet.
%
%  Берёт значение из первого столбца списка Columns, для которого порог
%  задан. Вызывающий передаёт [Категория, СтолбецГода, any].
threshold_value(Name, Columns, Value) :-
    member(Column, Columns),
    threshold(Name, Column, Value, _, _),
    !.

%! threshold_context_key(+Name, ?Key) is nondet.
%
%  Какой ответ выбирает столбец порога: category (по категории ТС) или
%  year (по году выпуска). Для порогов из столбца any ключа нет. Объяснение
%  показывает такой ответ рядом с признаками правила.
threshold_context_key(Name, category) :-
    threshold(Name, m1, _, _, _).
threshold_context_key(Name, year) :-
    threshold(Name, from_2000, _, _, _).
```

- [ ] **Step 4: Запустить тесты, убедиться, что проходят**

Run: `./scripts/run_tests.sh`
Expected: 29 тестов `passed` (последняя строка `[29/29] … passed`), код возврата 0.

- [ ] **Step 5: Commit**

```bash
git add src/thresholds.pl tests/test_thresholds.pl tests/all.pl
git commit -m "feat: thresholds as a separate fact group with sources"
```

---

### Task 4: Противоречия во входных данных (`consistency.pl`)

**Files:**
- Create: `src/consistency.pl`
- Create: `tests/test_consistency.pl`
- Modify: `tests/all.pl`

**Interfaces:**
- Consumes: список пар `Ключ-Значение` (значения — допустимые по `domain`).
- Produces: `consistency_issues(+Answers:list, -Issues:list(string))` — сообщения о взаимно несовместимых ответах; пустой список, если противоречий нет. «Неизвестно» противоречия не создаёт.

- [ ] **Step 1: Написать падающие тесты**

**Создать `tests/test_consistency.pl`:**
```prolog
:- encoding(utf8).

:- use_module('../src/consistency').

:- begin_tests(consistency).

test(consistent_petrol_car_has_no_issues) :-
    consistency_issues([fuel-petrol, co-0.3, ch-50, steering_play-3], Issues),
    assertion(Issues == []).

test(diesel_with_co_is_a_contradiction) :-
    consistency_issues([fuel-diesel, co-0.3], Issues),
    assertion(length(Issues, 1)).

test(diesel_with_ch_is_a_contradiction) :-
    consistency_issues([fuel-diesel, ch-50], Issues),
    assertion(length(Issues, 1)).

test(diesel_with_both_co_and_ch_reports_once) :-
    consistency_issues([fuel-diesel, co-0.3, ch-50], Issues),
    assertion(length(Issues, 1)).

test(unknown_measurement_is_not_a_contradiction) :-
    consistency_issues([fuel-diesel, co-unknown, ch-unknown], Issues),
    assertion(Issues == []).

test(petrol_with_smoke_is_a_contradiction) :-
    consistency_issues([fuel-petrol, smoke-1.0], Issues),
    assertion(length(Issues, 1)).

test(gas_with_smoke_is_a_contradiction) :-
    consistency_issues([fuel-gas, smoke-1.0], Issues),
    assertion(length(Issues, 1)).

test(electric_with_exhaust_values_is_a_contradiction) :-
    consistency_issues([fuel-electric, ch-100], Issues),
    assertion(length(Issues, 1)),
    consistency_issues([fuel-electric, smoke-1.0], Issues2),
    assertion(length(Issues2, 1)).

test(broken_joints_with_tiny_play_is_a_contradiction) :-
    consistency_issues([steering_joints-broken, steering_play-4], Issues),
    assertion(length(Issues, 1)).

test(broken_joints_with_play_of_five_degrees_is_consistent) :-
    consistency_issues([steering_joints-broken, steering_play-5], Issues),
    assertion(Issues == []).

test(broken_joints_with_unknown_play_is_consistent) :-
    consistency_issues([steering_joints-broken, steering_play-unknown], Issues),
    assertion(Issues == []).

test(electric_with_fuel_leak_is_a_contradiction) :-
    consistency_issues([fuel-electric, fluid_leaks-fuel], Issues),
    assertion(length(Issues, 1)).

test(petrol_with_fuel_leak_is_consistent) :-
    consistency_issues([fuel-petrol, fluid_leaks-fuel], Issues),
    assertion(Issues == []).

test(several_contradictions_are_all_reported) :-
    consistency_issues([fuel-electric, co-0.3, fluid_leaks-fuel,
                        steering_joints-broken, steering_play-1], Issues),
    assertion(length(Issues, 3)).

:- end_tests(consistency).
```

**Дописать в конец `tests/all.pl`:**
```prolog
:- consult(test_consistency).
```

- [ ] **Step 2: Запустить тесты, убедиться, что падают**

Run: `./scripts/run_tests.sh`
Expected: ошибка загрузки — `source_sink '../src/consistency' does not exist`.

- [ ] **Step 3: Реализовать `src/consistency.pl`**

**Создать `src/consistency.pl`:**
```prolog
:- encoding(utf8).

:- module(consistency, [consistency_issues/2]).

:- use_module(library(lists)).

/** <module> Противоречия во входных данных (п. 5.1.9, 5.2.2 ТЗ)

Проверяются пары ответов, которые не могут быть верными одновременно.
Каждое условие — отдельный факт consistency_issue/2. При противоречии
заключение не формируется (правило V08 базы знаний).

Ответ «неизвестно» противоречия не создаёт. Год выпуска позже 2026 здесь
не проверяется: допустимый диапазон года (1950…2026) отклоняет такой ввод
ещё при проверке допустимости в модуле domain.
*/

%! consistency_issues(+Answers:list, -Issues:list(string)) is det.
consistency_issues(Answers, Issues) :-
    findall(Message, consistency_issue(Answers, Message), Raw),
    list_to_set(Raw, Issues).

consistency_issue(Answers,
        "Для дизеля указаны CO или CH: у дизеля измеряется дымность.") :-
    memberchk(fuel-diesel, Answers),
    known_any(Answers, [co, ch]).
consistency_issue(Answers,
        "Для бензинового или газового двигателя указана дымность: измеряются CO и CH.") :-
    memberchk(fuel-Fuel, Answers),
    memberchk(Fuel, [petrol, gas]),
    known_any(Answers, [smoke]).
consistency_issue(Answers,
        "Для электромобиля указаны показатели выхлопа: отработавших газов у него нет.") :-
    memberchk(fuel-electric, Answers),
    known_any(Answers, [co, ch, smoke]).
consistency_issue(Answers,
        "Шарниры и тяги рулевого привода разрушены при суммарном люфте меньше 5°.") :-
    memberchk(steering_joints-broken, Answers),
    memberchk(steering_play-Play, Answers),
    number(Play),
    Play < 5.
consistency_issue(Answers,
        "Для электромобиля указана утечка топлива.") :-
    memberchk(fuel-electric, Answers),
    memberchk(fluid_leaks-fuel, Answers).

% Истинно, если хотя бы для одного из ключей дан известный ответ.
known_any(Answers, Keys) :-
    member(Key, Keys),
    memberchk(Key-Value, Answers),
    Value \== unknown,
    !.
```

- [ ] **Step 4: Запустить тесты, убедиться, что проходят**

Run: `./scripts/run_tests.sh`
Expected: 43 теста `passed` (последняя строка `[43/43] … passed`), код возврата 0.

- [ ] **Step 5: Commit**

```bash
git add src/consistency.pl tests/test_consistency.pl tests/all.pl
git commit -m "feat: detect contradictory input data"
```

---

### Task 5: Движок вывода, слой 2 и группа «Тормозная система» (P01–P10)

Вертикальный срез: после этой задачи система уже выдаёт заключение по ответам, хотя правила слоя 1 есть только для тормозов. Остальные группы добавляются задачами 6–8 без изменения движка.

**Files:**
- Create: `src/knowledge_base.pl`, `src/inference.pl`
- Create: `tests/fixtures.pl`, `tests/test_inference.pl`, `tests/test_rules_brakes.pl`
- Modify: `tests/all.pl`

**Interfaces:**
- Consumes: `domain:question/3`, `domain:question_applies/2`, `domain:validate_answers/2`, `domain:key_label/2`; `thresholds:threshold_value/3`; `consistency:consistency_issues/2`.
- Produces (модуль `knowledge_base`):
  - `rule_group(?Group)` — семь групп в порядке вывода.
  - `production_rule(Id, Group, Severity, Conditions:list, Text:string)` — слой 1; `Id` = `p01…p52`.
  - `verdict_rule(Id, Premises:list, Result, Text:string)` — слой 2; `Id` = `v01…v08`; `Result` = `verdict(V)` | `action(A)` | `status(S)`; посылки `has(Flag)`, `lacks(Flag)`, `verdict(V)`, `Flag` ∈ `critical, major, minor, complete, contradiction`.
  - Условия правил: `eq(Key,Value)`, `in(Key,[Value,…])`, `ge(Key,Number)`, `lt(Key,Number)` (число задано в правиле) и `lt_t/le_t/gt_t/ge_t(Key, ThresholdName)` (порог по категории/году).
- Produces (модуль `inference`):
  - `inspect_answers(+Answers, -Report)` — проверка допустимости, вывод, очистка хранилища.
  - `evaluate_answers(+Answers, -Report)` — чистый вывод без проверки допустимости и без хранилища.
  - `inspect_current(-Report)` — вывод по ответам из хранилища.
  - `set_answers(+Answers)`, `clear_answers/0`, `current_answer(?Key, ?Value)` — хранилище текущего осмотра.
  - `conditions_hold(+Conditions, +Answers)`; `fire_verdict_rules(+State:list, -Verdict, -Fired:list(Id-Result))`.
  - `rule_count(-N)` (слой 1), `rule_count_by_group(+Group, -N)`, `verdict_rule_count(-N)`.
  - `Report` — dict тега `report` с полями: `status` (`ok|insufficient_data|contradiction|invalid_input`), `verdict` (`not_admitted|admitted_with_remarks|admitted|none`), `action` (`prohibited|fix_before_reinspection|allowed|none`), `findings` (список dict тега `finding` с полями `rule, group, severity, text, evidence`), `verdict_rules` (список `v..`), `unknown` (список ключей), `diagnostics` (список строк).
- Produces (модуль `fixtures`, только тесты): `clean_answers(-Answers)`, `with_answers(+Overrides, +Base, -Answers)`, `without_answers(+Keys, +Base, -Answers)`, `report_ids(+Report, -Ids)`, `inspection_ids(+Answers, -Ids)`, `rules_for(+Overrides, -Ids)` (правила, сработавшие на исправном M1 с изменёнными ответами), `severity_of(+Overrides, +RuleId, -Severity)`.

- [ ] **Step 1: Написать общие данные тестов**

Исправный набор — легковой M1 2015 г., бензин, все показатели в норме; на нём не срабатывает ни одно правило слоя 1, включая «незначительные».

**Создать `tests/fixtures.pl`:**
```prolog
:- encoding(utf8).

:- module(fixtures, [
    clean_answers/1,
    with_answers/3,
    without_answers/3,
    report_ids/2,
    inspection_ids/2,
    rules_for/2,
    severity_of/3
]).

:- use_module('../src/inference').
:- use_module(library(lists)).
:- use_module(library(apply)).

/** <module> Общие данные автоматических проверок */

% Исправный легковой автомобиль: M1, 2015 г., бензин; ни одно правило не срабатывает.
clean_answers([
    category-m1, year-2015, fuel-petrol,
    brake_force-0.8, brake_imbalance-5, parking_brake-holds, brake_leak-tight,
    steering_play-3, steering_joints-ok,
    headlights-ok, headlight_aim-ok, signal_lights-ok, reflectors-present,
    tread_depth-5.0, tire_condition-ok, wheel_fasteners-ok,
    windshield-intact, wipers-ok, mirrors-ok,
    co-0.2, ch-50,
    seat_belts-ok, first_aid_kit-yes, fire_extinguisher-yes, warning_triangle-yes,
    structure-ok, fluid_leaks-none
]).

%! with_answers(+Overrides, +Base, -Answers) is det.
%  Заменяет (или добавляет) ответы Base по ключам из Overrides.
with_answers(Overrides, Base, Answers) :-
    foldl(put_answer, Overrides, Base, Answers).

put_answer(Key-Value, Answers0, [Key-Value|Rest]) :-
    (   selectchk(Key-_, Answers0, Rest)
    ->  true
    ;   Rest = Answers0
    ).

%! without_answers(+Keys, +Base, -Answers) is det.
without_answers(Keys, Base, Answers) :-
    exclude(pair_key_in(Keys), Base, Answers).

pair_key_in(Keys, Key-_) :-
    memberchk(Key, Keys).

%! report_ids(+Report, -Ids) is det.
%  Номера сработавших правил слоя 1 в порядке базы знаний.
report_ids(Report, Ids) :-
    get_dict(findings, Report, Findings),
    findall(Id, (member(Finding, Findings), get_dict(rule, Finding, Id)), Ids).

inspection_ids(Answers, Ids) :-
    inspect_answers(Answers, Report),
    report_ids(Report, Ids).

%! rules_for(+Overrides, -Ids) is det.
rules_for(Overrides, Ids) :-
    clean_answers(Base),
    with_answers(Overrides, Base, Answers),
    inspection_ids(Answers, Ids).

%! severity_of(+Overrides, +RuleId, -Severity) is semidet.
severity_of(Overrides, RuleId, Severity) :-
    clean_answers(Base),
    with_answers(Overrides, Base, Answers),
    inspect_answers(Answers, Report),
    get_dict(findings, Report, Findings),
    member(Finding, Findings),
    get_dict(rule, Finding, RuleId),
    get_dict(severity, Finding, Severity),
    !.
```

- [ ] **Step 2: Написать падающие тесты движка и слоя 2**

**Создать `tests/test_inference.pl`:**
```prolog
:- encoding(utf8).

:- use_module('../src/inference').
:- use_module(fixtures).

:- begin_tests(inference).

test(clean_car_is_admitted) :-
    clean_answers(Answers),
    inspect_answers(Answers, Report),
    assertion(Report.status == ok),
    assertion(Report.verdict == admitted),
    assertion(Report.action == allowed),
    assertion(Report.findings == []),
    assertion(Report.verdict_rules == [v03, v06]),
    assertion(Report.unknown == []),
    assertion(Report.diagnostics == []).

test(critical_finding_gives_not_admitted) :-
    clean_answers(Base),
    with_answers([brake_force-0.4], Base, Answers),
    inspect_answers(Answers, Report),
    assertion(Report.status == ok),
    assertion(Report.verdict == not_admitted),
    assertion(Report.action == prohibited),
    assertion(Report.verdict_rules == [v01, v04]),
    report_ids(Report, Ids),
    assertion(Ids == [p01]).

test(major_finding_gives_admitted_with_remarks) :-
    clean_answers(Base),
    with_answers([brake_leak-minor], Base, Answers),
    inspect_answers(Answers, Report),
    assertion(Report.verdict == admitted_with_remarks),
    assertion(Report.action == fix_before_reinspection),
    assertion(Report.verdict_rules == [v02, v05]).

test(minor_finding_alone_still_admits) :-
    clean_answers(Base),
    with_answers([brake_force-0.6], Base, Answers),
    inspect_answers(Answers, Report),
    assertion(Report.verdict == admitted),
    assertion(Report.action == allowed),
    assertion(Report.verdict_rules == [v03, v06]),
    report_ids(Report, Ids),
    assertion(Ids == [p02]).

test(critical_wins_over_major_and_minor) :-
    clean_answers(Base),
    with_answers([brake_force-0.4, brake_leak-minor, brake_imbalance-16],
                 Base, Answers),
    inspect_answers(Answers, Report),
    assertion(Report.verdict == not_admitted),
    report_ids(Report, Ids),
    assertion(Ids == [p01, p03, p10]).

test(finding_carries_group_severity_text_and_evidence) :-
    clean_answers(Base),
    with_answers([brake_force-0.4], Base, Answers),
    inspect_answers(Answers, Report),
    [Finding] = Report.findings,
    assertion(Finding.group == brakes),
    assertion(Finding.severity == critical),
    assertion(string(Finding.text)),
    assertion(memberchk(brake_force-0.4, Finding.evidence)),
    assertion(memberchk(category-m1, Finding.evidence)).

test(unknown_answer_blocks_admission) :-
    clean_answers(Base),
    with_answers([brake_force-unknown], Base, Answers),
    inspect_answers(Answers, Report),
    assertion(Report.status == insufficient_data),
    assertion(Report.verdict == none),
    assertion(Report.action == none),
    assertion(Report.unknown == [brake_force]),
    assertion(Report.verdict_rules == [v07]),
    assertion(Report.diagnostics \== []).

test(missing_answer_is_treated_as_unknown) :-
    clean_answers(Base),
    without_answers([brake_force], Base, Answers),
    inspect_answers(Answers, Report),
    assertion(Report.status == insufficient_data),
    assertion(Report.unknown == [brake_force]).

test(unknown_with_only_minor_findings_is_insufficient) :-
    clean_answers(Base),
    with_answers([brake_force-unknown, brake_imbalance-16], Base, Answers),
    inspect_answers(Answers, Report),
    assertion(Report.status == insufficient_data),
    assertion(Report.verdict == none),
    report_ids(Report, Ids),
    assertion(Ids == [p03]).

test(critical_finding_is_issued_despite_unknown_data) :-
    clean_answers(Base),
    with_answers([brake_force-unknown, brake_leak-major], Base, Answers),
    inspect_answers(Answers, Report),
    assertion(Report.status == ok),
    assertion(Report.verdict == not_admitted),
    assertion(Report.action == prohibited),
    assertion(Report.unknown == [brake_force]),
    assertion(Report.diagnostics \== []).

test(electric_car_is_not_asked_about_exhaust) :-
    clean_answers(Base),
    with_answers([fuel-electric], Base, A1),
    without_answers([co, ch], A1, Answers),
    inspect_answers(Answers, Report),
    assertion(Report.status == ok),
    assertion(Report.verdict == admitted),
    assertion(Report.unknown == []).

test(diesel_needs_smoke_not_co_and_ch) :-
    clean_answers(Base),
    with_answers([fuel-diesel, smoke-1.0], Base, A1),
    without_answers([co, ch], A1, Answers),
    inspect_answers(Answers, Report),
    assertion(Report.status == ok),
    assertion(Report.verdict == admitted),
    assertion(Report.unknown == []).

test(diesel_without_smoke_is_incomplete) :-
    clean_answers(Base),
    with_answers([fuel-diesel], Base, A1),
    without_answers([co, ch], A1, Answers),
    inspect_answers(Answers, Report),
    assertion(Report.status == insufficient_data),
    assertion(Report.unknown == [smoke]).

test(contradictory_input_gives_diagnostic_and_no_verdict) :-
    clean_answers(Base),
    with_answers([fuel-diesel, co-0.3], Base, Answers),
    inspect_answers(Answers, Report),
    assertion(Report.status == contradiction),
    assertion(Report.verdict == none),
    assertion(Report.action == none),
    assertion(Report.findings == []),
    assertion(Report.verdict_rules == [v08]),
    assertion(Report.diagnostics \== []).

test(invalid_value_gives_invalid_input_status) :-
    inspect_answers([category-m1, year-2015, fuel-petrol, brake_force-9], Report),
    assertion(Report.status == invalid_input),
    assertion(Report.verdict == none),
    assertion(Report.findings == []),
    assertion(Report.diagnostics \== []).

test(missing_required_key_gives_invalid_input_status) :-
    inspect_answers([brake_force-0.8], Report),
    assertion(Report.status == invalid_input).

test(answers_are_cleared_after_inspection) :-
    clean_answers(Answers),
    inspect_answers(Answers, _),
    assertion(\+ current_answer(_, _)).

test(invalid_call_also_clears_previous_state) :-
    set_answers([brake_leak-major]),
    inspect_answers([brake_force-9], Report),
    assertion(Report.status == invalid_input),
    assertion(\+ current_answer(_, _)).

test(inspect_current_uses_stored_answers) :-
    clean_answers(Answers),
    set_answers(Answers),
    inspect_current(Report),
    clear_answers,
    assertion(Report.verdict == admitted),
    assertion(\+ current_answer(_, _)).

:- end_tests(inference).
```

**Создать `tests/test_rules_brakes.pl`:**
```prolog
:- encoding(utf8).

:- use_module(fixtures).

% Границы полос правил P01–P10 «Тормозная система». Каждое значение даёт
% ровно одно правило (или ни одного), так что полосы не пересекаются.
:- begin_tests(rules_brakes).

test(force_below_minimum_is_critical) :-
    rules_for([brake_force-0.58], Ids),
    assertion(Ids == [p01]),
    severity_of([brake_force-0.58], p01, S),
    assertion(S == critical).

test(force_at_minimum_is_small_margin) :-
    rules_for([brake_force-0.59], Ids),
    assertion(Ids == [p02]),
    severity_of([brake_force-0.59], p02, S),
    assertion(S == minor).

test(force_just_below_margin_edge_is_small_margin) :-
    rules_for([brake_force-0.63], Ids),
    assertion(Ids == [p02]).

test(force_at_margin_edge_is_clean) :-
    rules_for([brake_force-0.64], Ids),
    assertion(Ids == []).

test(force_limits_depend_on_category) :-
    rules_for([category-m2_m3, brake_force-0.55], Ids1),
    assertion(Ids1 == [p02]),
    rules_for([category-n2_n3, brake_force-0.50], Ids2),
    assertion(Ids2 == [p01]),
    rules_for([category-m1, brake_force-0.55], Ids3),
    assertion(Ids3 == [p01]).

test(imbalance_bands) :-
    rules_for([brake_imbalance-15], A),
    assertion(A == []),
    rules_for([brake_imbalance-16], B),
    assertion(B == [p03]),
    rules_for([brake_imbalance-20], C),
    assertion(C == [p03]),
    rules_for([brake_imbalance-21], D),
    assertion(D == [p04]),
    rules_for([brake_imbalance-30], E),
    assertion(E == [p04]),
    rules_for([brake_imbalance-31], F),
    assertion(F == [p05]).

test(imbalance_severities) :-
    severity_of([brake_imbalance-16], p03, S3),
    assertion(S3 == minor),
    severity_of([brake_imbalance-21], p04, S4),
    assertion(S4 == major),
    severity_of([brake_imbalance-31], p05, S5),
    assertion(S5 == critical).

test(parking_brake_fails_is_critical) :-
    rules_for([parking_brake-fails], Ids),
    assertion(Ids == [p06]),
    severity_of([parking_brake-fails], p06, S),
    assertion(S == critical).

test(parking_brake_weak_is_major_except_heavy_trucks) :-
    forall(member(Category, [m1, m2_m3, n1]),
           (   rules_for([category-Category, parking_brake-weak], Ids),
               assertion(Ids == [p07])
           )),
    severity_of([parking_brake-weak], p07, S7),
    assertion(S7 == major),
    rules_for([category-n2_n3, parking_brake-weak], Ids8),
    assertion(Ids8 == [p08]),
    severity_of([category-n2_n3, parking_brake-weak], p08, S8),
    assertion(S8 == critical).

test(brake_leak_rules) :-
    rules_for([brake_leak-major], A),
    assertion(A == [p09]),
    severity_of([brake_leak-major], p09, S9),
    assertion(S9 == critical),
    rules_for([brake_leak-minor], B),
    assertion(B == [p10]),
    severity_of([brake_leak-minor], p10, S10),
    assertion(S10 == major).

:- end_tests(rules_brakes).
```

**Дописать в конец `tests/all.pl`:**
```prolog
:- consult(test_inference).
:- consult(test_rules_brakes).
```

- [ ] **Step 3: Запустить тесты, убедиться, что падают**

Run: `./scripts/run_tests.sh`
Expected: ошибка загрузки — `source_sink '../src/inference' does not exist`.

- [ ] **Step 4: Создать базу знаний: слой 2 и группа «Тормозная система»**

Слой 2 стоит выше слоя 1 намеренно (см. «Отступления», п. 4): следующие задачи дописывают группы слоя 1 в конец файла.

**Создать `src/knowledge_base.pl`:**
```prolog
:- encoding(utf8).

:- module(knowledge_base, [
    rule_group/1,
    production_rule/5,
    verdict_rule/4
]).

/** <module> База знаний технического осмотра автомобилей

Правила хранятся фактами двух видов (п. 5.8.1 ТЗ):

  * verdict_rule(Id, Premises, Result, Text) — слой 2, V01–V08:
    «состояние осмотра → заключение и рекомендуемое действие».
    Состояние — множество флагов critical, major, minor, complete,
    contradiction. Правила V01–V03, V07, V08 взаимоисключающи по построению:
    в каждом состоянии срабатывает ровно одно из них.
  * production_rule(Id, Group, Severity, Conditions, Text) — слой 1, P01–P52:
    «признаки → несоответствие» с группой и степенью критичности.

Условия правил слоя 1:
  eq(Key, Value)          ответ равен значению;
  in(Key, [Value, ...])   ответ — одно из значений;
  ge(Key, N), lt(Key, N)  число из ответа не меньше / меньше N;
  lt_t, le_t, gt_t, ge_t (Key, Name)
                          число из ответа сравнивается с порогом Name из
                          модуля thresholds (значение по категории или году).
Полосы правил одного признака не пересекаются, поэтому одно значение не даёт
двух разных степеней критичности; это проверяет tests/conflict_check.pl.
Факты rule_group/1 и служебные предикаты в подсчёт правил не входят.
*/

rule_group(brakes).
rule_group(steering).
rule_group(lighting).
rule_group(tires).
rule_group(visibility).
rule_group(ecology).
rule_group(other).

% ============================================================================
% СЛОЙ 2. Правила заключения V01–V08.
% ============================================================================

% V01–V03, V07, V08. Состояние осмотра → итоговое заключение или статус.
verdict_rule(v01, [has(critical), lacks(contradiction)],
    verdict(not_admitted),
    "Есть критическое несоответствие: транспортное средство не допускается независимо от состояния остальных узлов (п. 5.2.5 ТЗ).").
verdict_rule(v02, [has(major), lacks(critical), has(complete), lacks(contradiction)],
    verdict(admitted_with_remarks),
    "Есть существенные несоответствия и нет критических, данные полны: допуск с замечаниями (п. 5.2.6 ТЗ).").
verdict_rule(v03, [lacks(critical), lacks(major), has(complete), lacks(contradiction)],
    verdict(admitted),
    "Несоответствий нет или они только незначительные, данные полны: допуск (п. 5.2.6 ТЗ).").

% V04–V06. Заключение → рекомендуемое действие владельцу.
verdict_rule(v04, [verdict(not_admitted)],
    action(prohibited),
    "Не допущен: эксплуатация запрещена.").
verdict_rule(v05, [verdict(admitted_with_remarks)],
    action(fix_before_reinspection),
    "Допущен с замечаниями: устранить несоответствия до повторного осмотра.").
verdict_rule(v06, [verdict(admitted)],
    action(allowed),
    "Допущен: эксплуатация разрешена.").

% V07, V08. Диагностика неполных и противоречивых данных (п. 5.1.9 ТЗ).
verdict_rule(v07, [lacks(critical), lacks(complete), lacks(contradiction)],
    status(insufficient_data),
    "Критических несоответствий нет, но часть признаков неизвестна: допускающее заключение не формируется.").
verdict_rule(v08, [has(contradiction)],
    status(contradiction),
    "Входные данные противоречивы: заключение не формируется.").

% ============================================================================
% СЛОЙ 1. Правила несоответствий P01–P52.
% ============================================================================

% P01–P10. Тормозная система.
production_rule(p01, brakes, critical,
    [lt_t(brake_force, brake_force_min)],
    "Удельная тормозная сила ниже минимально допустимой для категории ТС.").
production_rule(p02, brakes, minor,
    [ge_t(brake_force, brake_force_min), lt_t(brake_force, brake_force_warn)],
    "Малый запас удельной тормозной силы до минимально допустимой.").
production_rule(p03, brakes, minor,
    [gt_t(brake_imbalance, brake_imbalance_warn), le_t(brake_imbalance, brake_imbalance_max)],
    "Неравномерность тормозных сил колёс оси приближается к допустимому пределу.").
production_rule(p04, brakes, major,
    [gt_t(brake_imbalance, brake_imbalance_max), le_t(brake_imbalance, brake_imbalance_crit)],
    "Неравномерность тормозных сил колёс оси выше допустимой.").
production_rule(p05, brakes, critical,
    [gt_t(brake_imbalance, brake_imbalance_crit)],
    "Неравномерность тормозных сил колёс оси выше критической.").
production_rule(p06, brakes, critical,
    [eq(parking_brake, fails)],
    "Стояночная тормозная система не удерживает транспортное средство.").
production_rule(p07, brakes, major,
    [eq(parking_brake, weak), in(category, [m1, m2_m3, n1])],
    "Стояночная тормозная система удерживает слабо.").
production_rule(p08, brakes, critical,
    [eq(parking_brake, weak), eq(category, n2_n3)],
    "Стояночная тормозная система удерживает слабо: для тяжёлых грузовых ТС (N2–N3) это критическое несоответствие.").
production_rule(p09, brakes, critical,
    [eq(brake_leak, major)],
    "Значительная утечка из тормозного привода.").
production_rule(p10, brakes, major,
    [eq(brake_leak, minor)],
    "Малая утечка из тормозного привода.").
```

- [ ] **Step 5: Реализовать движок `src/inference.pl`**

**Создать `src/inference.pl`:**
```prolog
:- encoding(utf8).

:- module(inference, [
    inspect_answers/2,
    inspect_current/1,
    evaluate_answers/2,
    conditions_hold/2,
    fire_verdict_rules/3,
    set_answers/1,
    clear_answers/0,
    current_answer/2,
    rule_count/1,
    rule_count_by_group/2,
    verdict_rule_count/1
]).

:- use_module(domain).
:- use_module(thresholds).
:- use_module(consistency).
:- use_module(knowledge_base).
:- use_module(library(lists)).
:- use_module(library(apply)).

/** <module> Механизм логического вывода

Вывод двухслойный. Слой 1 отбирает правила несоответствий, у которых
выполнены все условия. Из найденных степеней критичности, полноты данных и
противоречий строится состояние осмотра; слой 2 по состоянию выдаёт
заключение, действие и статус отчёта.

Ядро (evaluate_answers/2) работает над списком пар Ключ-Значение и ничего не
хранит. Динамический предикат stored_answer/2 нужен диалогу: он держит ответы
текущего осмотра и очищается до и после осмотра (п. 5.1.4, 5.2.3 ТЗ).
*/

:- dynamic stored_answer/2.

%! inspect_answers(+Answers:list, -Report:dict) is det.
%
%  Независимый осмотр по списку пар Ключ-Значение без диалога. Данные
%  проверяются на допустимость; после построения отчёта ответы удаляются.
inspect_answers(Answers, Report) :-
    setup_call_cleanup(
        clear_answers,
        once(inspect_validated(Answers, Report)),
        clear_answers).

inspect_validated(Answers, Report) :-
    validate_answers(Answers, Errors),
    (   Errors == []
    ->  set_answers(Answers),
        inspect_current(Report)
    ;   make_report(invalid_input, none, none, [], [], [], Errors, Report)
    ).

%! set_answers(+Answers:list) is det.
%  Заменяет ответы текущего осмотра. Используется диалоговым модулем.
set_answers(Answers) :-
    clear_answers,
    maplist(store_answer, Answers).

store_answer(Key-Value) :-
    assertz(stored_answer(Key, Value)).

clear_answers :-
    retractall(stored_answer(_, _)).

current_answer(Key, Value) :-
    stored_answer(Key, Value).

%! inspect_current(-Report:dict) is det.
%  Вывод по ответам из хранилища.
inspect_current(Report) :-
    findall(Key-Value, stored_answer(Key, Value), Answers),
    evaluate_answers(Answers, Report).

%! evaluate_answers(+Answers:list, -Report:dict) is det.
%
%  Строит отчёт. При противоречии входных данных правила слоя 1 не
%  применяются, заключение не выдаётся (V08).
evaluate_answers(Answers, Report) :-
    consistency_issues(Answers, Issues),
    (   Issues == []
    ->  matching_findings(Answers, Findings)
    ;   Findings = []
    ),
    unknown_keys(Answers, Unknown),
    inspection_state(Issues, Findings, Unknown, State),
    fire_verdict_rules(State, Verdict, Fired),
    fired_status(Fired, Status),
    fired_action(Fired, Action),
    findall(Id, member(Id-_, Fired), VerdictRules),
    diagnostics(Status, Issues, Unknown, Diagnostics),
    make_report(Status, Verdict, Action, Findings, VerdictRules, Unknown,
                Diagnostics, Report).

make_report(Status, Verdict, Action, Findings, VerdictRules, Unknown,
            Diagnostics, report{
                status: Status,
                verdict: Verdict,
                action: Action,
                findings: Findings,
                verdict_rules: VerdictRules,
                unknown: Unknown,
                diagnostics: Diagnostics
            }).

% --- Слой 1: отбор правил несоответствий -------------------------------------

matching_findings(Answers, Findings) :-
    findall(finding{rule: Id, group: Group, severity: Severity,
                    text: Text, evidence: Evidence},
            (   production_rule(Id, Group, Severity, Conditions, Text),
                conditions_hold(Conditions, Answers),
                conditions_evidence(Conditions, Answers, Evidence)
            ),
            Findings).

%! conditions_hold(+Conditions:list, +Answers:list) is semidet.
%  Все условия выполнены. Ответ «неизвестно» не удовлетворяет ни одному.
conditions_hold(Conditions, Answers) :-
    threshold_columns(Answers, Columns),
    maplist(condition_holds(Answers, Columns), Conditions).

% Столбцы порогов: категория, столбец года (до 2000 / с 2000) и any.
threshold_columns(Answers, [Category, YearColumn, any]) :-
    (   memberchk(category-Category, Answers)
    ->  true
    ;   Category = any
    ),
    (   memberchk(year-Year, Answers),
        integer(Year)
    ->  (   Year < 2000
        ->  YearColumn = before_2000
        ;   YearColumn = from_2000
        )
    ;   YearColumn = any
    ).

condition_holds(Answers, _, eq(Key, Expected)) :-
    memberchk(Key-Expected, Answers).
condition_holds(Answers, _, in(Key, Options)) :-
    memberchk(Key-Value, Answers),
    memberchk(Value, Options).
condition_holds(Answers, _, Condition) :-
    literal_condition(Condition, Key, Op, Limit),
    numeric_answer(Answers, Key, Value),
    compare_numbers(Op, Value, Limit).
condition_holds(Answers, Columns, Condition) :-
    threshold_condition(Condition, Key, Op, Name),
    numeric_answer(Answers, Key, Value),
    threshold_value(Name, Columns, Limit),
    compare_numbers(Op, Value, Limit).

literal_condition(ge(Key, Limit), Key, >=, Limit).
literal_condition(lt(Key, Limit), Key, <, Limit).

threshold_condition(lt_t(Key, Name), Key, <, Name).
threshold_condition(le_t(Key, Name), Key, =<, Name).
threshold_condition(gt_t(Key, Name), Key, >, Name).
threshold_condition(ge_t(Key, Name), Key, >=, Name).

numeric_answer(Answers, Key, Value) :-
    memberchk(Key-Value, Answers),
    number(Value).

compare_numbers(Op, Value, Limit) :-
    call(Op, Value, Limit).

% Ответы, на которых основано срабатывание правила, в порядке условий.
% Для сравнения с порогом добавляется ответ, выбравший значение порога
% (категория ТС или год выпуска).
conditions_evidence(Conditions, Answers, Evidence) :-
    findall(Key-Value,
            (   member(Condition, Conditions),
                condition_answer_key(Condition, Key),
                memberchk(Key-Value, Answers)
            ),
            Raw),
    list_to_set(Raw, Evidence).

condition_answer_key(Condition, Key) :-
    arg(1, Condition, Key).
condition_answer_key(Condition, Key) :-
    threshold_condition(Condition, _, _, Name),
    threshold_context_key(Name, Key).

% --- Неизвестные признаки ----------------------------------------------------

%! unknown_keys(+Answers, -Keys) is det.
%  Признаки, которые спрашиваются при данном типе топлива, но не имеют
%  известного ответа (ответ «неизвестно» или отсутствует).
unknown_keys(Answers, Keys) :-
    (   memberchk(fuel-Fuel0, Answers)
    ->  Fuel = Fuel0
    ;   Fuel = none
    ),
    findall(Key,
            (   question(Key, _, _),
                question_applies(Key, Fuel),
                \+ known_answer(Answers, Key)
            ),
            Keys).

known_answer(Answers, Key) :-
    memberchk(Key-Value, Answers),
    Value \== unknown.

% --- Слой 2: состояние осмотра и правила заключения --------------------------

inspection_state(Issues, Findings, Unknown, State) :-
    findall(Flag, state_flag(Issues, Findings, Unknown, Flag), State).

state_flag(Issues, _, _, contradiction) :-
    Issues \== [].
state_flag(_, Findings, _, Severity) :-
    member(Severity, [critical, major, minor]),
    has_severity(Findings, Severity).
state_flag(_, _, Unknown, complete) :-
    Unknown == [].

has_severity(Findings, Severity) :-
    member(Finding, Findings),
    get_dict(severity, Finding, Severity),
    !.

%! fire_verdict_rules(+State:list, -Verdict, -Fired:list) is det.
%
%  Сначала находится заключение по правилам, зависящим только от состояния;
%  затем срабатывают все правила слоя 2 (включая правила действия,
%  зависящие от заключения). Fired — список Id-Result в порядке базы знаний.
fire_verdict_rules(State, Verdict, Fired) :-
    findall(V,
            (   verdict_rule(_, Premises, verdict(V), _),
                premises_hold(Premises, State, none)
            ),
            Verdicts),
    (   Verdicts = [Verdict|_]
    ->  true
    ;   Verdict = none
    ),
    findall(Id-Result,
            (   verdict_rule(Id, Premises, Result, _),
                premises_hold(Premises, State, Verdict)
            ),
            Fired).

premises_hold(Premises, State, Verdict) :-
    maplist(premise_holds(State, Verdict), Premises).

premise_holds(State, _, has(Flag)) :-
    memberchk(Flag, State).
premise_holds(State, _, lacks(Flag)) :-
    \+ memberchk(Flag, State).
premise_holds(_, Verdict, verdict(Expected)) :-
    Verdict == Expected.

fired_status(Fired, Status) :-
    (   member(_-status(S), Fired)
    ->  Status = S
    ;   Status = ok
    ).

fired_action(Fired, Action) :-
    (   member(_-action(A), Fired)
    ->  Action = A
    ;   Action = none
    ).

% --- Диагностические сообщения -----------------------------------------------

diagnostics(contradiction, Issues, _, Issues) :-
    !.
diagnostics(insufficient_data, _, Unknown, [Message]) :-
    !,
    unknown_labels(Unknown, Labels),
    format(string(Message),
           "Недостаточно данных для допускающего заключения. Не определены признаки: ~w.",
           [Labels]).
diagnostics(ok, _, [], []) :-
    !.
diagnostics(ok, _, Unknown, [Message]) :-
    unknown_labels(Unknown, Labels),
    format(string(Message),
           "Заключение обосновано найденными критическими несоответствиями. Не определены признаки: ~w.",
           [Labels]).

unknown_labels(Keys, Labels) :-
    maplist(key_label, Keys, Texts),
    atomic_list_concat(Texts, '; ', Labels).

% --- Подсчёт правил (п. 5.8.1 ТЗ) --------------------------------------------

%! rule_count(-Count) is det.  Правила слоя 1.
rule_count(Count) :-
    findall(Id, production_rule(Id, _, _, _, _), Ids),
    length(Ids, Count).

rule_count_by_group(Group, Count) :-
    findall(Id, production_rule(Id, Group, _, _, _), Ids),
    length(Ids, Count).

%! verdict_rule_count(-Count) is det.  Правила слоя 2.
verdict_rule_count(Count) :-
    findall(Id, verdict_rule(Id, _, _, _), Ids),
    length(Ids, Count).
```

- [ ] **Step 6: Запустить тесты, убедиться, что проходят**

Run: `./scripts/run_tests.sh`
Expected: 72 теста `passed` (последняя строка `[72/72] … passed`), код возврата 0, строк `failed` нет.

- [ ] **Step 7: Commit**

```bash
git add src/knowledge_base.pl src/inference.pl tests/fixtures.pl tests/test_inference.pl tests/test_rules_brakes.pl tests/all.pl
git commit -m "feat: inference engine, verdict layer and brake rules P01-P10"
```

---

### Task 6: Правила «Рулевое управление» (P11–P15) и «Световые приборы» (P16–P22)

**Files:**
- Modify: `src/knowledge_base.pl` (дописать в конец)
- Create: `tests/test_rules_steering_lighting.pl`
- Modify: `tests/all.pl`

**Interfaces:**
- Consumes: `fixtures:rules_for/2`, `fixtures:severity_of/3`; пороги `steering_play_warn|max|crit` (по категории).
- Produces: правила `p11…p22` в `production_rule/5`; движок не меняется.

- [ ] **Step 1: Написать падающие тесты**

Соответствие условию из спеки: люфт — три полосы «80–100 % предела (Н) / выше предела (С) / выше критического (К)»; отражатели — критичность зависит от категории.

**Создать `tests/test_rules_steering_lighting.pl`:**
```prolog
:- encoding(utf8).

:- use_module(fixtures).

% Границы полос правил P11–P22.
:- begin_tests(rules_steering_lighting).

test(play_bands_for_m1) :-
    rules_for([steering_play-8], A),
    assertion(A == []),
    rules_for([steering_play-9], B),
    assertion(B == [p11]),
    rules_for([steering_play-10], C),
    assertion(C == [p11]),
    rules_for([steering_play-11], D),
    assertion(D == [p12]),
    rules_for([steering_play-20], E),
    assertion(E == [p12]),
    rules_for([steering_play-21], F),
    assertion(F == [p13]).

test(play_limits_depend_on_category) :-
    rules_for([category-m2_m3, steering_play-17], A),
    assertion(A == [p11]),
    rules_for([category-m2_m3, steering_play-21], B),
    assertion(B == [p12]),
    rules_for([category-m2_m3, steering_play-41], C),
    assertion(C == [p13]),
    rules_for([category-n2_n3, steering_play-25], D),
    assertion(D == [p11]),
    rules_for([category-n2_n3, steering_play-26], E),
    assertion(E == [p12]),
    rules_for([category-n2_n3, steering_play-51], F),
    assertion(F == [p13]).

test(play_severities) :-
    severity_of([steering_play-9], p11, S11),
    assertion(S11 == minor),
    severity_of([steering_play-11], p12, S12),
    assertion(S12 == major),
    severity_of([steering_play-21], p13, S13),
    assertion(S13 == critical).

test(steering_joints) :-
    rules_for([steering_joints-worn], A),
    assertion(A == [p14]),
    severity_of([steering_joints-worn], p14, S14),
    assertion(S14 == major),
    rules_for([steering_joints-broken, steering_play-5], B),
    assertion(B == [p15]),
    severity_of([steering_joints-broken, steering_play-5], p15, S15),
    assertion(S15 == critical).

test(headlights) :-
    rules_for([headlights-not_working], A),
    assertion(A == [p16]),
    severity_of([headlights-not_working], p16, S16),
    assertion(S16 == critical),
    rules_for([headlights-one_faulty], B),
    assertion(B == [p17]),
    severity_of([headlights-one_faulty], p17, S17),
    assertion(S17 == major),
    rules_for([headlight_aim-misaligned], C),
    assertion(C == [p18]),
    severity_of([headlight_aim-misaligned], p18, S18),
    assertion(S18 == major).

test(signal_lights) :-
    rules_for([signal_lights-not_working], A),
    assertion(A == [p19]),
    severity_of([signal_lights-not_working], p19, S19),
    assertion(S19 == critical),
    rules_for([signal_lights-partial], B),
    assertion(B == [p20]),
    severity_of([signal_lights-partial], p20, S20),
    assertion(S20 == major).

test(reflectors_severity_depends_on_category) :-
    forall(member(Category, [m1, n1]),
           (   rules_for([category-Category, reflectors-missing], Ids),
               assertion(Ids == [p21])
           )),
    forall(member(Category, [m2_m3, n2_n3]),
           (   rules_for([category-Category, reflectors-missing], Ids),
               assertion(Ids == [p22])
           )),
    severity_of([reflectors-missing], p21, S21),
    assertion(S21 == minor),
    severity_of([category-m2_m3, reflectors-missing], p22, S22),
    assertion(S22 == major).

:- end_tests(rules_steering_lighting).
```

**Дописать в конец `tests/all.pl`:**
```prolog
:- consult(test_rules_steering_lighting).
```

- [ ] **Step 2: Запустить тесты, убедиться, что новые падают**

Run: `./scripts/run_tests.sh`
Expected: 7 новых тестов `rules_steering_lighting:…` — `FAILED`; остальные проходят; код возврата не 0.

- [ ] **Step 3: Дописать правила в `src/knowledge_base.pl`**

**Дописать в конец `src/knowledge_base.pl`:**
```prolog
% P11–P15. Рулевое управление.
production_rule(p11, steering, minor,
    [gt_t(steering_play, steering_play_warn), le_t(steering_play, steering_play_max)],
    "Суммарный люфт рулевого управления приближается к предельному (80–100 % предела).").
production_rule(p12, steering, major,
    [gt_t(steering_play, steering_play_max), le_t(steering_play, steering_play_crit)],
    "Суммарный люфт рулевого управления выше предельного.").
production_rule(p13, steering, critical,
    [gt_t(steering_play, steering_play_crit)],
    "Суммарный люфт рулевого управления выше критического.").
production_rule(p14, steering, major,
    [eq(steering_joints, worn)],
    "Шарниры и тяги рулевого привода изношены.").
production_rule(p15, steering, critical,
    [eq(steering_joints, broken)],
    "Шарниры или тяги рулевого привода разрушены.").

% P16–P22. Внешние световые приборы и световозвращатели.
production_rule(p16, lighting, critical,
    [eq(headlights, not_working)],
    "Фары ближнего и дальнего света не работают.").
production_rule(p17, lighting, major,
    [eq(headlights, one_faulty)],
    "Неисправна одна из фар ближнего или дальнего света.").
production_rule(p18, lighting, major,
    [eq(headlight_aim, misaligned)],
    "Регулировка фар нарушена.").
production_rule(p19, lighting, critical,
    [eq(signal_lights, not_working)],
    "Сигнальные фонари не работают.").
production_rule(p20, lighting, major,
    [eq(signal_lights, partial)],
    "Сигнальные фонари работают частично.").
production_rule(p21, lighting, minor,
    [eq(reflectors, missing), in(category, [m1, n1])],
    "Световозвращатели отсутствуют (для M1 и N1 — незначительное несоответствие).").
production_rule(p22, lighting, major,
    [eq(reflectors, missing), in(category, [m2_m3, n2_n3])],
    "Световозвращатели отсутствуют (для M2–M3 и N2–N3 — существенное несоответствие).").
```

- [ ] **Step 4: Запустить тесты, убедиться, что проходят**

Run: `./scripts/run_tests.sh`
Expected: 79 тестов `passed` (последняя строка `[79/79] … passed`), код возврата 0.

- [ ] **Step 5: Commit**

```bash
git add src/knowledge_base.pl tests/test_rules_steering_lighting.pl tests/all.pl
git commit -m "feat: steering and lighting rules P11-P22"
```

---

### Task 7: Правила «Шины и колёса» (P23–P27) и «Приборы обзора» (P28–P33)

**Files:**
- Modify: `src/knowledge_base.pl` (дописать в конец)
- Create: `tests/test_rules_tires_visibility.pl`
- Modify: `tests/all.pl`

**Interfaces:**
- Consumes: `fixtures:rules_for/2`, `fixtures:severity_of/3`; пороги `tread_min`, `tread_warn` (по категории).
- Produces: правила `p23…p33`.

- [ ] **Step 1: Написать падающие тесты**

**Создать `tests/test_rules_tires_visibility.pl`:**
```prolog
:- encoding(utf8).

:- use_module(fixtures).

% Границы полос правил P23–P33.
:- begin_tests(rules_tires_visibility).

test(tread_bands_for_m1) :-
    rules_for([tread_depth-1.59], A),
    assertion(A == [p23]),
    rules_for([tread_depth-1.6], B),
    assertion(B == [p24]),
    rules_for([tread_depth-2.59], C),
    assertion(C == [p24]),
    rules_for([tread_depth-2.6], D),
    assertion(D == []).

test(tread_limits_depend_on_category) :-
    rules_for([category-m2_m3, tread_depth-1.9], A),
    assertion(A == [p23]),
    rules_for([category-m2_m3, tread_depth-2.0], B),
    assertion(B == [p24]),
    rules_for([category-m2_m3, tread_depth-3.0], C),
    assertion(C == []),
    rules_for([category-n2_n3, tread_depth-0.9], D),
    assertion(D == [p23]),
    rules_for([category-n2_n3, tread_depth-1.0], E),
    assertion(E == [p24]),
    rules_for([category-n2_n3, tread_depth-2.0], F),
    assertion(F == []).

test(tread_severities) :-
    severity_of([tread_depth-1.5], p23, S23),
    assertion(S23 == critical),
    severity_of([tread_depth-2.0], p24, S24),
    assertion(S24 == minor).

test(tire_condition_and_fasteners) :-
    rules_for([tire_condition-cord_visible], A),
    assertion(A == [p25]),
    severity_of([tire_condition-cord_visible], p25, S25),
    assertion(S25 == critical),
    rules_for([tire_condition-damaged], B),
    assertion(B == [p26]),
    severity_of([tire_condition-damaged], p26, S26),
    assertion(S26 == major),
    rules_for([wheel_fasteners-missing], C),
    assertion(C == [p27]),
    severity_of([wheel_fasteners-missing], p27, S27),
    assertion(S27 == critical).

test(windshield) :-
    rules_for([windshield-driver_crack], A),
    assertion(A == [p28]),
    severity_of([windshield-driver_crack], p28, S28),
    assertion(S28 == critical),
    rules_for([windshield-chips], B),
    assertion(B == [p29]),
    severity_of([windshield-chips], p29, S29),
    assertion(S29 == minor).

test(wipers) :-
    rules_for([wipers-not_working], A),
    assertion(A == [p30]),
    severity_of([wipers-not_working], p30, S30),
    assertion(S30 == critical),
    rules_for([wipers-worn], B),
    assertion(B == [p31]),
    severity_of([wipers-worn], p31, S31),
    assertion(S31 == major).

test(mirrors) :-
    rules_for([mirrors-damaged], A),
    assertion(A == [p32]),
    severity_of([mirrors-damaged], p32, S32),
    assertion(S32 == major),
    rules_for([mirrors-missing], B),
    assertion(B == [p33]),
    severity_of([mirrors-missing], p33, S33),
    assertion(S33 == critical).

:- end_tests(rules_tires_visibility).
```

**Дописать в конец `tests/all.pl`:**
```prolog
:- consult(test_rules_tires_visibility).
```

- [ ] **Step 2: Запустить тесты, убедиться, что новые падают**

Run: `./scripts/run_tests.sh`
Expected: 7 новых тестов `rules_tires_visibility:…` — `FAILED`; остальные проходят.

- [ ] **Step 3: Дописать правила в `src/knowledge_base.pl`**

**Дописать в конец `src/knowledge_base.pl`:**
```prolog
% P23–P27. Шины и колёса.
production_rule(p23, tires, critical,
    [lt_t(tread_depth, tread_min)],
    "Глубина протектора ниже минимально допустимой для категории ТС.").
production_rule(p24, tires, minor,
    [ge_t(tread_depth, tread_min), lt_t(tread_depth, tread_warn)],
    "Малый запас глубины протектора до минимально допустимой.").
production_rule(p25, tires, critical,
    [eq(tire_condition, cord_visible)],
    "На шине виден корд.").
production_rule(p26, tires, major,
    [eq(tire_condition, damaged)],
    "Шины имеют повреждения.").
production_rule(p27, tires, critical,
    [eq(wheel_fasteners, missing)],
    "Отсутствуют крепёжные элементы колёс.").

% P28–P33. Приборы обзора и стеклоочистители.
production_rule(p28, visibility, critical,
    [eq(windshield, driver_crack)],
    "Трещина ветрового стекла в зоне обзора водителя.").
production_rule(p29, visibility, minor,
    [eq(windshield, chips)],
    "Сколы ветрового стекла.").
production_rule(p30, visibility, critical,
    [eq(wipers, not_working)],
    "Стеклоочистители не работают.").
production_rule(p31, visibility, major,
    [eq(wipers, worn)],
    "Стеклоочистители изношены.").
production_rule(p32, visibility, major,
    [eq(mirrors, damaged)],
    "Зеркала заднего вида повреждены.").
production_rule(p33, visibility, critical,
    [eq(mirrors, missing)],
    "Зеркала заднего вида отсутствуют.").
```

- [ ] **Step 4: Запустить тесты, убедиться, что проходят**

Run: `./scripts/run_tests.sh`
Expected: 86 тестов `passed` (последняя строка `[86/86] … passed`), код возврата 0.

- [ ] **Step 5: Commit**

```bash
git add src/knowledge_base.pl tests/test_rules_tires_visibility.pl tests/all.pl
git commit -m "feat: tires and visibility rules P23-P33"
```

---

### Task 8: Правила «Экология» (P34–P39) и «Прочее и комплектация» (P40–P52)

**Files:**
- Modify: `src/knowledge_base.pl` (дописать в конец)
- Create: `tests/test_rules_ecology_other.pl`
- Modify: `tests/all.pl`

**Interfaces:**
- Consumes: `fixtures:rules_for/2`, `severity_of/3`, `clean_answers/1`, `with_answers/3`, `without_answers/3`, `inspection_ids/2`; пороги `co_*`, `ch_*` (по году), `smoke_*`.
- Produces: правила `p34…p52`. После задачи в базе 52 правила слоя 1 и 8 правил слоя 2.

- [ ] **Step 1: Написать падающие тесты**

Исправный набор — год 2015, поэтому пределы CO 0,5 % и CH 100 ppm; год 1995 переключает на 3,5 % и 1200 ppm. Дизель проверяется набором без CO/CH, иначе это было бы противоречие входа.

**Создать `tests/test_rules_ecology_other.pl`:**
```prolog
:- encoding(utf8).

:- use_module(fixtures).

% Границы полос правил P34–P52.
:- begin_tests(rules_ecology_other).

% Дизель: вместо CO и CH спрашивается дымность.
diesel_ids(Overrides, Ids) :-
    clean_answers(Base),
    with_answers([fuel-diesel|Overrides], Base, A1),
    without_answers([co, ch], A1, Answers),
    inspection_ids(Answers, Ids).

test(co_bands_for_year_2015) :-
    rules_for([co-0.45], A),
    assertion(A == []),
    rules_for([co-0.46], B),
    assertion(B == [p37]),
    rules_for([co-0.5], C),
    assertion(C == [p37]),
    rules_for([co-0.51], D),
    assertion(D == [p34]).

test(ch_bands_for_year_2015) :-
    rules_for([ch-90], A),
    assertion(A == []),
    rules_for([ch-91], B),
    assertion(B == [p38]),
    rules_for([ch-100], C),
    assertion(C == [p38]),
    rules_for([ch-101], D),
    assertion(D == [p35]).

test(limits_for_cars_before_2000) :-
    rules_for([year-1995, co-3.15], A),
    assertion(A == []),
    rules_for([year-1995, co-3.16], B),
    assertion(B == [p37]),
    rules_for([year-1995, co-3.5], C),
    assertion(C == [p37]),
    rules_for([year-1995, co-3.6], D),
    assertion(D == [p34]),
    rules_for([year-1995, ch-1200], E),
    assertion(E == [p38]),
    rules_for([year-1995, ch-1201], F),
    assertion(F == [p35]).

test(year_2000_switches_to_strict_limits) :-
    rules_for([year-1999, co-1.0], A),
    assertion(A == []),
    rules_for([year-2000, co-1.0], B),
    assertion(B == [p34]).

test(smoke_bands_for_diesel) :-
    diesel_ids([smoke-2.25], A),
    assertion(A == []),
    diesel_ids([smoke-2.26], B),
    assertion(B == [p39]),
    diesel_ids([smoke-2.5], C),
    assertion(C == [p39]),
    diesel_ids([smoke-2.6], D),
    assertion(D == [p36]).

test(ecology_severities) :-
    severity_of([co-0.6], p34, S34),
    assertion(S34 == major),
    severity_of([ch-150], p35, S35),
    assertion(S35 == major),
    severity_of([co-0.46], p37, S37),
    assertion(S37 == minor),
    severity_of([ch-91], p38, S38),
    assertion(S38 == minor).

test(seat_belts_depend_on_year) :-
    rules_for([seat_belts-missing], A),
    assertion(A == [p40]),
    rules_for([year-1991, seat_belts-missing], B),
    assertion(B == [p40]),
    rules_for([year-1990, seat_belts-missing], C),
    assertion(C == [p41]),
    severity_of([seat_belts-missing], p40, S40),
    assertion(S40 == critical),
    severity_of([year-1990, seat_belts-missing], p41, S41),
    assertion(S41 == minor),
    rules_for([seat_belts-faulty], D),
    assertion(D == [p42]),
    severity_of([seat_belts-faulty], p42, S42),
    assertion(S42 == major).

test(first_aid_kit) :-
    rules_for([first_aid_kit-no], A),
    assertion(A == [p43]),
    severity_of([first_aid_kit-no], p43, S43),
    assertion(S43 == minor).

test(fire_extinguisher_severity_depends_on_category) :-
    forall(member(Category, [m1, n1]),
           (   rules_for([category-Category, fire_extinguisher-no], Ids),
               assertion(Ids == [p44])
           )),
    forall(member(Category, [m2_m3, n2_n3]),
           (   rules_for([category-Category, fire_extinguisher-no], Ids),
               assertion(Ids == [p45])
           )),
    severity_of([fire_extinguisher-no], p44, S44),
    assertion(S44 == minor),
    severity_of([category-n1, fire_extinguisher-no], p44, S44b),
    assertion(S44b == minor),
    severity_of([category-n2_n3, fire_extinguisher-no], p45, S45),
    assertion(S45 == major).

test(warning_triangle_severity_depends_on_category) :-
    forall(member(Category, [m1, n1]),
           (   rules_for([category-Category, warning_triangle-no], Ids),
               assertion(Ids == [p46])
           )),
    forall(member(Category, [m2_m3, n2_n3]),
           (   rules_for([category-Category, warning_triangle-no], Ids),
               assertion(Ids == [p47])
           )),
    severity_of([warning_triangle-no], p46, S46),
    assertion(S46 == minor),
    severity_of([category-m2_m3, warning_triangle-no], p47, S47),
    assertion(S47 == major).

test(structure) :-
    rules_for([structure-corrosion], A),
    assertion(A == [p48]),
    severity_of([structure-corrosion], p48, S48),
    assertion(S48 == minor),
    rules_for([structure-destroyed], B),
    assertion(B == [p49]),
    severity_of([structure-destroyed], p49, S49),
    assertion(S49 == critical).

test(fluid_leaks) :-
    rules_for([fluid_leaks-traces], A),
    assertion(A == [p50]),
    severity_of([fluid_leaks-traces], p50, S50),
    assertion(S50 == minor),
    rules_for([fluid_leaks-dripping], B),
    assertion(B == [p51]),
    severity_of([fluid_leaks-dripping], p51, S51),
    assertion(S51 == major),
    rules_for([fluid_leaks-fuel], C),
    assertion(C == [p52]),
    severity_of([fluid_leaks-fuel], p52, S52),
    assertion(S52 == critical).

:- end_tests(rules_ecology_other).
```

**Дописать в конец `tests/all.pl`:**
```prolog
:- consult(test_rules_ecology_other).
```

- [ ] **Step 2: Запустить тесты, убедиться, что новые падают**

Run: `./scripts/run_tests.sh`
Expected: 12 новых тестов `rules_ecology_other:…` — `FAILED`; остальные проходят.

- [ ] **Step 3: Дописать правила в `src/knowledge_base.pl`**

**Дописать в конец `src/knowledge_base.pl`:**
```prolog
% P34–P39. Экологические показатели. Пределы CO и CH выбирает год выпуска.
production_rule(p34, ecology, major,
    [gt_t(co, co_max)],
    "Содержание CO в отработавших газах выше предельного.").
production_rule(p35, ecology, major,
    [gt_t(ch, ch_max)],
    "Содержание CH в отработавших газах выше предельного.").
production_rule(p36, ecology, major,
    [gt_t(smoke, smoke_max)],
    "Дымность отработавших газов выше предельной.").
production_rule(p37, ecology, minor,
    [gt_t(co, co_warn), le_t(co, co_max)],
    "Содержание CO приближается к предельному (выше 90 % предела).").
production_rule(p38, ecology, minor,
    [gt_t(ch, ch_warn), le_t(ch, ch_max)],
    "Содержание CH приближается к предельному (выше 90 % предела).").
production_rule(p39, ecology, minor,
    [gt_t(smoke, smoke_warn), le_t(smoke, smoke_max)],
    "Дымность приближается к предельной (выше 90 % предела).").

% P40–P52. Прочие элементы конструкции и обязательная комплектация.
production_rule(p40, other, critical,
    [eq(seat_belts, missing), ge(year, 1991)],
    "Ремни безопасности отсутствуют на автомобиле, выпущенном с 1991 года.").
production_rule(p41, other, minor,
    [eq(seat_belts, missing), lt(year, 1991)],
    "Ремни безопасности отсутствуют на автомобиле, выпущенном до 1991 года.").
production_rule(p42, other, major,
    [eq(seat_belts, faulty)],
    "Ремни безопасности неисправны.").
production_rule(p43, other, minor,
    [eq(first_aid_kit, no)],
    "Отсутствует аптечка.").
production_rule(p44, other, minor,
    [eq(fire_extinguisher, no), in(category, [m1, n1])],
    "Отсутствует огнетушитель (для M1 и N1 — незначительное несоответствие).").
production_rule(p45, other, major,
    [eq(fire_extinguisher, no), in(category, [m2_m3, n2_n3])],
    "Отсутствует огнетушитель (для M2–M3 и N2–N3 — существенное несоответствие).").
production_rule(p46, other, minor,
    [eq(warning_triangle, no), in(category, [m1, n1])],
    "Отсутствует знак аварийной остановки (для M1 и N1 — незначительное несоответствие).").
production_rule(p47, other, major,
    [eq(warning_triangle, no), in(category, [m2_m3, n2_n3])],
    "Отсутствует знак аварийной остановки (для M2–M3 и N2–N3 — существенное несоответствие).").
production_rule(p48, other, minor,
    [eq(structure, corrosion)],
    "Коррозия несущих элементов без потери несущей способности.").
production_rule(p49, other, critical,
    [eq(structure, destroyed)],
    "Несущие элементы конструкции разрушены.").
production_rule(p50, other, minor,
    [eq(fluid_leaks, traces)],
    "Следы утечек эксплуатационных жидкостей.").
production_rule(p51, other, major,
    [eq(fluid_leaks, dripping)],
    "Капельные утечки эксплуатационных жидкостей.").
production_rule(p52, other, critical,
    [eq(fluid_leaks, fuel)],
    "Утечка топлива.").
```

- [ ] **Step 4: Запустить тесты, убедиться, что проходят**

Run: `./scripts/run_tests.sh`
Expected: 98 тестов `passed` (последняя строка `[98/98] … passed`), код возврата 0.

- [ ] **Step 5: Commit**

```bash
git add src/knowledge_base.pl tests/test_rules_ecology_other.pl tests/all.pl
git commit -m "feat: ecology and equipment rules P34-P52 (52 layer-1 rules in total)"
```

---

### Task 9: Структура базы знаний и проверка правил на конфликты

Закрывает испытания 4 и 12 (п. 5.1.5, 5.8.1, 5.2.4 ТЗ).

**Files:**
- Create: `tests/project_paths.pl`, `tests/conflict_check.pl`
- Create: `tests/test_rules_structure.pl`, `tests/test_conflicts.pl`
- Modify: `tests/all.pl`

**Interfaces:**
- Consumes: `knowledge_base:production_rule/5`, `verdict_rule/4`, `rule_group/1`; `inference:conditions_hold/2`, `fire_verdict_rules/3`, `rule_count/1`, `rule_count_by_group/2`, `verdict_rule_count/1`; `domain:question/3`; `thresholds:threshold/5`, `threshold_value/3`.
- Produces (модуль `project_paths`, тесты): `project_file(+Relative:atom, -Absolute:atom)` — путь от корня проекта, не зависящий от текущего каталога.
- Produces (модуль `conflict_check`, тесты и скрипт контрольной таблицы):
  - `layer1_pairs(-Pairs)` — пары `Id1-Id2` правил слоя 1 с общим признаком (кроме `category`, `year`) и разной критичностью;
  - `layer1_conflicts(-Conflicts)` — список `conflict(Id1, Id2, Answers)`: наборы ответов, при которых совпали оба правила пары; ожидается `[]`;
  - `overlap_witness(+Conditions1, +Conditions2, -Answers)` — найти набор ответов, удовлетворяющий обоим спискам условий (полу-детерминированно);
  - `layer2_states(-States)` — все 32 сочетания флагов `critical, major, minor, complete, contradiction`;
  - `layer2_violations(-Violations)` — состояния, где не ровно одно правило из V01–V03, V07, V08 или неверное число правил действия; ожидается `[]`.

- [ ] **Step 1: Написать общий модуль путей**

**Создать `tests/project_paths.pl`:**
```prolog
:- encoding(utf8).

:- module(project_paths, [project_file/2]).

:- use_module(library(filesex)).

/** <module> Пути к файлам проекта для тестов

Тесты открывают исходники и документы по пути от корня проекта, поэтому
результат не зависит от каталога, из которого запущен swipl.
*/

:- dynamic root_dir/1.

% tests/project_paths.pl лежит в <корень>/tests.
:- prolog_load_context(directory, Dir),
   file_directory_name(Dir, Root),
   assertz(root_dir(Root)).

%! project_file(+Relative, -Absolute) is det.
project_file(Relative, Absolute) :-
    root_dir(Root),
    directory_file_path(Root, Relative, Absolute).
```

- [ ] **Step 2: Написать падающие тесты структуры базы знаний**

Тест числа правил считает только факты `production_rule/5` и `verdict_rule/4`; пороги, подписи и `rule_group/1` в подсчёт не входят.

**Создать `tests/test_rules_structure.pl`:**
```prolog
:- encoding(utf8).

:- use_module('../src/knowledge_base').
:- use_module('../src/domain').
:- use_module('../src/thresholds').
:- use_module('../src/inference',
              [rule_count/1, rule_count_by_group/2, verdict_rule_count/1]).
:- use_module(project_paths).

:- begin_tests(rules_structure).

numbered_ids(Prefix, Count, Ids) :-
    findall(Id,
            (   between(1, Count, N),
                (   N < 10
                ->  format(atom(Id), '~w0~d', [Prefix, N])
                ;   format(atom(Id), '~w~d', [Prefix, N])
                )
            ),
            Ids).

test(layer1_has_at_least_fifty_rules) :-
    rule_count(Count),
    assertion(Count >= 50).

test(layer1_has_52_and_layer2_has_8_rules) :-
    rule_count(Layer1),
    verdict_rule_count(Layer2),
    assertion(Layer1 =:= 52),
    assertion(Layer2 =:= 8),
    assertion(Layer1 + Layer2 =:= 60).

test(rule_counts_by_group) :-
    forall(member(Group-Expected,
                  [brakes-10, steering-5, lighting-7, tires-5,
                   visibility-6, ecology-6, other-13]),
           (   rule_count_by_group(Group, Count),
               assertion(Count =:= Expected)
           )).

test(layer1_ids_are_unique_and_sequential) :-
    findall(Id, production_rule(Id, _, _, _, _), Ids),
    numbered_ids(p, 52, Expected),
    assertion(Ids == Expected).

test(layer2_ids_are_unique_and_sequential) :-
    findall(Id, verdict_rule(Id, _, _, _), Ids),
    numbered_ids(v, 8, Expected),
    assertion(Ids == Expected).

test(every_rule_has_known_group_severity_and_text) :-
    forall(production_rule(Id, Group, Severity, Conditions, Text),
           (   assertion(rule_group(Group)),
               assertion(memberchk(Severity, [critical, major, minor])),
               assertion(string(Text)),
               assertion(Text \== ""),
               assertion(Conditions \== []),
               assertion(atom(Id))
           )).

test(all_severities_and_groups_are_used) :-
    forall(member(Severity, [critical, major, minor]),
           assertion(production_rule(_, _, Severity, _, _))),
    forall(rule_group(Group),
           (   assertion(production_rule(_, Group, _, _, _)),
               assertion(group_label(Group, _))
           )).

test(condition_keys_are_known_features) :-
    forall((production_rule(_, _, _, Conditions, _), member(Condition, Conditions)),
           (   arg(1, Condition, Key),
               assertion(known_question_key(Key))
           )).

test(every_feature_is_used_by_rules_except_fuel) :-
    findall(Key,
            (   production_rule(_, _, _, Conditions, _),
                member(Condition, Conditions),
                arg(1, Condition, Key)
            ),
            Used0),
    sort(Used0, Used),
    findall(Key, (question(Key, _, _), \+ memberchk(Key, Used)), Unused),
    % Тип топлива не входит в условия правил: он выбирает набор вопросов
    % и проверяется в consistency.pl.
    assertion(Unused == [fuel]).

test(every_referenced_threshold_exists_for_every_category_and_year) :-
    forall((   production_rule(_, _, _, Conditions, _),
               member(Condition, Conditions),
               memberchk(Condition, [lt_t(_, _), le_t(_, _), gt_t(_, _), ge_t(_, _)]),
               arg(2, Condition, Name)
           ),
           forall((   member(Category, [m1, m2_m3, n1, n2_n3]),
                      member(YearColumn, [before_2000, from_2000])
                  ),
                  assertion(threshold_value(Name, [Category, YearColumn, any], _)))).

test(layer2_results_cover_all_verdicts_and_actions) :-
    forall(member(Verdict, [not_admitted, admitted_with_remarks, admitted]),
           (   assertion(verdict_rule(_, _, verdict(Verdict), _)),
               assertion(verdict_label(Verdict, _))
           )),
    forall(member(Action, [prohibited, fix_before_reinspection, allowed]),
           (   assertion(verdict_rule(_, _, action(Action), _)),
               assertion(action_label(Action, _))
           )).

test(knowledge_base_source_has_group_comments) :-
    project_file('src/knowledge_base.pl', Path),
    read_file_to_string(Path, Source, [encoding(utf8)]),
    forall(member(Header,
                  ["% P01–P10.", "% P11–P15.", "% P16–P22.", "% P23–P27.",
                   "% P28–P33.", "% P34–P39.", "% P40–P52.",
                   "% V01–V03", "% V04–V06", "% V07, V08."]),
           assertion(sub_string(Source, _, _, _, Header))).

:- end_tests(rules_structure).
```

- [ ] **Step 3: Написать падающие тесты проверки конфликтов**

**Создать `tests/test_conflicts.pl`:**
```prolog
:- encoding(utf8).

:- use_module(conflict_check).

% Испытание 12 (п. 5.2.4 ТЗ): проверка базы знаний на противоречивость.
:- begin_tests(conflicts).

test(layer1_has_pairs_to_check) :-
    layer1_pairs(Pairs),
    length(Pairs, Count),
    assertion(Count >= 20).

test(layer1_rules_with_a_common_feature_never_match_together) :-
    layer1_conflicts(Conflicts),
    assertion(Conflicts == []).

test(checker_finds_an_overlap_when_bands_overlap) :-
    overlap_witness([gt_t(steering_play, steering_play_max)],
                    [gt_t(steering_play, steering_play_crit)],
                    Answers),
    assertion(memberchk(steering_play-_, Answers)).

test(checker_finds_no_overlap_for_disjoint_bands) :-
    assertion(\+ overlap_witness([le_t(steering_play, steering_play_max)],
                                 [gt_t(steering_play, steering_play_max)],
                                 _)).

test(checker_respects_category_conditions) :-
    assertion(\+ overlap_witness([eq(reflectors, missing), in(category, [m1, n1])],
                                 [eq(reflectors, missing), in(category, [m2_m3, n2_n3])],
                                 _)),
    assertion(overlap_witness([eq(reflectors, missing), in(category, [m1, n1])],
                              [eq(reflectors, missing), in(category, [m1])],
                              _)).

test(layer2_covers_all_32_states) :-
    layer2_states(States),
    length(States, Count),
    assertion(Count =:= 32),
    sort(States, Unique),
    assertion(length(Unique, 32)).

test(layer2_gives_exactly_one_outcome_in_every_state) :-
    layer2_violations(Violations),
    assertion(Violations == []).

:- end_tests(conflicts).
```

**Дописать в конец `tests/all.pl`:**
```prolog
:- consult(test_rules_structure).
:- consult(test_conflicts).
```

- [ ] **Step 4: Запустить тесты, убедиться, что падают**

Run: `./scripts/run_tests.sh`
Expected: ошибка загрузки — `source_sink 'conflict_check' does not exist`.

- [ ] **Step 5: Реализовать `tests/conflict_check.pl`**

Кандидаты значений строятся независимо от логики движка: все перечислимые значения из `domain`, равномерная сетка по диапазону признака (200 шагов), все значения порогов и их отклонения на ±0,001, границы литералов в условиях `ge/lt(year, N)` и граница столбцов порогов по году (1999/2000). Перебираются все категории ТС.

**Создать `tests/conflict_check.pl`:**
```prolog
:- encoding(utf8).

:- module(conflict_check, [
    layer1_pairs/1,
    layer1_conflicts/1,
    overlap_witness/3,
    layer2_states/1,
    layer2_violations/1
]).

:- use_module('../src/knowledge_base').
:- use_module('../src/domain').
:- use_module('../src/thresholds').
:- use_module('../src/inference', [conditions_hold/2, fire_verdict_rules/3]).
:- use_module(library(lists)).
:- use_module(library(apply)).

/** <module> Проверка базы знаний на противоречивость (п. 5.2.4 ТЗ)

Слой 1. Для каждой пары правил с общим признаком и разной критичностью
ищется набор ответов, при котором совпадают оба правила. Категория и год
выпуска — контекст (они лишь выбирают пороги и область правила), общим
признаком не считаются. Ожидаемый результат — ни одной такой пары.

Слой 2. Перебираются все 32 сочетания флагов состояния осмотра; в каждом
должно сработать ровно одно правило из V01–V03, V07, V08 и ровно одно
правило действия, если заключение выдано.
*/

context_key(category).
context_key(year).

subject_keys(Conditions, Keys) :-
    findall(Key,
            (   member(Condition, Conditions),
                arg(1, Condition, Key),
                \+ context_key(Key)
            ),
            Raw),
    sort(Raw, Keys).

%! layer1_pairs(-Pairs:list) is det.
layer1_pairs(Pairs) :-
    findall(Id1-Id2,
            (   production_rule(Id1, _, Severity1, Conditions1, _),
                production_rule(Id2, _, Severity2, Conditions2, _),
                Id1 @< Id2,
                Severity1 \== Severity2,
                subject_keys(Conditions1, Keys1),
                subject_keys(Conditions2, Keys2),
                member(Key, Keys1),
                memberchk(Key, Keys2)
            ),
            Raw),
    sort(Raw, Pairs).

%! layer1_conflicts(-Conflicts:list) is det.
layer1_conflicts(Conflicts) :-
    layer1_pairs(Pairs),
    findall(conflict(Id1, Id2, Answers),
            (   member(Id1-Id2, Pairs),
                production_rule(Id1, _, _, Conditions1, _),
                production_rule(Id2, _, _, Conditions2, _),
                overlap_witness(Conditions1, Conditions2, Answers)
            ),
            Conflicts).

%! overlap_witness(+Conditions1, +Conditions2, -Answers) is semidet.
%  Набор ответов, при котором выполнены оба списка условий.
overlap_witness(Conditions1, Conditions2, Answers) :-
    append(Conditions1, Conditions2, All),
    findall(Key, (member(Condition, All), arg(1, Condition, Key)), Keys0),
    sort([category, year|Keys0], Keys),
    candidate_answers(Keys, All, Answers),
    conditions_hold(Conditions1, Answers),
    conditions_hold(Conditions2, Answers),
    !.

candidate_answers([], _, []).
candidate_answers([Key|Keys], All, [Key-Value|Rest]) :-
    candidate_values(Key, All, Values),
    member(Value, Values),
    candidate_answers(Keys, All, Rest).

candidate_values(Key, _, Values) :-
    question(Key, _, choice(Values)),
    !.
candidate_values(year, All, Values) :-
    !,
    question(year, _, int_range(Min, Max)),
    findall(Edge, (member(Condition, All), literal_edge(Condition, year, Edge)), Edges),
    % 1999 и 2000 — граница столбцов порогов before_2000 / from_2000.
    append([Min, Max, 1999, 2000], Edges, Raw),
    sort(Raw, Values).
candidate_values(Key, _, Values) :-
    question(Key, _, num_range(Min, Max)),
    numeric_candidates(Min, Max, Values).

literal_edge(ge(Key, N), Key, N).
literal_edge(ge(Key, N), Key, Edge) :- Edge is N - 1.
literal_edge(lt(Key, N), Key, N).
literal_edge(lt(Key, N), Key, Edge) :- Edge is N - 1.

numeric_candidates(Min, Max, Values) :-
    Steps = 200,
    findall(V,
            (   between(0, Steps, I),
                V is Min + I * (Max - Min) / Steps
            ),
            Grid),
    findall(V,
            (   threshold(_, _, Threshold, _, _),
                member(Delta, [-0.001, 0, 0.001]),
                V is Threshold + Delta,
                V >= Min,
                V =< Max
            ),
            Edges),
    append(Grid, Edges, Raw),
    sort(Raw, Values).

% --- Слой 2 ------------------------------------------------------------------

state_flags([critical, major, minor, complete, contradiction]).

%! layer2_states(-States:list) is det.
layer2_states(States) :-
    state_flags(Flags),
    findall(State, sub_flags(Flags, State), States).

sub_flags([], []).
sub_flags([Flag|Flags], State) :-
    (   sub_flags(Flags, State)
    ;   sub_flags(Flags, Rest),
        State = [Flag|Rest]
    ).

%! layer2_violations(-Violations:list) is det.
layer2_violations(Violations) :-
    layer2_states(States),
    findall(violation(State, Primary, Actions),
            (   member(State, States),
                fire_verdict_rules(State, Verdict, Fired),
                findall(Id, (member(Id-Result, Fired), primary_result(Result)), Primary),
                findall(Id, member(Id-action(_), Fired), Actions),
                \+ acceptable(Verdict, Primary, Actions)
            ),
            Violations).

primary_result(verdict(_)).
primary_result(status(_)).

acceptable(Verdict, [_], Actions) :-
    (   Verdict == none
    ->  Actions == []
    ;   length(Actions, 1)
    ).
```

- [ ] **Step 6: Запустить тесты, убедиться, что проходят**

Run: `./scripts/run_tests.sh`
Expected: 117 тестов `passed` (последняя строка `[117/117] … passed`), код возврата 0. Проверка конфликтов занимает несколько секунд.

Если `layer1_rules_with_a_common_feature_never_match_together` падает, в сообщении будет `conflict(Id1, Id2, Answers)` — это настоящий конфликт полос: исправить условия правил в `knowledge_base.pl`, а не тест.

- [ ] **Step 7: Commit**

```bash
git add tests/project_paths.pl tests/conflict_check.pl tests/test_rules_structure.pl tests/test_conflicts.pl tests/all.pl
git commit -m "test: rule structure checks and conflict verification of both layers"
```

---

### Task 10: Диалог и печать отчёта (`expert_system.pl`)

**Files:**
- Create: `src/expert_system.pl`
- Create: `tests/dialog_support.pl`, `tests/test_dialog.pl`
- Modify: `tests/all.pl`

**Interfaces:**
- Consumes: `domain:question/3`, `question_applies/2`, `required_key/1`, `answer_hint/2`, `key_label/2`, `value_label/3`, `value_text/3`, `valid_value/2`, `group_label/2`, `severity_label/2`, `verdict_label/2`, `action_label/2`; `knowledge_base:rule_group/1`, `verdict_rule/4`; `inference:set_answers/1`, `clear_answers/0`, `inspect_current/1`, `rule_count/1`, `rule_count_by_group/2`, `verdict_rule_count/1`.
- Produces (модуль `expert_system`):
  - `start/0` — точка входа: настраивает UTF-8 и запускает `run_session/0`;
  - `run_session/0` — баннер и цикл осмотров, читает `current_input`;
  - `inspection/0` — один осмотр (для интерактивной среды);
  - `print_report(+Report)` — печать отчёта в `current_output`;
  - `show_rule_count/0` — подсчёт правил по слоям и группам.
- Produces (модуль `dialog_support`, тесты): `dialog_input(+Answers, +Inserts, -Text:string)` — текст, который «набрал бы» пользователь: по строке на каждый запрашиваемый признак в порядке вопросов, перед строкой признака `Key` вставляются все `Key-Line` из `Inserts`, а `Key=Line` заменяет саму строку признака; `run_dialog(+Input:string, -Output:string)` — выполнить `run_session/0` с входом из строки и вернуть вывод; `report_output(+Report, -Output:string)` — текст `print_report/1`.

Поведение диалога:
- порядок вопросов — как в `domain:question/3`; признаки `co`/`ch`/`smoke` спрашиваются только для подходящего типа топлива (уже заданного к этому моменту);
- ввод нормализуется: обрезаются пробелы, регистр не важен, десятичная запятая принимается как точка;
- значение для выбора принимается по русской подписи (`слабо`), по латинскому атому (`weak`) или по алиасу (`д`/`y`, `н`/`n` для да/нет); для категории кириллические `М`/`Н` приравниваются к латинским;
- «неизвестно», «не знаю», `unknown`, `?` — для всех признаков, кроме `category`, `year`, `fuel`; там выводится сообщение «Этот признак обязателен» и запрос повторяется;
- недопустимое значение — сообщение «Недопустимое значение…» и повтор запроса;
- конец ввода (EOF) в любой момент — сообщение «Ввод завершён…», без аварии и без отчёта;
- после отчёта — вопрос «Начать новый осмотр? (да / нет)»; ответы очищаются до и после каждого осмотра.

- [ ] **Step 1: Написать вспомогательный модуль тестов диалога**

**Создать `tests/dialog_support.pl`:**
```prolog
:- encoding(utf8).

:- module(dialog_support, [
    dialog_input/3,
    run_dialog/2,
    report_output/2
]).

:- use_module('../src/domain').
:- use_module('../src/expert_system').
:- use_module(library(lists)).

/** <module> Вспомогательные предикаты для проверки диалога */

%! dialog_input(+Answers, +Inserts, -Text:string) is det.
%
%  Text — ввод пользователя для осмотра с ответами Answers. Inserts —
%  список особых строк:
%    Key-Line   строка Line подаётся перед корректным ответом на вопрос Key
%               (проверка повторного запроса);
%    Key=Line   строка Line подаётся вместо корректного ответа на вопрос Key
%               (проверка разбора ввода).
dialog_input(Answers, Inserts, Text) :-
    memberchk(fuel-Fuel, Answers),
    findall(Line,
            (   question(Key, _, _),
                question_applies(Key, Fuel),
                (   member(Key-Line, Inserts)
                ;   valid_line(Key, Answers, Inserts, Line)
                )
            ),
            Lines),
    atomic_list_concat(Lines, '\n', Atom),
    atom_concat(Atom, '\n', WithNewline),
    atom_string(WithNewline, Text).

valid_line(Key, Answers, Inserts, Line) :-
    (   member(Key=Replacement, Inserts)
    ->  Line = Replacement
    ;   memberchk(Key-Value, Answers),
        value_text(Key, Value, Line)
    ).

%! run_dialog(+Input:string, -Output:string) is det.
run_dialog(Input, Output) :-
    open_string(Input, In),
    current_input(Old),
    with_output_to(string(Output),
        setup_call_cleanup(
            set_input(In),
            run_session,
            ( set_input(Old), close(In) ))).

%! report_output(+Report, -Output:string) is det.
report_output(Report, Output) :-
    with_output_to(string(Output), print_report(Report)).
```

- [ ] **Step 2: Написать падающие тесты диалога**

**Создать `tests/test_dialog.pl`:**
```prolog
:- encoding(utf8).

:- use_module('../src/inference', [current_answer/2]).
:- use_module(fixtures).
:- use_module(dialog_support).

:- begin_tests(dialog).

clean_dialog(Inserts, Text) :-
    clean_answers(Answers),
    dialog_input(Answers, Inserts, Text).

test(first_question_is_printed) :-
    clean_dialog([], Text),
    run_dialog(Text, Output),
    assertion(sub_string(Output, _, _, _, "Категория транспортного средства")).

test(clean_inspection_runs_to_the_end) :-
    clean_dialog([], Body),
    string_concat(Body, "нет\n", Text),
    run_dialog(Text, Output),
    assertion(sub_string(Output, _, _, _, "допущен к эксплуатации")),
    assertion(sub_string(Output, _, _, _, "эксплуатация разрешена")),
    assertion(sub_string(Output, _, _, _, "Работа завершена.")).

test(all_28_questions_are_asked_for_petrol_only_27) :-
    clean_dialog([], Body),
    string_concat(Body, "нет\n", Text),
    run_dialog(Text, Output),
    assertion(sub_string(Output, _, _, _, "Содержание CO")),
    assertion(sub_string(Output, _, _, _, "Содержание CH")),
    assertion(\+ sub_string(Output, _, _, _, "Дымность")).

test(electric_car_is_not_asked_about_exhaust) :-
    clean_answers(Base),
    with_answers([fuel-electric], Base, A1),
    without_answers([co, ch], A1, Answers),
    dialog_input(Answers, [], Body),
    string_concat(Body, "нет\n", Text),
    run_dialog(Text, Output),
    assertion(\+ sub_string(Output, _, _, _, "Содержание CO")),
    assertion(\+ sub_string(Output, _, _, _, "Дымность")),
    assertion(sub_string(Output, _, _, _, "допущен к эксплуатации")).

test(diesel_car_is_asked_about_smoke) :-
    clean_answers(Base),
    with_answers([fuel-diesel, smoke-1.0], Base, A1),
    without_answers([co, ch], A1, Answers),
    dialog_input(Answers, [], Body),
    string_concat(Body, "нет\n", Text),
    run_dialog(Text, Output),
    assertion(sub_string(Output, _, _, _, "Дымность")),
    assertion(\+ sub_string(Output, _, _, _, "Содержание CO")).

test(invalid_choice_is_rejected_and_question_repeated) :-
    clean_dialog([category-"грузовик"], Body),
    string_concat(Body, "нет\n", Text),
    run_dialog(Text, Output),
    assertion(sub_string(Output, _, _, _, "Недопустимое значение")),
    assertion(sub_string(Output, _, _, _, "допущен к эксплуатации")).

test(out_of_range_number_is_rejected_and_question_repeated) :-
    clean_dialog([brake_force-"1.5", brake_force-"минус"], Body),
    string_concat(Body, "нет\n", Text),
    run_dialog(Text, Output),
    findall(x, sub_string(Output, _, _, _, "Недопустимое значение"), Rejections),
    assertion(length(Rejections, 2)),
    assertion(sub_string(Output, _, _, _, "допущен к эксплуатации")).

test(required_answer_cannot_be_unknown) :-
    clean_dialog([year-"неизвестно"], Body),
    string_concat(Body, "нет\n", Text),
    run_dialog(Text, Output),
    assertion(sub_string(Output, _, _, _, "обязателен")),
    assertion(sub_string(Output, _, _, _, "допущен к эксплуатации")).

test(unknown_is_accepted_for_optional_features) :-
    clean_answers(Base),
    with_answers([brake_force-unknown], Base, Answers),
    dialog_input(Answers, [], Body),
    string_concat(Body, "нет\n", Text),
    run_dialog(Text, Output),
    assertion(sub_string(Output, _, _, _, "Не определены признаки")),
    assertion(sub_string(Output, _, _, _, "Удельная тормозная сила")).

test(input_is_normalized) :-
    clean_dialog([category="  М1  ", brake_force="0,8"], Body),
    string_concat(Body, "нет\n", Text),
    run_dialog(Text, Output),
    assertion(\+ sub_string(Output, _, _, _, "Недопустимое значение")),
    assertion(sub_string(Output, _, _, _, "допущен к эксплуатации")).

test(latin_atoms_are_accepted_as_answers) :-
    clean_answers(Base),
    with_answers([parking_brake-weak], Base, Answers),
    dialog_input(Answers, [parking_brake-"weak"], Body),
    string_concat(Body, "нет\n", Text),
    run_dialog(Text, Output),
    assertion(sub_string(Output, _, _, _, "P07")).

test(end_of_input_mid_inspection_is_handled) :-
    run_dialog("м1\n2015\n", Output),
    assertion(sub_string(Output, _, _, _, "Ввод завершён")),
    assertion(\+ sub_string(Output, _, _, _, "Результат осмотра")).

test(empty_input_is_handled) :-
    run_dialog("", Output),
    assertion(sub_string(Output, _, _, _, "Ввод завершён")).

test(bad_next_action_answer_is_repeated) :-
    clean_dialog([], Body),
    string_concat(Body, "может быть\nнет\n", Text),
    run_dialog(Text, Output),
    assertion(sub_string(Output, _, _, _, "Введите «да» или «нет»")).

test(two_inspections_do_not_share_answers) :-
    clean_dialog([], First),
    clean_answers(Base),
    with_answers([wheel_fasteners-missing], Base, Second0),
    dialog_input(Second0, [], Second),
    atomic_list_concat([First, "да\n", Second, "нет\n"], Text),
    run_dialog(Text, Output),
    assertion(sub_string(Output, _, _, _, "Работа завершена.")),
    % В отчёте первого осмотра нет замечаний, в отчёте второго — только P27.
    sub_string(Output, Before, _, After, "Начать новый осмотр"),
    sub_string(Output, 0, Before, _, FirstPart),
    sub_string(Output, _, After, 0, SecondPart),
    !,
    assertion(\+ sub_string(FirstPart, _, _, _, "P27")),
    assertion(sub_string(SecondPart, _, _, _, "P27")),
    assertion(sub_string(SecondPart, _, _, _, "не допущен к эксплуатации")),
    assertion(\+ current_answer(_, _)).

test(report_shows_group_rule_number_severity_and_features) :-
    clean_answers(Base),
    with_answers([steering_play-34], Base, Answers),
    dialog_input(Answers, [], Body),
    string_concat(Body, "нет\n", Text),
    run_dialog(Text, Output),
    assertion(sub_string(Output, _, _, _, "Рулевое управление")),
    assertion(sub_string(Output, _, _, _, "P13")),
    assertion(sub_string(Output, _, _, _, "критическая")),
    assertion(sub_string(Output, _, _, _, "Суммарный люфт рулевого управления, °: 34")),
    assertion(sub_string(Output, _, _, _, "V01")),
    assertion(sub_string(Output, _, _, _, "V04")),
    assertion(sub_string(Output, _, _, _, "эксплуатация запрещена")).

test(reference_notice_is_printed_in_every_report) :-
    clean_dialog([], Body),
    string_concat(Body, "нет\n", Text),
    run_dialog(Text, Output),
    assertion(sub_string(Output, _, _, _, "носит справочный характер и не заменяет технический осмотр")).

:- end_tests(dialog).
```

**Дописать в конец `tests/all.pl`:**
```prolog
:- consult(test_dialog).
```

- [ ] **Step 3: Запустить тесты, убедиться, что падают**

Run: `./scripts/run_tests.sh`
Expected: ошибка загрузки — `source_sink '../src/expert_system' does not exist`.

- [ ] **Step 4: Реализовать `src/expert_system.pl`**

**Создать `src/expert_system.pl`:**
```prolog
:- encoding(utf8).

:- module(expert_system, [
    start/0,
    run_session/0,
    inspection/0,
    print_report/1,
    show_rule_count/0
]).

:- use_module(domain).
:- use_module(knowledge_base, [rule_group/1, verdict_rule/4]).
:- use_module(inference).
:- use_module(library(lists)).
:- use_module(library(apply)).
:- use_module(library(readutil)).

/** <module> Текстовый интерфейс экспертной системы технического осмотра

Диалог задаёт вопросы по признакам из модуля domain, проверяет ввод и
повторяет запрос при ошибке (п. 5.1.1, 5.1.3, 5.2.1 ТЗ), после отчёта
предлагает новый осмотр или выход (п. 5.1.10). Печать отчёта показывает
использованные признаки и номера правил обоих слоёв (п. 5.1.8, 5.8.2) и
оговорку о справочном характере результата (п. 5.8.4).
*/

%! start is det.
%
%  Начальный предикат программы: настраивает UTF-8 и запускает осмотры до
%  команды пользователя завершить работу.
start :-
    configure_streams,
    run_session.

configure_streams :-
    catch(set_stream(user_input, encoding(utf8)), _, true),
    catch(set_stream(user_output, encoding(utf8)), _, true),
    catch(set_stream(user_error, encoding(utf8)), _, true).

%! run_session is det.
%  Баннер и цикл осмотров; читает current_input, пишет в current_output.
run_session :-
    print_banner,
    inspection_loop.

print_banner :-
    nl,
    writeln("Экспертная система технического осмотра автомобилей"),
    writeln("Ответьте на вопросы об автомобиле. Слово «неизвестно» допустимо,"),
    writeln("если показатель не определён; категория, год выпуска и тип топлива обязательны."),
    nl.

inspection_loop :-
    inspection_with_outcome(Outcome),
    (   Outcome == end_of_file
    ->  writeln("Ввод завершён. Работа программы завершена.")
    ;   ask_next_action(Action),
        (   Action == again
        ->  inspection_loop
        ;   writeln("Работа завершена.")
        )
    ).

%! inspection is det.
%  Один осмотр; удобен для вызова из интерактивной среды SWI-Prolog.
inspection :-
    inspection_with_outcome(_).

inspection_with_outcome(Outcome) :-
    clear_answers,
    ask_all_questions(Pairs, Outcome),
    (   Outcome == complete
    ->  set_answers(Pairs),
        inspect_current(Report),
        print_report(Report)
    ;   true
    ),
    clear_answers.

% --- Вопросы -----------------------------------------------------------------

ask_all_questions(Pairs, Outcome) :-
    findall(Key, question(Key, _, _), Keys),
    ask_questions(Keys, [], Reversed, Outcome),
    reverse(Reversed, Pairs).

% Acc — уже полученные пары в обратном порядке; по ним определяется тип топлива.
ask_questions([], Acc, Acc, complete).
ask_questions([Key|Rest], Acc, Pairs, Outcome) :-
    (   asked_for(Key, Acc)
    ->  ask_question(Key, Answer),
        (   Answer = value(Value)
        ->  ask_questions(Rest, [Key-Value|Acc], Pairs, Outcome)
        ;   Pairs = Acc,
            Outcome = end_of_file
        )
    ;   ask_questions(Rest, Acc, Pairs, Outcome)
    ).

asked_for(Key, Acc) :-
    (   memberchk(fuel-Fuel, Acc)
    ->  true
    ;   Fuel = none
    ),
    question_applies(Key, Fuel).

%! ask_question(+Key, -Answer) is det.
%  Answer — value(Value) или end_of_file. Запрос повторяется до допустимого ответа.
ask_question(Key, Answer) :-
    question(Key, Prompt, _),
    answer_hint(Key, Hint),
    format("~w (~w): ", [Prompt, Hint]),
    flush_output,
    read_input_line(Raw),
    (   Raw == end_of_file
    ->  nl,
        writeln("Ввод завершён до окончания осмотра. Осмотр не выполнен."),
        Answer = end_of_file
    ;   parse_response(Key, Raw, Value)
    ->  Answer = value(Value)
    ;   reject_message(Key, Raw),
        ask_question(Key, Answer)
    ).

read_input_line(Raw) :-
    current_input(In),
    read_line_to_string(In, Raw).

reject_message(Key, Raw) :-
    normalized(Raw, Text),
    (   required_key(Key),
        unknown_word(Text)
    ->  writeln("Этот признак обязателен: ответ «неизвестно» недопустим. Введите значение.")
    ;   writeln("Недопустимое значение. Введите один из указанных вариантов или число в допустимых пределах.")
    ).

% --- Разбор ответа -----------------------------------------------------------

parse_response(Key, Raw, unknown) :-
    \+ required_key(Key),
    normalized(Raw, Text),
    unknown_word(Text).
parse_response(Key, Raw, Value) :-
    question(Key, _, Kind),
    normalized(Raw, Text),
    parse_kind(Kind, Key, Text, Value),
    valid_value(Key, Value).

unknown_word(Text) :-
    memberchk(Text, ["неизвестно", "не знаю", "unknown", "?"]).

normalized(Raw, Text) :-
    normalize_space(string(Trimmed), Raw),
    string_lower(Trimmed, Text).

parse_kind(choice(Values), Key, Text, Value) :-
    member(Value, Values),
    option_matches(Key, Value, Text).
parse_kind(int_range(_, _), _, Text, Value) :-
    plain_number(Text, Value),
    integer(Value).
parse_kind(num_range(_, _), _, Text, Value) :-
    plain_number(Text, Value).

option_matches(Key, Value, Text) :-
    (   atom_string(Value, Text)
    ;   value_label(Key, Value, Label),
        string_lower(Label, Text)
    ;   yes_no_alias(Value, Text)
    ;   Key == category,
        latinized(Text, Latin),
        atom_string(Value, Latin)
    ;   Key == category,
        latinized(Text, Latin),
        value_label(Key, Value, Label),
        string_lower(Label, Latin)
    ),
    !.

yes_no_alias(yes, "д").
yes_no_alias(yes, "y").
yes_no_alias(no, "н").
yes_no_alias(no, "n").

% Кириллические «м» и «н» в названии категории (М1, Н2-Н3) приравниваются
% к латинским, чтобы русская раскладка не мешала вводу.
latinized(Text, Latin) :-
    string_codes(Text, Codes),
    maplist(latin_code, Codes, LatinCodes),
    string_codes(Latin, LatinCodes),
    Latin \== Text.

latin_code(0'м, 0'm) :- !.
latin_code(0'н, 0'n) :- !.
latin_code(Code, Code).

% Число без знака с необязательной дробной частью; запятая — как точка.
plain_number(Text, Value) :-
    split_string(Text, ",", "", Parts),
    atomic_list_concat(Parts, '.', Atom),
    atom_codes(Atom, Codes),
    phrase(unsigned_decimal, Codes),
    number_codes(Value, Codes).

unsigned_decimal --> digit_seq, ( ".", digit_seq -> [] ; [] ).

digit_seq --> [Code], { between(0'0, 0'9, Code) }, digit_rest.

digit_rest --> [Code], { between(0'0, 0'9, Code) }, !, digit_rest.
digit_rest --> [].

% --- Новый осмотр или выход --------------------------------------------------

ask_next_action(Action) :-
    nl,
    write("Начать новый осмотр? (да / нет): "),
    flush_output,
    read_input_line(Raw),
    (   Raw == end_of_file
    ->  Action = exit
    ;   normalized(Raw, Text),
        (   memberchk(Text, ["да", "д", "yes", "y", "1"])
        ->  Action = again
        ;   memberchk(Text, ["нет", "н", "no", "n", "0"])
        ->  Action = exit
        ;   writeln("Введите «да» или «нет»."),
            ask_next_action(Action)
        )
    ).

% --- Печать отчёта -----------------------------------------------------------

%! print_report(+Report:dict) is det.
print_report(Report) :-
    nl,
    writeln("Результат осмотра"),
    writeln("-----------------"),
    print_status(Report.status),
    print_verdict(Report.verdict, Report.action),
    (   memberchk(Report.status, [ok, insufficient_data])
    ->  print_findings(Report.findings)
    ;   true
    ),
    print_explanation(Report),
    print_diagnostics(Report.diagnostics),
    nl,
    writeln("Оговорка: результат работы системы носит справочный характер и не заменяет технический осмотр, проводимый аккредитованным оператором.").

print_status(ok) :-
    writeln("Статус: заключение сформировано.").
print_status(insufficient_data) :-
    writeln("Статус: данных недостаточно; заключение о допуске не формируется.").
print_status(contradiction) :-
    writeln("Статус: обнаружены противоречивые данные; заключение не формируется.").
print_status(invalid_input) :-
    writeln("Статус: переданы недопустимые данные.").

print_verdict(none, _) :-
    !.
print_verdict(Verdict, Action) :-
    verdict_label(Verdict, VerdictLabel),
    action_label(Action, ActionLabel),
    format("Заключение: ~w~n", [VerdictLabel]),
    format("Рекомендуемое действие: ~w~n", [ActionLabel]).

print_findings([]) :-
    !,
    nl,
    writeln("Несоответствий по известным признакам не выявлено.").
print_findings(Findings) :-
    nl,
    writeln("Выявленные несоответствия по группам:"),
    forall(rule_group(Group), print_group(Group, Findings)).

print_group(Group, Findings) :-
    include(in_group(Group), Findings, InGroup),
    (   InGroup == []
    ->  true
    ;   group_label(Group, Label),
        format("~n  ~w~n", [Label]),
        forall(member(Finding, InGroup), print_finding(Finding))
    ).

in_group(Group, Finding) :-
    get_dict(group, Finding, Group).

print_finding(Finding) :-
    upcase_atom(Finding.rule, RuleLabel),
    severity_label(Finding.severity, SeverityLabel),
    format("    - ~w, ~w: ~w~n", [RuleLabel, SeverityLabel, Finding.text]),
    forall(member(Key-Value, Finding.evidence), print_evidence(Key, Value)).

print_evidence(Key, Value) :-
    key_label(Key, KeyLabel),
    value_text(Key, Value, ValueText),
    format("        признак: ~w: ~w~n", [KeyLabel, ValueText]).

% Цепочка «ответ → правило слоя 1 → правило слоя 2 → заключение».
print_explanation(Report) :-
    nl,
    writeln("Объяснение вывода:"),
    findall(RuleLabel,
            (   member(Finding, Report.findings),
                upcase_atom(Finding.rule, RuleLabel)
            ),
            FindingRules),
    (   Report.status == contradiction
    ->  writeln("  Правила несоответствий: не применялись из-за противоречия входных данных.")
    ;   FindingRules == []
    ->  writeln("  Правила несоответствий: не сработали.")
    ;   atomic_list_concat(FindingRules, ', ', Joined),
        format("  Правила несоответствий: ~w.~n", [Joined])
    ),
    (   Report.verdict_rules == []
    ->  true
    ;   writeln("  Правила заключения:"),
        forall(member(Id, Report.verdict_rules), print_verdict_rule(Id))
    ).

print_verdict_rule(Id) :-
    verdict_rule(Id, _, _, Text),
    upcase_atom(Id, IdLabel),
    format("    - ~w: ~w~n", [IdLabel, Text]).

print_diagnostics([]) :-
    !.
print_diagnostics(Diagnostics) :-
    nl,
    writeln("Диагностика:"),
    forall(member(Message, Diagnostics), format("  - ~w~n", [Message])).

% --- Подсчёт правил ----------------------------------------------------------

%! show_rule_count is det.
%
%  Печатает число продукционных правил по слоям и группам (п. 5.8.1 ТЗ).
%  Факты признаков, пороги, подписи и служебные предикаты не считаются.
show_rule_count :-
    rule_count(Layer1),
    verdict_rule_count(Layer2),
    Total is Layer1 + Layer2,
    format("Всего продукционных правил: ~d~n", [Total]),
    format("Слой 1. Признаки → несоответствие: ~d~n", [Layer1]),
    forall(rule_group(Group),
           (   rule_count_by_group(Group, Count),
               group_label(Group, Label),
               format("  ~w: ~d~n", [Label, Count])
           )),
    format("Слой 2. Несоответствия → заключение: ~d~n", [Layer2]).
```

- [ ] **Step 5: Запустить тесты, убедиться, что проходят**

Run: `./scripts/run_tests.sh`
Expected: 134 теста `passed` (последняя строка `[134/134] … passed`), код возврата 0.

- [ ] **Step 6: Проверить запуск вручную**

Run: `printf 'м1\n2015\nбензин\n0,8\n5\nудерживает\nгерметичен\n3\nисправны\nисправны\nв норме\nисправны\nна месте\n5\nнорма\nв норме\nцелое\nисправны\nисправны\n0.2\n50\nисправны\nда\nда\nда\nнорма\nнет\nнет\n' | ./scripts/run.sh`
Expected: в конце отчёта строки `Заключение: допущен к эксплуатации`, `Рекомендуемое действие: эксплуатация разрешена`, `Несоответствий по известным признакам не выявлено.` и оговорка; затем `Начать новый осмотр? (да / нет):` и `Работа завершена.`

- [ ] **Step 7: Commit**

```bash
git add src/expert_system.pl tests/dialog_support.pl tests/test_dialog.pl tests/all.pl
git commit -m "feat: interactive dialog, report printing and rule count"
```

---

### Task 11: Контрольные наборы и приёмочные испытания 1–12

Каждое испытание 1–12 таблицы 2 ТЗ получает тест `tNN_…` в `tests/test_acceptance.pl`. Испытание 13 (комплект документации) проверяется в задаче 13.

**Files:**
- Create: `tests/scenarios.pl`, `tests/test_acceptance.pl`
- Modify: `tests/all.pl`

**Interfaces:**
- Consumes: всё, что создано в задачах 1–10 (`fixtures`, `dialog_support`, `conflict_check`, `project_paths`, `inference`, `expert_system:show_rule_count/0`).
- Produces (модуль `scenarios`, используется скриптом таблиц в задаче 12):
  - `scenario(Id, Title:string, Answers:list, expect(Status, Verdict, Action, RuleIds))` — 13 контрольных наборов `s01…s13`;
  - `scenario_report(+Id, -Report)` — отчёт `inspect_answers/2` по набору.

Набор `s01` — исправный; `s02` — только незначительные; `s03` — существенные; `s04` — критические (четыре набора испытания 5); `s05` — единственное критическое (испытание 8); `s06`, `s07` — дизель и электромобиль; `s08`, `s09` — категория и год меняют пороги и критичность; `s10`, `s11`, `s13` — неполные данные; `s12` — противоречие.

- [ ] **Step 1: Создать контрольные наборы**

**Создать `tests/scenarios.pl`:**
```prolog
:- encoding(utf8).

:- module(scenarios, [
    scenario/4,
    scenario_report/2
]).

:- use_module(fixtures).
:- use_module('../src/inference', [inspect_answers/2]).

/** <module> Контрольные наборы данных (сценарии осмотра)

scenario(Id, Title, Answers, expect(Status, Verdict, Action, RuleIds)) —
набор ответов и ожидаемый результат. Наборы S01–S04 — четыре набора
испытания 5 (исправный, незначительные, существенные, критические).
*/

scenario(s01, "Исправный легковой автомобиль M1",
         Answers, expect(ok, admitted, allowed, [])) :-
    build([], [], Answers).
scenario(s02, "Только незначительные несоответствия (малый запас тормозной силы и протектора, сколы стекла, нет аптечки)",
         Answers, expect(ok, admitted, allowed, [p02, p24, p29, p43])) :-
    build([brake_force-0.60, tread_depth-2.0, windshield-chips, first_aid_kit-no], [], Answers).
scenario(s03, "Существенные несоответствия без критических (малая утечка привода, регулировка фар, изношенные щётки, CO выше предела)",
         Answers, expect(ok, admitted_with_remarks, fix_before_reinspection, [p10, p18, p31, p34])) :-
    build([brake_leak-minor, headlight_aim-misaligned, wipers-worn, co-0.6], [], Answers).
scenario(s04, "Критические несоответствия (тормозная сила ниже нормы, люфт руля 34°, нет крепления колёс)",
         Answers, expect(ok, not_admitted, prohibited, [p01, p13, p27])) :-
    build([brake_force-0.4, steering_play-34, wheel_fasteners-missing], [], Answers).
scenario(s05, "Единственное критическое несоответствие: нет крепёжных элементов колёс, остальное в норме",
         Answers, expect(ok, not_admitted, prohibited, [p27])) :-
    build([wheel_fasteners-missing], [], Answers).
scenario(s06, "Исправный дизельный автомобиль (вместо CO и CH — дымность)",
         Answers, expect(ok, admitted, allowed, [])) :-
    build([fuel-diesel, smoke-1.0], [co, ch], Answers).
scenario(s07, "Исправный электромобиль (показатели выхлопа не спрашиваются)",
         Answers, expect(ok, admitted, allowed, [])) :-
    build([fuel-electric], [co, ch], Answers).
scenario(s08, "Грузовик N2–N3, 2005 г.: стояночная слабо, люфт 26°, нет световозвращателей",
         Answers, expect(ok, not_admitted, prohibited, [p08, p12, p22])) :-
    build([category-n2_n3, year-2005, parking_brake-weak, steering_play-26, reflectors-missing], [], Answers).
scenario(s09, "Автомобиль 1985 г. без ремней безопасности (для года до 1991 — незначительное)",
         Answers, expect(ok, admitted, allowed, [p41])) :-
    build([year-1985, seat_belts-missing], [], Answers).
scenario(s10, "Неполные данные: удельная тормозная сила неизвестна, критических нет",
         Answers, expect(insufficient_data, none, none, [])) :-
    build([brake_force-unknown], [], Answers).
scenario(s11, "Неполные данные при критическом несоответствии: сила неизвестна, утечка привода значительная",
         Answers, expect(ok, not_admitted, prohibited, [p09])) :-
    build([brake_force-unknown, brake_leak-major], [], Answers).
scenario(s12, "Противоречие входа: дизель и указан CO",
         Answers, expect(contradiction, none, none, [])) :-
    build([fuel-diesel, co-0.3], [], Answers).
scenario(s13, "Минимальный набор: указаны только категория, год и тип топлива",
         [category-m1, year-2015, fuel-petrol],
         expect(insufficient_data, none, none, [])).

build(Overrides, Dropped, Answers) :-
    clean_answers(Base),
    with_answers(Overrides, Base, A1),
    without_answers(Dropped, A1, Answers).

%! scenario_report(+Id, -Report) is det.
scenario_report(Id, Report) :-
    scenario(Id, _, Answers, _),
    inspect_answers(Answers, Report).
```

- [ ] **Step 2: Написать приёмочные тесты**

Испытание 10 запускает основную команду `swipl -q -s src/expert_system.pl -g start -t halt` в отдельном процессе и читает русский вывод в UTF-8.

**Создать `tests/test_acceptance.pl`:**
```prolog
:- encoding(utf8).

:- use_module('../src/domain').
:- use_module('../src/knowledge_base', [rule_group/1]).
:- use_module('../src/thresholds', [threshold/5]).
:- use_module('../src/inference').
:- use_module('../src/expert_system', [show_rule_count/0]).
:- use_module(fixtures).
:- use_module(scenarios).
:- use_module(dialog_support).
:- use_module(conflict_check).
:- use_module(project_paths).
:- use_module(library(process)).
:- use_module(library(readutil)).

% Приёмочные испытания таблицы 2 ТЗ. Имя теста tNN соответствует номеру
% испытания; проверка документации (испытание 13) — в test_docs.pl.
:- begin_tests(acceptance).

scenario_output(Id, Output) :-
    scenario_report(Id, Report),
    report_output(Report, Output).

% Все сценарии дают заранее ожидаемый результат.
test(scenarios_match_their_expectations) :-
    forall(scenario(Id, _, _, expect(Status, Verdict, Action, Rules)),
           (   scenario_report(Id, Report),
               get_dict(status, Report, ActualStatus),
               get_dict(verdict, Report, ActualVerdict),
               get_dict(action, Report, ActualAction),
               report_ids(Report, ActualRules),
               assertion(ActualStatus == Status),
               assertion(ActualVerdict == Verdict),
               assertion(ActualAction == Action),
               assertion(ActualRules == Rules)
           )).

% 1. Загрузка файла и первый вопрос (п. 5.1.1, 5.5.2).
test(t01_first_question_is_printed) :-
    run_dialog("", Output),
    assertion(sub_string(Output, _, _, _, "Категория транспортного средства")).

% 2. Не менее пятнадцати признаков принимаются и используются при выводе (п. 5.1.2).
test(t02_at_least_fifteen_features_are_accepted_and_used) :-
    clean_answers(Answers),
    length(Answers, Count),
    assertion(Count >= 15),
    inspect_answers(Answers, Report),
    get_dict(status, Report, Status),
    get_dict(unknown, Report, Unknown),
    assertion(Status == ok),
    assertion(Unknown == []),
    % Категория, год и тип топлива выбирают пороги и набор вопросов; остальные
    % признаки должны хотя бы при одном значении вызывать срабатывание правила.
    forall((   member(Key-_, Answers),
               \+ memberchk(Key, [category, year, fuel])
           ),
           assertion(feature_changes_result(Key))).

feature_changes_result(Key) :-
    question(Key, _, Kind),
    kind_extremes(Kind, Values),
    member(Value, Values),
    rules_for([Key-Value], Ids),
    Ids \== [],
    !.

kind_extremes(choice(Values), Values).
kind_extremes(num_range(Min, Max), [Min, Max]).

% 3. Недопустимые значения отклоняются, запрос повторяется (п. 5.1.3, 5.2.1).
test(t03_invalid_values_are_rejected_and_inspection_continues) :-
    clean_answers(Answers),
    dialog_input(Answers,
                 [category-"грузовик", brake_force-"7", steering_play-"-5"],
                 Body),
    string_concat(Body, "нет\n", Text),
    run_dialog(Text, Output),
    findall(x, sub_string(Output, _, _, _, "Недопустимое значение"), Rejections),
    assertion(length(Rejections, 3)),
    assertion(sub_string(Output, _, _, _, "Заключение: допущен к эксплуатации")).

% 4. Не менее 50 пронумерованных правил; факты в подсчёт не входят (п. 5.1.5, 5.8.1).
test(t04_rule_count_is_at_least_fifty_and_excludes_facts) :-
    rule_count(Layer1),
    assertion(Layer1 >= 50),
    findall(x, threshold(_, _, _, _, _), Thresholds),
    length(Thresholds, ThresholdCount),
    assertion(ThresholdCount > 0),
    assertion(Layer1 =\= ThresholdCount),
    with_output_to(string(Output), show_rule_count),
    assertion(sub_string(Output, _, _, _, "Всего продукционных правил: 60")).

% 5. Четыре набора: исправный, незначительные, существенные, критические (п. 5.1.6, 5.1.7, 5.1.11, 5.2.6).
test(t05_four_sets_cover_all_verdicts_severities_and_classes) :-
    Sets = [s01-admitted, s02-admitted, s03-admitted_with_remarks, s04-not_admitted],
    forall(member(Id-Verdict, Sets),
           (   scenario_report(Id, Report),
               get_dict(status, Report, Status),
               get_dict(verdict, Report, ActualVerdict),
               get_dict(action, Report, Action),
               get_dict(findings, Report, Findings),
               assertion(Status == ok),
               assertion(ActualVerdict == Verdict),
               assertion(memberchk(Action, [allowed, fix_before_reinspection, prohibited])),
               forall(member(Finding, Findings),
                      (   get_dict(group, Finding, Group),
                          get_dict(severity, Finding, Severity),
                          assertion(rule_group(Group)),
                          assertion(memberchk(Severity, [critical, major, minor]))
                      ))
           )),
    findall(Severity,
            (   member(Id-_, Sets),
                scenario_report(Id, Report),
                get_dict(findings, Report, Findings),
                member(Finding, Findings),
                get_dict(severity, Finding, Severity)
            ),
            Severities0),
    sort(Severities0, Severities),
    assertion(Severities == [critical, major, minor]),
    findall(V, member(_-V, Sets), Verdicts0),
    sort(Verdicts0, Verdicts),
    assertion(length(Verdicts, 3)).

% 6. Объяснение содержит признаки и номера правил (п. 5.1.8, 5.8.2).
test(t06_explanation_lists_features_and_rule_numbers) :-
    scenario_output(s04, Output),
    forall(member(Part,
                  ["P01", "P13", "P27",
                   "Удельная тормозная сила рабочей тормозной системы: 0.4",
                   "Суммарный люфт рулевого управления, °: 34",
                   "Крепление колёс: нет крепёжных элементов",
                   "Правила несоответствий: P01, P13, P27",
                   "V01", "V04"]),
           assertion(sub_string(Output, _, _, _, Part))).

% 7. Неполные и противоречивые данные: диагностика без аварии (п. 5.1.9, 5.2.2).
test(t07_incomplete_and_contradictory_data_are_diagnosed) :-
    forall(member(Id, [s10, s12, s13]),
           (   scenario_output(Id, Output),
               assertion(sub_string(Output, _, _, _, "Диагностика:")),
               assertion(\+ sub_string(Output, _, _, _, "Заключение:"))
           )),
    scenario_output(s12, Contradiction),
    assertion(sub_string(Contradiction, _, _, _, "противоречивые данные")),
    assertion(sub_string(Contradiction, _, _, _, "не применялись")),
    scenario_output(s10, Incomplete),
    assertion(sub_string(Incomplete, _, _, _, "Удельная тормозная сила рабочей тормозной системы")).

% 8. Единственное критическое несоответствие (п. 5.2.5).
test(t08_single_critical_finding_gives_not_admitted) :-
    scenario_report(s05, Report),
    report_ids(Report, Ids),
    assertion(Ids == [p27]),
    scenario_output(s05, Output),
    assertion(sub_string(Output, _, _, _, "Заключение: не допущен к эксплуатации")),
    assertion(sub_string(Output, _, _, _, "P27, критическая")).

% 9. Два осмотра подряд: результат второго определяется только его данными
%    (п. 5.1.4, 5.1.10, 5.2.3).
test(t09_second_inspection_does_not_see_the_first) :-
    scenario(s03, _, First, _),
    scenario(s01, _, Second, _),
    dialog_input(First, [], FirstText),
    dialog_input(Second, [], SecondText),
    atomic_list_concat([FirstText, "да\n", SecondText, "нет\n"], Text),
    run_dialog(Text, Output),
    sub_string(Output, Before, _, After, "Начать новый осмотр"),
    !,
    sub_string(Output, 0, Before, _, FirstPart),
    sub_string(Output, _, After, 0, SecondPart),
    assertion(sub_string(FirstPart, _, _, _, "Заключение: допущен с замечаниями")),
    assertion(sub_string(FirstPart, _, _, _, "P10")),
    assertion(sub_string(SecondPart, _, _, _, "Заключение: допущен к эксплуатации")),
    assertion(sub_string(SecondPart, _, _, _, "Несоответствий по известным признакам не выявлено")),
    assertion(\+ sub_string(SecondPart, _, _, _, "P10")),
    assertion(\+ current_answer(_, _)).

% 10. UTF-8 и текстовый режим (п. 5.5.1–5.5.4): исходники в UTF-8, а
%     основная команда запуска в отдельном процессе выводит русский текст.
test(t10_sources_are_utf8_and_the_start_command_works) :-
    forall(member(File, ['src/domain.pl', 'src/thresholds.pl', 'src/consistency.pl',
                         'src/knowledge_base.pl', 'src/inference.pl',
                         'src/expert_system.pl']),
           (   project_file(File, Path),
               read_file_to_string(Path, Source, [encoding(utf8)]),
               assertion(sub_string(Source, 0, _, _, ":- encoding(utf8).")),
               assertion(\+ sub_string(Source, _, _, _, "�")),
               string_codes(Source, Codes),
               assertion((member(Code, Codes), Code >= 0x410, Code =< 0x44F))
           )),
    project_file('src/expert_system.pl', Main),
    clean_answers(Answers),
    dialog_input(Answers, [], Body),
    string_concat(Body, "нет\n", Input),
    process_create(path(swipl), ['-q', '-s', Main, '-g', start, '-t', halt],
                   [stdin(pipe(In)), stdout(pipe(Out)), stderr(null), process(Pid)]),
    set_stream(In, encoding(utf8)),
    write(In, Input),
    close(In),
    set_stream(Out, encoding(utf8)),
    read_string(Out, _, Output),
    close(Out),
    process_wait(Pid, ExitStatus),
    assertion(ExitStatus == exit(0)),
    assertion(sub_string(Output, _, _, _, "Заключение: допущен к эксплуатации")).

% 11. Пороги вынесены отдельно с источниками; в заключении есть оговорка (п. 5.8.3, 5.8.4).
test(t11_thresholds_have_sources_and_reports_carry_the_notice) :-
    forall(threshold(_, _, _, _, Source), assertion(Source \== "")),
    project_file('src/thresholds.pl', Path),
    read_file_to_string(Path, Text, [encoding(utf8)]),
    assertion(sub_string(Text, _, _, _, "ТР ТС 018/2011")),
    assertion(sub_string(Text, _, _, _, "ГОСТ 33997-2016")),
    forall(member(Id, [s01, s04, s10, s12]),
           (   scenario_output(Id, Output),
               assertion(sub_string(Output, _, _, _, "носит справочный характер и не заменяет технический осмотр"))
           )),
    inspect_answers([brake_force-9], Invalid),
    report_output(Invalid, InvalidOutput),
    assertion(sub_string(InvalidOutput, _, _, _, "носит справочный характер и не заменяет технический осмотр")).

% 12. Проверка базы знаний на противоречивость (п. 5.2.4).
test(t12_no_rules_give_mutually_exclusive_outcomes) :-
    layer1_conflicts(Conflicts),
    assertion(Conflicts == []),
    layer2_violations(Violations),
    assertion(Violations == []).

:- end_tests(acceptance).
```

**Дописать в конец `tests/all.pl`:**
```prolog
:- consult(test_acceptance).
```

- [ ] **Step 3: Запустить тесты**

Run: `./scripts/run_tests.sh`
Expected: 147 тестов `passed` (последняя строка `[147/147] … passed`), код возврата 0.

Наборы `scenarios.pl` не менялись после разработки правил: если ожидаемый результат набора не совпадает с фактическим, сначала проверьте, что изменилось в правилах или порогах, и только потом правьте ожидание.

- [ ] **Step 4: Commit**

```bash
git add tests/scenarios.pl tests/test_acceptance.pl tests/all.pl
git commit -m "test: control scenarios and acceptance tests 1-12 of the terms of reference"
```

---

### Task 12: Таблицы для документации, контрольные примеры и модель классификации

Таблицы признаков, порогов, правил, контрольных примеров и проверки конфликтов печатаются самой системой и вставляются в документы: числа в документах не переписываются вручную и не расходятся с кодом.

**Files:**
- Create: `tests/doc_tables.pl`, `scripts/doc_tables.sh`
- Create: `docs/control_examples.md`, `docs/classification_model.md`

**Interfaces:**
- Consumes: `scenarios:scenario/4`, `scenarios:scenario_report/2`, `conflict_check:*`, `fixtures:clean_answers/1`, `fixtures:report_ids/2`, `knowledge_base`, `thresholds`, `domain`, `inference`.
- Produces: `scripts/doc_tables.sh <имя>` печатает таблицу Markdown в stdout. Имена: `features`, `thresholds`, `rules`, `verdict_rules`, `counts`, `clean`, `changes`, `control`, `conflicts`. Неизвестное имя — сообщение в stderr и код возврата 1.

- [ ] **Step 1: Создать генератор таблиц**

**Создать `tests/doc_tables.pl`:**
```prolog
:- encoding(utf8).

:- module(doc_tables, [main/0, print_table/1]).

:- use_module('../src/domain').
:- use_module('../src/thresholds').
:- use_module('../src/knowledge_base').
:- use_module('../src/inference').
:- use_module(scenarios).
:- use_module(conflict_check).
:- use_module(fixtures, [report_ids/2, clean_answers/1]).
:- use_module(library(lists)).
:- use_module(library(apply)).

/** <module> Таблицы для документации, построенные из самой системы

Документы не переписываются вручную из кода: таблицы признаков, порогов,
правил, контрольных примеров и проверки конфликтов печатаются отсюда в
формате Markdown. Запуск: scripts/doc_tables.sh <имя таблицы>.
Имена: features, thresholds, rules, verdict_rules, counts, clean, changes,
control, conflicts.
*/

%! main is det.
%  Точка входа скрипта: имя таблицы — последний аргумент командной строки.
main :-
    current_prolog_flag(argv, Argv),
    last(Argv, NameText),
    atom_string(Name, NameText),
    (   print_table(Name)
    ->  true
    ;   format(user_error, "Неизвестная таблица: ~w~n", [Name]),
        halt(1)
    ).

%! print_table(+Name:atom) is semidet.
print_table(features)      :- features_table.
print_table(thresholds)    :- thresholds_table.
print_table(rules)         :- rules_table.
print_table(verdict_rules) :- verdict_rules_table.
print_table(counts)        :- counts_table.
print_table(clean)         :- clean_table.
print_table(changes)       :- changes_table.
print_table(control)       :- control_table.
print_table(conflicts)     :- conflicts_table.

% --- Признаки ----------------------------------------------------------------

features_table :-
    writeln("| № | Признак | Ключ | Допустимые ответы | Когда спрашивается |"),
    writeln("|---:|---|---|---|---|"),
    findall(Key, question(Key, _, _), Keys),
    forall(nth1(N, Keys, Key),
           (   question(Key, Prompt, _),
               answer_hint(Key, Hint),
               asked_text(Key, When),
               format("| ~d | ~w | `~w` | ~w | ~w |~n", [N, Prompt, Key, Hint, When])
           )).

asked_text(Key, When) :-
    (   fuel_specific(Key, Fuels)
    ->  maplist(fuel_text, Fuels, Texts),
        atomic_list_concat(Texts, ', ', Joined),
        format(string(When), "только для типа топлива: ~w", [Joined])
    ;   When = "всегда"
    ).

fuel_text(Fuel, Text) :-
    value_text(fuel, Fuel, Text).

% --- Пороги ------------------------------------------------------------------

thresholds_table :-
    writeln("| Порог | Столбец | Значение | Единица | Источник |"),
    writeln("|---|---|---:|---|---|"),
    forall(threshold(Name, Column, Value, Unit, Source),
           format("| `~w` | `~w` | ~w | ~w | ~w |~n", [Name, Column, Value, Unit, Source])).

% --- Правила -----------------------------------------------------------------

rules_table :-
    writeln("| Правило | Группа | Критичность | Условия | Несоответствие |"),
    writeln("|---|---|---|---|---|"),
    forall(production_rule(Id, Group, Severity, Conditions, Text),
           (   upcase_atom(Id, IdLabel),
               group_label(Group, GroupLabel),
               severity_label(Severity, SeverityLabel),
               maplist(condition_text, Conditions, Parts),
               atomic_list_concat(Parts, '; ', Joined),
               format("| ~w | ~w | ~w | ~w | ~w |~n",
                      [IdLabel, GroupLabel, SeverityLabel, Joined, Text])
           )).

verdict_rules_table :-
    writeln("| Правило | Посылки | Результат | Смысл |"),
    writeln("|---|---|---|---|"),
    forall(verdict_rule(Id, Premises, Result, Text),
           (   upcase_atom(Id, IdLabel),
               format("| ~w | `~q` | `~q` | ~w |~n", [IdLabel, Premises, Result, Text])
           )).

condition_text(eq(Key, Value), Text) :-
    value_text(Key, Value, ValueText),
    format(string(Text), "`~w` = ~w", [Key, ValueText]).
condition_text(in(Key, Values), Text) :-
    maplist(value_text(Key), Values, Texts),
    atomic_list_concat(Texts, ', ', Joined),
    format(string(Text), "`~w` ∈ {~w}", [Key, Joined]).
condition_text(ge(Key, N), Text) :-
    format(string(Text), "`~w` ≥ ~w", [Key, N]).
condition_text(lt(Key, N), Text) :-
    format(string(Text), "`~w` < ~w", [Key, N]).
condition_text(lt_t(Key, Name), Text) :-
    format(string(Text), "`~w` < `~w`", [Key, Name]).
condition_text(le_t(Key, Name), Text) :-
    format(string(Text), "`~w` ≤ `~w`", [Key, Name]).
condition_text(gt_t(Key, Name), Text) :-
    format(string(Text), "`~w` > `~w`", [Key, Name]).
condition_text(ge_t(Key, Name), Text) :-
    format(string(Text), "`~w` ≥ `~w`", [Key, Name]).

counts_table :-
    rule_count(Layer1),
    verdict_rule_count(Layer2),
    Total is Layer1 + Layer2,
    writeln("| Слой | Группа | Правил |"),
    writeln("|---|---|---:|"),
    forall(rule_group(Group),
           (   rule_count_by_group(Group, Count),
               group_label(Group, Label),
               format("| 1. Признаки → несоответствие | ~w | ~d |~n", [Label, Count])
           )),
    format("| 1. Признаки → несоответствие | **Итого** | **~d** |~n", [Layer1]),
    format("| 2. Несоответствия → заключение | V01–V08 | **~d** |~n", [Layer2]),
    format("| | **Всего** | **~d** |~n", [Total]).

% --- Контрольные примеры -----------------------------------------------------

% Исправный набор — основа сценариев; остальные сценарии описаны отличиями от него.
clean_table :-
    writeln("| Признак | Ключ | Ответ |"),
    writeln("|---|---|---|"),
    clean_answers(Answers),
    forall(member(Key-Value, Answers),
           (   key_label(Key, Label),
               value_text(Key, Value, ValueText),
               format("| ~w | `~w` | ~w |~n", [Label, Key, ValueText])
           )).

changes_table :-
    writeln("| № | Ответы, отличные от исправного набора |"),
    writeln("|---:|---|"),
    clean_answers(Clean),
    findall(Id, scenario(Id, _, _, _), Ids),
    forall(nth1(N, Ids, Id),
           (   scenario(Id, _, Answers, _),
               changes_text(Clean, Answers, Text),
               format("| ~d | ~w |~n", [N, Text])
           )).

changes_text(Clean, Answers, Text) :-
    findall(Key, (member(Key-_, Clean), \+ memberchk(Key-_, Answers)), Dropped),
    findall(Key-Value,
            (   member(Key-Value, Answers),
                \+ memberchk(Key-Value, Clean)
            ),
            Changed),
    (   Answers == Clean
    ->  Text = "нет отличий"
    ;   length(Dropped, DroppedCount),
        DroppedCount > 5
    ->  pairs_text(Answers, Listed),
        format(string(Text), "заданы только: ~w", [Listed])
    ;   pairs_text(Changed, ChangedText),
        (   Dropped == []
        ->  Text = ChangedText
        ;   atomic_list_concat(Dropped, ', ', DroppedText),
            format(string(Text), "~w; не задаются: ~w", [ChangedText, DroppedText])
        )
    ).

pairs_text(Pairs, Text) :-
    maplist(pair_text, Pairs, Parts),
    atomic_list_concat(Parts, '; ', Text).

pair_text(Key-Value, Text) :-
    value_text(Key, Value, ValueText),
    format(string(Text), "`~w` = ~w", [Key, ValueText]).

control_table :-
    writeln("| № | Сценарий | Ожидаемый результат | Фактический результат | Проверка разработчиков | Приёмочный результат |"),
    writeln("|---:|---|---|---|---|---|"),
    findall(Id, scenario(Id, _, _, _), Ids),
    forall(nth1(N, Ids, Id),
           (   scenario(Id, Title, _, expect(Status, Verdict, Action, Rules)),
               scenario_report(Id, Report),
               report_ids(Report, ActualRules),
               outcome_text(Status, Verdict, Action, Rules, Expected),
               outcome_text(Report.status, Report.verdict, Report.action, ActualRules, Actual),
               (   Expected == Actual
               ->  Check = "Пройдено"
               ;   Check = "НЕ ПРОЙДЕНО"
               ),
               format("| ~d | ~w | ~w | ~w | ~w | |~n", [N, Title, Expected, Actual, Check])
           )).

outcome_text(Status, Verdict, Action, Rules, Text) :-
    (   Verdict \== none
    ->  verdict_label(Verdict, VerdictLabel),
        action_label(Action, ActionLabel),
        rules_text(Rules, RulesText),
        format(string(Text), "~w; ~w; ~w", [VerdictLabel, ActionLabel, RulesText])
    ;   status_text(Status, StatusText),
        format(string(Text), "~w", [StatusText])
    ).

rules_text([], "несоответствий нет").
rules_text(Rules, Text) :-
    Rules = [_|_],
    maplist(upcase_atom, Rules, Labels),
    atomic_list_concat(Labels, ', ', Joined),
    format(string(Text), "правила ~w", [Joined]).

status_text(insufficient_data, "диагностика: данных недостаточно, заключение не формируется").
status_text(contradiction, "диагностика: противоречие входных данных, заключение не формируется").
status_text(invalid_input, "диагностика: недопустимые данные").

% --- Проверка конфликтов правил (испытание 12) -------------------------------

conflicts_table :-
    layer1_pairs(Pairs),
    length(Pairs, PairCount),
    layer1_conflicts(Conflicts),
    length(Conflicts, ConflictCount),
    layer2_states(States),
    length(States, StateCount),
    layer2_violations(Violations),
    length(Violations, ViolationCount),
    writeln("| Проверка | Что перебиралось | Найдено нарушений |"),
    writeln("|---|---|---:|"),
    format("| Слой 1 | ~d пар правил с общим признаком и разной критичностью; для каждой пары — сетка значений признака, пороги и их окрестности, все четыре категории ТС, границы года (1999/2000, 1990/1991) | ~d |~n",
           [PairCount, ConflictCount]),
    format("| Слой 2 | все ~d сочетания флагов «есть критическое / есть существенное / есть незначительное / данные полны / есть противоречие»; в каждом ровно одно правило из V01–V03, V07, V08 и не более одного правила действия | ~d |~n",
           [StateCount, ViolationCount]).
```

**Создать `scripts/doc_tables.sh`:**
```sh
#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec swipl -q -s "$SCRIPT_DIR/../tests/doc_tables.pl" -g main -t halt -- "$1"
```

- [ ] **Step 2: Проверить генератор**

```sh
chmod +x scripts/doc_tables.sh
for name in features thresholds rules verdict_rules counts clean changes control conflicts; do
  echo "== $name: $(./scripts/doc_tables.sh $name | wc -l) строк"
done
./scripts/doc_tables.sh unknown_name; echo "exit=$?"
./scripts/doc_tables.sh control | grep -c "НЕ ПРОЙДЕНО" || true
```

Expected: `features` — 30 строк (заголовок, разделитель, 28 признаков); `thresholds` — 43; `rules` — 54; `verdict_rules` — 10; `counts` — 12; `clean` — 29; `changes` — 15; `control` — 15; `conflicts` — 4; для `unknown_name` — сообщение «Неизвестная таблица» и `exit=1`; последняя команда печатает `0`.

- [ ] **Step 3: Создать `docs/control_examples.md` (вводная часть и проверки диалога)**

**Создать `docs/control_examples.md`:**
```markdown
# Контрольные примеры

Документ фиксирует ожидаемое поведение системы и результат предварительной
проверки разработчиками (п. 6.2 ТЗ). Графу «Приёмочный результат» тестировщик
заполняет независимо; разработчики её не заполняют.

Разделы 2–6 построены автоматически командой `./scripts/doc_tables.sh <имя>`
из тех же наборов данных и правил, которые проверяют автоматические тесты
(`tests/scenarios.pl`, `tests/conflict_check.pl`). Столбец «Фактический
результат» — это вывод программы на момент сборки документа. Если он не
совпал с ожидаемым, вместо «Пройдено» в «Проверке разработчиков»
печатается отметка об ошибке.

Ответы вводятся в диалоге по-русски, как показано в подсказке вопроса
(«удерживает», «слабо», «да», «нет», число с точкой или запятой).

## 1. Проверки диалога

| № | Действие | Ожидаемый результат | Проверка разработчиков | Приёмочный результат |
|---:|---|---|---|---|
| Д1 | На вопрос о категории ввести «грузовик», затем «м1» | Сообщение «Недопустимое значение…», вопрос повторён, осмотр продолжен | Пройдено (`test_dialog`, `t03`) | |
| Д2 | Удельная тормозная сила: ввести «1.5» (выше диапазона), затем «0,8» | Первое значение отклонено, второе принято, десятичная запятая допустима | Пройдено (`test_dialog`, `t03`) | |
| Д3 | Год выпуска: ввести «неизвестно» | Сообщение «Этот признак обязателен…», вопрос повторён (то же для категории и типа топлива) | Пройдено (`test_dialog`) | |
| Д4 | Тип топлива «электро» | Вопросы о CO, CH и дымности не задаются, всего 25 вопросов | Пройдено (`test_dialog`) | |
| Д5 | Тип топлива «дизель» | Спрашивается дымность, CO и CH не спрашиваются, всего 26 вопросов | Пройдено (`test_dialog`) | |
| Д6 | Прервать ввод (Ctrl-D) посреди осмотра | Сообщение «Ввод завершён…», отчёта нет, аварии нет | Пройдено (`test_dialog`) | |
| Д7 | После отчёта ввести «может быть» | «Введите «да» или «нет»», вопрос повторён | Пройдено (`test_dialog`) | |
| Д8 | Два осмотра подряд: набор 3, затем набор 1 | В отчёте второго осмотра нет правил первого (P10) и нет замечаний | Пройдено (`t09`) | |
| Д9 | Запуск `swipl -q -s src/expert_system.pl -g start -t halt`, ввод исправного набора | Русский текст читается, осмотр завершается кодом 0 | Пройдено (`t10`) | |
```

- [ ] **Step 4: Добавить в документ таблицы, построенные системой**

```sh
{
  printf '\n## 2. Контрольные наборы данных\n\n'
  printf 'Наборы 1–4 — испытание 5 (исправный, незначительные, существенные, критические); набор 5 — испытание 8; наборы 10, 11, 13 — неполные данные; набор 12 — противоречие (испытание 7).\n\n'
  ./scripts/doc_tables.sh control
  printf '\n## 3. Исправный набор ответов (основа сценариев)\n\n'
  ./scripts/doc_tables.sh clean
  printf '\n## 4. Отличия сценариев от исправного набора\n\n'
  ./scripts/doc_tables.sh changes
  printf '\n## 5. Проверка базы знаний на конфликты (испытание 12)\n\n'
  ./scripts/doc_tables.sh conflicts
  printf '\n## 6. Подсчёт правил (испытание 4)\n\n'
  ./scripts/doc_tables.sh counts
} >> docs/control_examples.md
grep -c "НЕ ПРОЙДЕНО" docs/control_examples.md || true
```

Expected: последняя команда печатает `0`. В `docs/control_examples.md` шесть разделов; в разделе 5 в столбце «Найдено нарушений» стоят нули.

- [ ] **Step 5: Создать `docs/classification_model.md`**

**Создать `docs/classification_model.md`:**
```markdown
# Модель классификации

## Как система получает результат

1. **Проверка допустимости** (`domain:validate_answers/2` и диалог). Значение
   должно принадлежать перечню или диапазону признака; ошибочный ввод
   отклоняется, запрос повторяется (п. 5.1.3, 5.2.1 ТЗ). «Неизвестно»
   допустимо для всех признаков, кроме категории, года и типа топлива.
2. **Противоречия входа** (`consistency:consistency_issues/2`). Пять
   условий, например «дизель и указан CO» или «шарниры разрушены при люфте
   меньше 5°». При противоречии правила слоя 1 не применяются, заключение не
   формируется (правило V08).
3. **Слой 1 — несоответствия.** Каждое из 52 правил P01–P52 сравнивает ответы
   с порогами и выдаёт несоответствие с группой, степенью критичности и
   текстом. Пороги выбираются по категории ТС, для CO и CH — по году выпуска.
4. **Состояние осмотра.** Из найденных несоответствий и полноты данных
   строится набор флагов: `critical`, `major`, `minor`, `complete`,
   `contradiction`.
5. **Слой 2 — заключение.** Восемь правил V01–V08 по состоянию выдают
   заключение, рекомендуемое действие или статус диагностики.
6. **Отчёт.** Группы несоответствий, правила и использованные признаки,
   диагностика и оговорка о справочном характере результата
   (п. 5.1.8, 5.8.2, 5.8.4 ТЗ).

## Классы результата (п. 5.1.11 ТЗ)

| Направление | Значения |
|---|---|
| Итоговое заключение | допущен к эксплуатации; допущен с замечаниями, требуется повторный осмотр; не допущен к эксплуатации |
| Группа несоответствий | тормозная система; рулевое управление; внешние световые приборы и световозвращатели; шины и колёса; приборы обзора и стеклоочистители; экологические показатели; прочие элементы конструкции и обязательная комплектация |
| Степень критичности | критическая; существенная; незначительная |
| Рекомендуемое действие | эксплуатация разрешена; устранить несоответствия до повторного осмотра; эксплуатация запрещена |

## Шкала критичности

Шкала — решение команды проекта, а не норма закона (п. 10 ТЗ допускает
уточнение формулировок правил по согласованию с руководителем).

- **Критическая** — непосредственная угроза безопасности движения. Действие:
  эксплуатация запрещена.
- **Существенная** — нарушение обязательного требования без непосредственной
  угрозы. Действие: устранить до повторного осмотра.
- **Незначительная** — отклонение или малый запас до предела; на допуск не
  влияет.

## Итоговое заключение

- Есть хотя бы одно критическое несоответствие — «не допущен», даже если часть
  признаков неизвестна (п. 5.2.5).
- Критических нет, есть существенные, данные полны — «допущен с замечаниями»
  (п. 5.2.6).
- Несоответствий нет или только незначительные, данные полны — «допущен».
- Критических нет, но есть неизвестные признаки — заключение о допуске не
  выдаётся, статус `insufficient_data`; система показывает найденные
  несоответствия и перечисляет, чего не хватило.
- Противоречие входных данных — заключение не выдаётся, статус `contradiction`.

Правила одного признака построены непересекающимися полосами, а правила
слоя 2 — так, чтобы в каждом состоянии срабатывало ровно одно правило
заключения. Оба свойства проверяются автоматически (`tests/conflict_check.pl`,
испытание 12); результат — в `docs/control_examples.md`, раздел 5.
```

- [ ] **Step 6: Добавить в модель таблицы, построенные системой**

```sh
{
  printf '\n## Входные признаки\n\nЗа один осмотр спрашивается 25 (электро), 26 (дизель) или 27 (бензин, газ) признаков.\n\n'
  ./scripts/doc_tables.sh features
  printf '\n## Пороговые значения\n\nЗначения записаны по памяти и не сверены с оригиналами ТР ТС 018/2011 (прил. 8) и ГОСТ 33997-2016. Значения «принято командой» — решение команды проекта. Все значения подтверждает команда на этапе 2 ТЗ. Столбец `any` — порог не зависит ни от категории, ни от года; `before_2000` и `from_2000` выбираются по году выпуска.\n\n'
  ./scripts/doc_tables.sh thresholds
  printf '\n## Правила слоя 1. Признаки → несоответствие\n\n'
  ./scripts/doc_tables.sh rules
  printf '\n## Правила слоя 2. Несоответствия → заключение\n\nПосылки `has(Флаг)` и `lacks(Флаг)` проверяют состояние осмотра, `verdict(Заключение)` — уже полученное заключение.\n\n'
  ./scripts/doc_tables.sh verdict_rules
  printf '\n## Подсчёт правил\n\nСчитаются только продукционные правила; факты признаков, пороги, подписи и служебные предикаты в подсчёт не входят (п. 5.8.1 ТЗ).\n\n'
  ./scripts/doc_tables.sh counts
} >> docs/classification_model.md
```

Expected: в `docs/classification_model.md` появились разделы «Входные признаки» (28 строк), «Пороговые значения», «Правила слоя 1» (52 строки P01–P52), «Правила слоя 2» (8 строк V01–V08), «Подсчёт правил» (итого 60).

- [ ] **Step 7: Commit**

```bash
git add tests/doc_tables.pl scripts/doc_tables.sh docs/control_examples.md docs/classification_model.md
git commit -m "docs: control examples and classification model generated from the system"
```

---

### Task 13: Руководство пользователя, сверка с ТЗ, передача тестировщику, черновик отчёта и испытание 13

**Files:**
- Modify: `README.md` (сейчас пустой, создан `uv init`)
- Create: `docs/requirements_traceability.md`, `docs/tester_handoff.md`, `docs/report_draft.md`
- Create: `tests/test_docs.pl`
- Modify: `tests/all.pl`

**Interfaces:**
- Consumes: `project_paths:project_file/2`; все документы и исходники предыдущих задач.
- Produces: комплект документации по п. 6.2 ТЗ (краткое руководство — `README.md`; таблица контрольных примеров — `docs/control_examples.md`; отчёт — `docs/report_draft.md`, черновик для технического писателя) и испытание 13 (`t13_…`).

- [ ] **Step 1: Написать падающие тесты комплекта документации**

Тесты проверяют комплектность и связность: каждый пункт ТЗ упомянут в сверке, руководство содержит команду запуска, таблица контрольных примеров содержит все три столбца результатов и не содержит «НЕ ПРОЙДЕНО», в каждом исходном файле есть комментарий модуля.

**Создать `tests/test_docs.pl`:**
```prolog
:- encoding(utf8).

:- use_module(project_paths).
:- use_module(library(readutil)).

% Испытание 13 (п. 6.1, 6.2 ТЗ): комментарии в исходном тексте и комплект документации.
:- begin_tests(docs).

file_text(Relative, Text) :-
    project_file(Relative, Path),
    read_file_to_string(Path, Text, [encoding(utf8)]).

test(t13_documentation_kit_is_present) :-
    forall(member(File,
                  ['docs/tz_car_inspection_v1.0.docx',
                   'README.md',
                   'docs/report_draft.md',
                   'docs/control_examples.md',
                   'docs/classification_model.md',
                   'docs/requirements_traceability.md',
                   'docs/tester_handoff.md']),
           (   project_file(File, Path),
               assertion(exists_file(Path)),
               size_file(Path, Size),
               assertion(Size > 500)
           )).

test(t13_readme_has_the_start_command_and_test_command) :-
    file_text('README.md', Text),
    assertion(sub_string(Text, _, _, _, "swipl -q -s src/expert_system.pl -g start -t halt")),
    assertion(sub_string(Text, _, _, _, "scripts/run_tests.sh")),
    assertion(sub_string(Text, _, _, _, "SWI-Prolog 10.0.2")).

test(t13_control_examples_have_expected_and_actual_results) :-
    file_text('docs/control_examples.md', Text),
    forall(member(Part,
                  ["Ожидаемый результат", "Фактический результат",
                   "Проверка разработчиков", "Приёмочный результат",
                   "Проверка базы знаний на конфликты"]),
           assertion(sub_string(Text, _, _, _, Part))),
    assertion(\+ sub_string(Text, _, _, _, "НЕ ПРОЙДЕНО")).

test(t13_traceability_mentions_every_requirement) :-
    file_text('docs/requirements_traceability.md', Text),
    forall(member(Point,
                  ["5.1.1", "5.1.2", "5.1.3", "5.1.4", "5.1.5", "5.1.6",
                   "5.1.7", "5.1.8", "5.1.9", "5.1.10", "5.1.11",
                   "5.2.1", "5.2.2", "5.2.3", "5.2.4", "5.2.5", "5.2.6",
                   "5.5.1", "5.5.2", "5.5.3", "5.5.4",
                   "5.8.1", "5.8.2", "5.8.3", "5.8.4", "6.1", "6.2"]),
           assertion(sub_string(Text, _, _, _, Point))).

test(t13_every_source_file_has_a_module_comment) :-
    forall(member(File,
                  ['src/domain.pl', 'src/thresholds.pl', 'src/consistency.pl',
                   'src/knowledge_base.pl', 'src/inference.pl',
                   'src/expert_system.pl']),
           (   file_text(File, Text),
               assertion(sub_string(Text, _, _, _, "/** <module>"))
           )).

test(t13_report_draft_has_the_expected_sections) :-
    file_text('docs/report_draft.md', Text),
    forall(member(Heading,
                  ["## 1. Постановка задачи", "## 2. Предметная область",
                   "## 3. Классификация результата", "## 4. База знаний",
                   "## 5. Неполные и противоречивые данные",
                   "## 6. Диалог и объяснение", "## 7. Тестирование",
                   "## 8. Ограничения"]),
           assertion(sub_string(Text, _, _, _, Heading))).

:- end_tests(docs).
```

**Дописать в конец `tests/all.pl`:**
```prolog
:- consult(test_docs).
```

- [ ] **Step 2: Запустить тесты, убедиться, что падают**

Run: `./scripts/run_tests.sh`
Expected: 4 из 6 новых тестов `docs:…` — `FAILED` (`t13_documentation_kit_is_present`, `t13_readme_has_the_start_command_and_test_command`, `t13_traceability_mentions_every_requirement`, `t13_report_draft_has_the_expected_sections`: нужных файлов ещё нет); `t13_every_source_file_has_a_module_comment` и `t13_control_examples_have_expected_and_actual_results` проходят (второй — потому что задача 12 выполнена).

- [ ] **Step 3: Написать `README.md`**

**Создать `README.md`:**
````markdown
# Экспертная система технического осмотра автомобилей

Учебная экспертная система на SWI-Prolog. Пользователь отвечает на вопросы о
состоянии автомобиля (25–27 вопросов в зависимости от типа топлива), система
выдаёт:

- **заключение**: «допущен к эксплуатации», «допущен с замечаниями, требуется
  повторный осмотр» или «не допущен к эксплуатации»;
- **перечень несоответствий** по семи группам узлов и трём степеням критичности
  (критическая, существенная, незначительная);
- **рекомендуемое действие**: «эксплуатация разрешена», «устранить
  несоответствия до повторного осмотра» или «эксплуатация запрещена»;
- **объяснение**: использованные признаки и номера сработавших правил.

Результат носит справочный характер и не заменяет технический осмотр,
проводимый аккредитованным оператором. Система учебная и не является
результатом технического осмотра в смысле законодательства РФ.

## Требования

- SWI-Prolog 10.0.2 (контрольная версия) или совместимая 10.x;
- терминал с кодировкой UTF-8;
- Windows, Linux или macOS. Сеть и сторонние библиотеки Prolog не нужны.

Python-окружение (`pyproject.toml`, `uv.lock`) нужно только для подготовки
`.docx`-версий документов и в саму систему не входит.

## Быстрый запуск

Из корня проекта (команда не зависит от оболочки и подходит для Windows,
Linux и macOS):

```sh
swipl -q -s src/expert_system.pl -g start -t halt
```

На macOS и Linux то же делает `./scripts/run.sh`.

В интерактивной среде SWI-Prolog:

```prolog
?- [src/expert_system].
?- start.            % осмотры до команды «нет»
?- inspection.       % один осмотр
?- show_rule_count.  % число правил по слоям и группам
```

## Как проходит осмотр

1. Система задаёт вопросы по одному. Подсказка в скобках перечисляет допустимые
   ответы: слово из списка («удерживает», «слабо», «да», «нет»), латинское имя
   значения (`weak`) или число. Регистр не важен; десятичная запятая допустима.
2. **Категория ТС** (M1, M2-M3, N1, N2-N3), **год выпуска** и **тип топлива**
   обязательны: от них зависят пороги и набор вопросов. Ответ «неизвестно» для
   них не принимается.
3. На остальные вопросы можно ответить «неизвестно», «не знаю», `unknown` или
   `?`. Если критических несоответствий нет, заключение о допуске в этом
   случае не выдаётся, а система перечисляет, чего не хватило.
4. Вопросы про CO и CH задаются для бензина и газа, про дымность — для дизеля;
   для электромобиля их нет.
5. Недопустимое значение (слово не из списка, число вне диапазона) отклоняется,
   вопрос повторяется.
6. После отчёта система спрашивает «Начать новый осмотр? (да / нет)». Ответы
   предыдущего осмотра не влияют на следующий. Конец ввода (Ctrl-D в Linux и
   macOS, Ctrl-Z Enter в Windows) завершает работу без аварии.

## Пример отчёта

Критические несоответствия: тормозная сила 0,4, люфт руля 34°, нет крепления
колёс (остальные ответы — исправный автомобиль M1):

```text
Результат осмотра
-----------------
Статус: заключение сформировано.
Заключение: не допущен к эксплуатации
Рекомендуемое действие: эксплуатация запрещена

Выявленные несоответствия по группам:

  Тормозная система
    - P01, критическая: Удельная тормозная сила ниже минимально допустимой для категории ТС.
        признак: Удельная тормозная сила рабочей тормозной системы: 0.4
        признак: Категория транспортного средства: M1

  Рулевое управление
    - P13, критическая: Суммарный люфт рулевого управления выше критического.
        признак: Суммарный люфт рулевого управления, °: 34
        признак: Категория транспортного средства: M1

  Шины и колёса
    - P27, критическая: Отсутствуют крепёжные элементы колёс.
        признак: Крепление колёс: нет крепёжных элементов

Объяснение вывода:
  Правила несоответствий: P01, P13, P27.
  Правила заключения:
    - V01: Есть критическое несоответствие: транспортное средство не допускается независимо от состояния остальных узлов (п. 5.2.5 ТЗ).
    - V04: Не допущен: эксплуатация запрещена.

Оговорка: результат работы системы носит справочный характер и не заменяет технический осмотр, проводимый аккредитованным оператором.
```

Другие статусы отчёта: «данных недостаточно; заключение о допуске не
формируется» (критических нет, часть признаков неизвестна) и «обнаружены
противоречивые данные; заключение не формируется» (например, для дизеля
указан CO).

## Вызов без диалога

Для контрольных наборов есть программный вызов: список пар `Ключ-Значение`
(ключи и значения — в `docs/classification_model.md`, раздел «Входные признаки»).
Обязательны `category`, `year`, `fuel`; отсутствующий признак считается
неизвестным.

```prolog
?- use_module(src/inference), use_module(src/expert_system).
?- inspect_answers([category-m1, year-2015, fuel-petrol,
                    brake_force-0.4, brake_imbalance-5, parking_brake-holds,
                    brake_leak-tight, steering_play-3, steering_joints-ok,
                    headlights-ok, headlight_aim-ok, signal_lights-ok,
                    reflectors-present, tread_depth-5.0, tire_condition-ok,
                    wheel_fasteners-ok, windshield-intact, wipers-ok,
                    mirrors-ok, co-0.2, ch-50, seat_belts-ok,
                    first_aid_kit-yes, fire_extinguisher-yes,
                    warning_triangle-yes, structure-ok, fluid_leaks-none],
                   Report),
   print_report(Report).
```

`Report` — словарь с полями `status` (`ok`, `insufficient_data`,
`contradiction`, `invalid_input`), `verdict`, `action`, `findings`,
`verdict_rules`, `unknown`, `diagnostics`.

## Автоматические проверки

```sh
./scripts/run_tests.sh
```

Ожидается код возврата 0, все тесты `passed`, сообщений `failed` и `ERROR`
нет. Тесты покрывают 13 приёмочных испытаний таблицы 2 ТЗ, границы всех
порогов и проверку базы знаний на конфликты правил.

## Структура

| Путь | Назначение |
|---|---|
| `src/domain.pl` | 28 признаков, допустимые значения, подписи, проверка ввода |
| `src/thresholds.pl` | пороги с источниками |
| `src/consistency.pl` | противоречия во входных данных |
| `src/knowledge_base.pl` | 52 правила несоответствий (P01–P52) и 8 правил заключения (V01–V08) |
| `src/inference.pl` | логический вывод, хранилище ответов осмотра |
| `src/expert_system.pl` | диалог и печать отчёта |
| `tests/` | автоматические проверки |
| `scripts/` | запуск программы, тестов и генерация таблиц для документов |
| `docs/` | ТЗ, модель классификации, контрольные примеры, сверка с ТЗ, передача тестировщику, черновик отчёта |

## Ограничения

- Пороговые значения записаны по памяти и не сверены с ТР ТС 018/2011
  (прил. 8) и ГОСТ 33997-2016; их подтверждает команда проекта.
- Шкала критичности — решение команды, а не норма закона.
- Не поддерживаются прицепы и мототранспорт, гидроусилитель руля, ABS,
  периодичность осмотра.
````

- [ ] **Step 4: Написать сверку с ТЗ**

**Создать `docs/requirements_traceability.md`:**
```markdown
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
```

- [ ] **Step 5: Написать передачу тестировщику**

**Создать `docs/tester_handoff.md`:**
```markdown
# Передача продукта тестировщику

## Что передаётся

Вся рабочая папка проекта (или архив с ней). В ней: техническое задание
(`docs/tz_car_inspection_v1.0.docx`), программа (`src/`), автоматические
проверки (`tests/`), скрипты (`scripts/`), контрольные примеры
(`docs/control_examples.md`), сверка с ТЗ
(`docs/requirements_traceability.md`) и руководство (`README.md`). Сетевых
зависимостей у программы нет.

Это комплект разработчиков для начала тестирования. Отчёт о разработке
(до 10 страниц, п. 6.2 ТЗ) готовит технический писатель по черновику
`docs/report_draft.md` и результатам испытаний. Графу «Приёмочный результат»
в `docs/control_examples.md` заполняет тестировщик независимо; разработчики её
не заполняют.

Контрольная среда разработчиков: SWI-Prolog 10.0.2, macOS (arm64), кодировка
исходников и терминала UTF-8.

## Начало проверки

1. Открыть терминал в корне проекта.
2. Выполнить `swipl --version` и записать версию в протокол.
3. Запустить программу: `swipl -q -s src/expert_system.pl -g start -t halt`.
   Должен появиться первый вопрос «Категория транспортного средства».
4. Провести сценарии из `docs/control_examples.md`: раздел 1 (проверки
   диалога) и раздел 2 (наборы данных; ответы — разделы 3 и 4). Занести
   результат в последнюю графу.
5. Запустить автоматические проверки: `./scripts/run_tests.sh` (в Windows —
   `swipl -q -s tests/all.pl -g run_tests -t halt`). Ожидается код возврата 0,
   все тесты `passed`, сообщений `failed` и `ERROR` нет.

## Соответствие испытаниям таблицы 2 ТЗ

| Испытание | Что сделать вручную | Где смотреть |
|---:|---|---|
| 1 | Запустить основную команду, убедиться в первом вопросе | Раздел 1, Д9 |
| 2 | Пройти осмотр исправного набора: 27 вопросов для бензина, 26 для дизеля, 25 для электромобиля | Разделы 3 и 4 |
| 3 | Ввести «грузовик» вместо категории и «1.5» вместо удельной тормозной силы, затем допустимые значения | Раздел 1, Д1–Д3 |
| 4 | В интерактивной среде выполнить `?- [src/expert_system]. ?- show_rule_count.` — итог 60 (52 + 8) | Раздел 6 |
| 5 | Провести наборы 1–4 | Раздел 2 |
| 6 | В отчёте набора 4 найти номера правил и признаки | Раздел 2, набор 4 |
| 7 | Наборы 10, 12, 13; прервать ввод (Ctrl-D) посреди осмотра | Раздел 2; раздел 1, Д6 |
| 8 | Набор 5 | Раздел 2 |
| 9 | Два осмотра подряд: набор 3, затем набор 1 | Раздел 1, Д8 |
| 10 | Убедиться, что русский текст читается; при необходимости повторить в Windows и Linux | Раздел 1, Д9 |
| 11 | Открыть `src/thresholds.pl`: у каждого порога указан источник; в отчёте есть оговорка | `src/thresholds.pl` |
| 12 | Просмотреть проверку конфликтов | Раздел 5 |
| 13 | Проверить комментарии в `src/` и комплект документов | `docs/requirements_traceability.md` |

## Что сообщать разработчикам

- расхождение фактического результата с ожидаемым: номер набора, введённые
  ответы, текст вывода;
- ошибку или аварийное завершение: точная последовательность ввода;
- некорректное отображение русского текста: операционная система, терминал,
  версия SWI-Prolog.

## Известные ограничения

- Пороговые значения записаны по памяти и не сверены с ТР ТС 018/2011
  (прил. 8) и ГОСТ 33997-2016; расхождение числа с нормативом — замечание к
  порогу, а не к структуре системы.
- Шкала критичности — решение команды.
- Проверка на Windows и Linux разработчиками не проводилась.
```

- [ ] **Step 6: Написать черновик отчёта**

Черновик пишется для технического писателя, который доведёт его до отчёта объёмом не более 10 страниц (без ТЗ, п. 6.2 ТЗ).

**Создать `docs/report_draft.md`:**
````markdown
# Отчёт о разработке экспертной системы технического осмотра автомобилей (черновик)

> Черновик для технического писателя. Итоговый отчёт — не более 10 страниц без
> ТЗ (п. 6.2 ТЗ); ТЗ приводится в приложении. Числа получены на текущей версии
> кода; перед сдачей их нужно сверить командами `./scripts/run_tests.sh` и
> `./scripts/doc_tables.sh counts`.

## 1. Постановка задачи

Цель — действующая экспертная система, представляющая знания о правилах
технического осмотра автомобилей в виде продукционных правил и выполняющая
логический вывод средствами Prolog (п. 4.2 ТЗ). По ответам пользователя о
состоянии автомобиля система определяет заключение о допуске к эксплуатации,
перечень несоответствий и рекомендуемое действие и поясняет результат.

Система учебно-демонстрационная. Её заключение не заменяет диагностическую
карту аккредитованного оператора технического осмотра; это напоминание
печатается в конце каждого отчёта (п. 5.8.4 ТЗ). Реализация — SWI-Prolog
10.0.2, локальный диалог в текстовом режиме, кодировка UTF-8.

## 2. Предметная область и входные признаки

Система принимает 28 признаков; за один осмотр спрашивается 25 (электромобиль),
26 (дизель) или 27 (бензин, газ). Это больше 15 признаков по п. 5.1.2 ТЗ;
все 14 обязательных признаков покрыты (соответствие — в
`docs/requirements_traceability.md`).

| Группа | Признаки |
|---|---|
| Общие | категория ТС (M1, M2-M3, N1, N2-N3), год выпуска, тип топлива |
| Тормозная система | удельная тормозная сила, неравномерность тормозных сил оси, стояночная система, герметичность привода |
| Рулевое управление | суммарный люфт, состояние шарниров и тяг |
| Внешние световые приборы | фары, регулировка фар, сигнальные фонари, световозвращатели |
| Шины и колёса | глубина протектора, состояние шин, крепление колёс |
| Приборы обзора | ветровое стекло, стеклоочистители, зеркала |
| Экология | CO и CH (бензин, газ), дымность (дизель) |
| Прочее | ремни, аптечка, огнетушитель, знак аварийной остановки, несущие элементы, утечки жидкостей |

Категория, год выпуска и тип топлива обязательны: от них зависят пороги и набор
вопросов. На остальные признаки допустим ответ «неизвестно».

## 3. Классификация результата

Результат классифицируется по четырём направлениям (п. 5.1.11 ТЗ):

- итоговое заключение (три значения);
- группа несоответствия (семь групп);
- степень критичности: критическая, существенная, незначительная;
- рекомендуемое действие (три значения).

Шкала критичности — решение команды проекта. Критическое несоответствие —
непосредственная угроза безопасности движения; существенное — нарушение
обязательного требования без непосредственной угрозы; незначительное —
отклонение или малый запас до предела, на допуск не влияющий.

## 4. База знаний и логический вывод

Вывод двухслойный. **Слой 1** — 52 правила P01–P52 «признаки → несоответствие»;
в каждом заданы группа, критичность и текст. **Слой 2** — 8 правил V01–V08
«состояние осмотра → заключение, действие, статус». Всего 60 правил (ориентир
ТЗ — 60, минимум — 50).

Пример правила слоя 1 (`src/knowledge_base.pl`):

```prolog
production_rule(p13, steering, critical,
    [gt_t(steering_play, steering_play_crit)],
    "Суммарный люфт рулевого управления выше критического.").
```

Условие сравнивает ответ с именованным порогом; значение порога выбирается по
категории ТС (для CO и CH — по году выпуска) из `src/thresholds.pl`. Пороги
вынесены в одну группу фактов с источником (п. 5.8.3 ТЗ), их 16 имён и 41
значение. Числа записаны по памяти и подлежат сверке с ТР ТС 018/2011 (прил. 8)
и ГОСТ 33997-2016.

Из найденных несоответствий и полноты данных строится состояние осмотра;
правила слоя 2 по нему выдают результат:

| Правило | Условие | Результат |
|---|---|---|
| V01 | есть критическое несоответствие | не допущен (п. 5.2.5 ТЗ) |
| V02 | есть существенные, критических нет, данные полны | допущен с замечаниями |
| V03 | нет несоответствий или только незначительные, данные полны | допущен |
| V04–V06 | по заключению | эксплуатация запрещена / устранить до повторного осмотра / разрешена |
| V07 | критических нет, есть неизвестные признаки | заключение не выдаётся |
| V08 | противоречие входных данных | заключение не выдаётся |

Правила V01–V03, V07, V08 взаимоисключающи по построению; правила одного
признака построены непересекающимися полосами. Оба свойства проверяются
автоматически (см. раздел 7).

## 5. Неполные и противоречивые данные

Если критическое несоответствие найдено, заключение «не допущен» выдаётся даже
при неизвестных признаках: оно обосновано и не зависит от остальных ответов.
Если критических нет, а часть признаков неизвестна, допускающее заключение не
выдаётся: система показывает найденные несоответствия и перечисляет, чего не
хватило (статус `insufficient_data`).

Противоречия входных данных проверяет модуль `consistency`. Пять условий,
например: для дизеля указан CO или CH; для электромобиля указаны показатели
выхлопа или утечка топлива; шарниры разрушены при люфте меньше 5°. При
противоречии выводится диагностика, заключение не формируется (статус
`contradiction`). Ошибочный ввод и конец ввода не приводят к аварии (п. 5.2.2 ТЗ).

## 6. Диалог и объяснение

Диалог задаёт вопросы по одному, проверяет допустимость каждого значения и
повторяет запрос при ошибке. После отчёта пользователь выбирает: новый осмотр
или выход. Ответы предыдущего осмотра удаляются до и после осмотра
(п. 5.1.4, 5.2.3 ТЗ).

Отчёт группирует несоответствия по узлам, для каждого показывает номер
правила, критичность, текст и использованные признаки, затем — правила
заключения. Пример (набор 4 из `docs/control_examples.md`): люфт 34° →
правило P13 (рулевое управление, критическая) → правило V01 → «не допущен к
эксплуатации», действие V04 — «эксплуатация запрещена» (п. 5.1.8, 5.8.2 ТЗ).
Полный пример вывода — в `README.md`.

## 7. Тестирование

Автоматические проверки (plunit, `./scripts/run_tests.sh`):

- тесты домена, порогов, противоречий входа и движка вывода;
- проверка границ каждой полосы каждого правила (по категориям и годам);
- 13 приёмочных испытаний таблицы 2 ТЗ (`tests/test_acceptance.pl`,
  `tests/test_docs.pl`), включая запуск основной команды в отдельном процессе;
- проверка базы знаний на конфликты (испытание 12, п. 5.2.4 ТЗ): для каждой
  пары правил слоя 1 с общим признаком и разной критичностью перебираются
  значения (сетка по диапазону, пороги и их окрестности, все категории ТС,
  границы года), а для слоя 2 — все 32 сочетания флагов состояния. Найденных
  конфликтов нет; результат зафиксирован в `docs/control_examples.md`, раздел 5.

Контрольные примеры (13 наборов данных и 9 проверок диалога) описаны в
`docs/control_examples.md`; графу «Приёмочный результат» заполняет тестировщик.

## 8. Ограничения и дальнейшая работа

- Пороговые значения не сверены с первоисточниками; ошибка в числе меняет
  результат осмотра, но не структуру системы, так как пороги лежат в одном файле.
- Шкала критичности — решение команды (п. 10 ТЗ допускает уточнение формулировок
  правил по согласованию с руководителем).
- Проверка на Windows и Linux разработчиками не проводилась.
- Не вошли в первую версию: прицепы и мототранспорт, гидроусилитель, ABS,
  периодичность осмотра, раздельный учёт шарниров рулевого привода.

## Приложения

- Приложение А. Техническое задание (`docs/tz_car_inspection_v1.0.docx`).
- Приложение Б. Таблица контрольных примеров (`docs/control_examples.md`).
- Приложение В. Модель классификации со всеми правилами (`docs/classification_model.md`).
````

- [ ] **Step 7: Запустить тесты, убедиться, что проходят**

Run: `./scripts/run_tests.sh`
Expected: 153 теста `passed` (последняя строка `[153/153] … passed`), код возврата 0, строк `failed` нет.

Затем проверить, что числа в отчёте и руководстве совпадают с кодом:

```sh
./scripts/doc_tables.sh counts | tail -3
```

Expected: строки с итогами `52`, `8` и `60`.

- [ ] **Step 8: Commit**

```bash
git add README.md docs/requirements_traceability.md docs/tester_handoff.md docs/report_draft.md tests/test_docs.pl tests/all.pl
git commit -m "docs: user guide, requirements traceability, tester handoff, report draft, acceptance test 13"
```

---

## Самопроверка плана

**Покрытие спеки.** Разделы спеки → задачи:

| Раздел спеки | Задача |
|---|---|
| 1. Цель и рамки, классы результатов | Global Constraints; задача 2 (подписи классов) |
| 2. Двухслойный вывод | задачи 5–8 (слой 2 и слой 1), задача 9 (взаимоисключаемость) |
| 3. Структура проекта; пороги по категории; источники порогов | задачи 2–5, 10; задача 3 |
| 4. 28 входных признаков | задача 2 |
| 5. Диалог: условные вопросы, «неизвестно», недостаток данных, противоречия, `inspect_answers/2`, оговорка, завершение | задачи 2, 4, 5, 10 |
| 6. Шкала критичности, пороги, правила P01–P52, V01–V08, объяснение | задачи 3, 5–8, 10 |
| 7. Проверка конфликтов, тесты, документация, скрипты | задачи 1, 9, 11–13 |
| 8. Принятые решения (YAGNI) | Global Constraints |
| 9. Риски | `thresholds.pl` (комментарий), `docs/*` (ограничения) |

**Отступления от спеки** перечислены в начале плана (год > 2026, готовые значения запасов, разнесение по модулям, порядок слоёв в файле, латинские имена).

**Согласованность имён.** Ключи признаков, атомы значений и идентификаторы правил (`p01…p52`, `v01…v08`) заданы в задачах 2, 5–8 и используются в тестах, сценариях и документах без изменений. Отчёт: поля `status`, `verdict`, `action`, `findings`, `verdict_rules`, `unknown`, `diagnostics` — как в задаче 5.
