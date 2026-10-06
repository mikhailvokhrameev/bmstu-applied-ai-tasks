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
