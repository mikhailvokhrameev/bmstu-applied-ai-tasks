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
