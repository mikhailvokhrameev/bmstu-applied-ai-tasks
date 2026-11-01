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
