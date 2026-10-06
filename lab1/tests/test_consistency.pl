:- encoding(utf8).

:- use_module('../src/consistency').

:- begin_tests(consistency).

test(consistent_petrol_car_has_no_issues) :-
    consistency_issues([fuel-petrol, co-0.3, ch-50, steering_play-3], Issues),
    assertion(Issues == []).

test(diesel_with_co_is_a_contradiction) :-
    consistency_issues([fuel-diesel, co-0.3], Issues),
    assertion(length(Issues, 1)).

test(diesel_with_ch_is_a_contradiction) :-
    consistency_issues([fuel-diesel, ch-50], Issues),
    assertion(length(Issues, 1)).

test(diesel_with_both_co_and_ch_reports_once) :-
    consistency_issues([fuel-diesel, co-0.3, ch-50], Issues),
    assertion(length(Issues, 1)).

test(unknown_measurement_is_not_a_contradiction) :-
    consistency_issues([fuel-diesel, co-unknown, ch-unknown], Issues),
    assertion(Issues == []).

test(petrol_with_smoke_is_a_contradiction) :-
    consistency_issues([fuel-petrol, smoke-1.0], Issues),
    assertion(length(Issues, 1)).

test(gas_with_smoke_is_a_contradiction) :-
    consistency_issues([fuel-gas, smoke-1.0], Issues),
    assertion(length(Issues, 1)).

test(electric_with_exhaust_values_is_a_contradiction) :-
    consistency_issues([fuel-electric, ch-100], Issues),
    assertion(length(Issues, 1)),
    consistency_issues([fuel-electric, smoke-1.0], Issues2),
    assertion(length(Issues2, 1)).

test(broken_joints_with_tiny_play_is_a_contradiction) :-
    consistency_issues([steering_joints-broken, steering_play-4], Issues),
    assertion(length(Issues, 1)).

test(broken_joints_with_play_of_five_degrees_is_consistent) :-
    consistency_issues([steering_joints-broken, steering_play-5], Issues),
    assertion(Issues == []).

test(broken_joints_with_unknown_play_is_consistent) :-
    consistency_issues([steering_joints-broken, steering_play-unknown], Issues),
    assertion(Issues == []).

test(electric_with_fuel_leak_is_a_contradiction) :-
    consistency_issues([fuel-electric, fluid_leaks-fuel], Issues),
    assertion(length(Issues, 1)).

test(petrol_with_fuel_leak_is_consistent) :-
    consistency_issues([fuel-petrol, fluid_leaks-fuel], Issues),
    assertion(Issues == []).

test(several_contradictions_are_all_reported) :-
    consistency_issues([fuel-electric, co-0.3, fluid_leaks-fuel,
                        steering_joints-broken, steering_play-1], Issues),
    assertion(length(Issues, 3)).

:- end_tests(consistency).
