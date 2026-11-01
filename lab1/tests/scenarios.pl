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
