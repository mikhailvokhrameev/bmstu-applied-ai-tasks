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
