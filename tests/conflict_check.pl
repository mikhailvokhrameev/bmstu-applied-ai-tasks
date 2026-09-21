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
