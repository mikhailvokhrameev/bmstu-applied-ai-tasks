:- encoding(utf8).

:- use_module(fixtures).

% Границы полос правил P23–P33.
:- begin_tests(rules_tires_visibility).

test(tread_bands_for_m1) :-
    rules_for([tread_depth-1.59], A),
    assertion(A == [p23]),
    rules_for([tread_depth-1.6], B),
    assertion(B == [p24]),
    rules_for([tread_depth-2.59], C),
    assertion(C == [p24]),
    rules_for([tread_depth-2.6], D),
    assertion(D == []).

test(tread_limits_depend_on_category) :-
    rules_for([category-m2_m3, tread_depth-1.9], A),
    assertion(A == [p23]),
    rules_for([category-m2_m3, tread_depth-2.0], B),
    assertion(B == [p24]),
    rules_for([category-m2_m3, tread_depth-3.0], C),
    assertion(C == []),
    rules_for([category-n2_n3, tread_depth-0.9], D),
    assertion(D == [p23]),
    rules_for([category-n2_n3, tread_depth-1.0], E),
    assertion(E == [p24]),
    rules_for([category-n2_n3, tread_depth-2.0], F),
    assertion(F == []).

test(tread_severities) :-
    severity_of([tread_depth-1.5], p23, S23),
    assertion(S23 == critical),
    severity_of([tread_depth-2.0], p24, S24),
    assertion(S24 == minor).

test(tire_condition_and_fasteners) :-
    rules_for([tire_condition-cord_visible], A),
    assertion(A == [p25]),
    severity_of([tire_condition-cord_visible], p25, S25),
    assertion(S25 == critical),
    rules_for([tire_condition-damaged], B),
    assertion(B == [p26]),
    severity_of([tire_condition-damaged], p26, S26),
    assertion(S26 == major),
    rules_for([wheel_fasteners-missing], C),
    assertion(C == [p27]),
    severity_of([wheel_fasteners-missing], p27, S27),
    assertion(S27 == critical).

test(windshield) :-
    rules_for([windshield-driver_crack], A),
    assertion(A == [p28]),
    severity_of([windshield-driver_crack], p28, S28),
    assertion(S28 == critical),
    rules_for([windshield-chips], B),
    assertion(B == [p29]),
    severity_of([windshield-chips], p29, S29),
    assertion(S29 == minor).

test(wipers) :-
    rules_for([wipers-not_working], A),
    assertion(A == [p30]),
    severity_of([wipers-not_working], p30, S30),
    assertion(S30 == critical),
    rules_for([wipers-worn], B),
    assertion(B == [p31]),
    severity_of([wipers-worn], p31, S31),
    assertion(S31 == major).

test(mirrors) :-
    rules_for([mirrors-damaged], A),
    assertion(A == [p32]),
    severity_of([mirrors-damaged], p32, S32),
    assertion(S32 == major),
    rules_for([mirrors-missing], B),
    assertion(B == [p33]),
    severity_of([mirrors-missing], p33, S33),
    assertion(S33 == critical).

:- end_tests(rules_tires_visibility).
