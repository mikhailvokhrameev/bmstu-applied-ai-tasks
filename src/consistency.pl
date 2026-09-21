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
