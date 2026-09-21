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
