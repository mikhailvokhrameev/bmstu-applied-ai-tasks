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
