:- encoding(utf8).

:- use_module(fixtures).

% Границы полос правил P11–P22.
:- begin_tests(rules_steering_lighting).

test(play_bands_for_m1) :-
    rules_for([steering_play-8], A),
    assertion(A == []),
    rules_for([steering_play-9], B),
    assertion(B == [p11]),
    rules_for([steering_play-10], C),
    assertion(C == [p11]),
    rules_for([steering_play-11], D),
    assertion(D == [p12]),
    rules_for([steering_play-20], E),
    assertion(E == [p12]),
    rules_for([steering_play-21], F),
    assertion(F == [p13]).

test(play_limits_depend_on_category) :-
    rules_for([category-m2_m3, steering_play-17], A),
    assertion(A == [p11]),
    rules_for([category-m2_m3, steering_play-21], B),
    assertion(B == [p12]),
    rules_for([category-m2_m3, steering_play-41], C),
    assertion(C == [p13]),
    rules_for([category-n2_n3, steering_play-25], D),
    assertion(D == [p11]),
    rules_for([category-n2_n3, steering_play-26], E),
    assertion(E == [p12]),
    rules_for([category-n2_n3, steering_play-51], F),
    assertion(F == [p13]).

test(play_severities) :-
    severity_of([steering_play-9], p11, S11),
    assertion(S11 == minor),
    severity_of([steering_play-11], p12, S12),
    assertion(S12 == major),
    severity_of([steering_play-21], p13, S13),
    assertion(S13 == critical).

test(steering_joints) :-
    rules_for([steering_joints-worn], A),
    assertion(A == [p14]),
    severity_of([steering_joints-worn], p14, S14),
    assertion(S14 == major),
    rules_for([steering_joints-broken, steering_play-5], B),
    assertion(B == [p15]),
    severity_of([steering_joints-broken, steering_play-5], p15, S15),
    assertion(S15 == critical).

test(headlights) :-
    rules_for([headlights-not_working], A),
    assertion(A == [p16]),
    severity_of([headlights-not_working], p16, S16),
    assertion(S16 == critical),
    rules_for([headlights-one_faulty], B),
    assertion(B == [p17]),
    severity_of([headlights-one_faulty], p17, S17),
    assertion(S17 == major),
    rules_for([headlight_aim-misaligned], C),
    assertion(C == [p18]),
    severity_of([headlight_aim-misaligned], p18, S18),
    assertion(S18 == major).

test(signal_lights) :-
    rules_for([signal_lights-not_working], A),
    assertion(A == [p19]),
    severity_of([signal_lights-not_working], p19, S19),
    assertion(S19 == critical),
    rules_for([signal_lights-partial], B),
    assertion(B == [p20]),
    severity_of([signal_lights-partial], p20, S20),
    assertion(S20 == major).

test(reflectors_severity_depends_on_category) :-
    forall(member(Category, [m1, n1]),
           (   rules_for([category-Category, reflectors-missing], Ids),
               assertion(Ids == [p21])
           )),
    forall(member(Category, [m2_m3, n2_n3]),
           (   rules_for([category-Category, reflectors-missing], Ids),
               assertion(Ids == [p22])
           )),
    severity_of([reflectors-missing], p21, S21),
    assertion(S21 == minor),
    severity_of([category-m2_m3, reflectors-missing], p22, S22),
    assertion(S22 == major).

:- end_tests(rules_steering_lighting).
