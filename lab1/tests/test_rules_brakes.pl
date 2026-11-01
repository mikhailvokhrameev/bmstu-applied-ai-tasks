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
