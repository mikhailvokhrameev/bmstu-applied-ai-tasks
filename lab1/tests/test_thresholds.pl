:- encoding(utf8).

:- use_module('../src/thresholds').

:- begin_tests(thresholds).

test(every_threshold_has_a_source) :-
    forall(threshold(_, _, _, _, Source),
           (   assertion(string(Source)),
               assertion(Source \== "")
           )).

test(every_threshold_is_a_number) :-
    forall(threshold(_, _, Value, _, _), assertion(number(Value))).

test(every_threshold_has_a_complete_column_set) :-
    forall(threshold_name(Name),
           (   findall(Column, threshold(Name, Column, _, _, _), Columns),
               assertion(   (   Columns == [m1, m2_m3, n1, n2_n3]
                            ;   Columns == [before_2000, from_2000]
                            ;   Columns == [any]
                            ))
           )).

test(sixteen_named_thresholds) :-
    findall(Name, threshold_name(Name), Names),
    length(Names, Count),
    assertion(Count =:= 16).

test(category_thresholds_follow_the_spec) :-
    threshold_value(brake_force_min, [m1, any], A),
    assertion(A =:= 0.59),
    threshold_value(brake_force_min, [n2_n3, any], B),
    assertion(B =:= 0.51),
    threshold_value(steering_play_max, [n2_n3, from_2000, any], C),
    assertion(C =:= 25),
    threshold_value(steering_play_crit, [m2_m3, any], D),
    assertion(D =:= 40),
    threshold_value(tread_min, [n2_n3, before_2000, any], E),
    assertion(E =:= 1.0).

test(year_column_selects_ecology_limits) :-
    threshold_value(co_max, [m1, before_2000, any], A),
    assertion(A =:= 3.5),
    threshold_value(co_max, [m1, from_2000, any], B),
    assertion(B =:= 0.5),
    threshold_value(ch_max, [n1, before_2000, any], C),
    assertion(C =:= 1200),
    threshold_value(ch_max, [n1, from_2000, any], D),
    assertion(D =:= 100).

test(category_independent_thresholds_use_any) :-
    threshold_value(brake_imbalance_max, [m1, from_2000, any], A),
    assertion(A =:= 20),
    threshold_value(smoke_max, [n2_n3, before_2000, any], B),
    assertion(B =:= 2.5).

test(context_key_tells_which_answer_selects_the_column) :-
    assertion(threshold_context_key(brake_force_min, category)),
    assertion(threshold_context_key(co_max, year)),
    assertion(\+ threshold_context_key(brake_imbalance_max, _)),
    assertion(\+ threshold_context_key(smoke_max, _)).

test(unknown_threshold_name_has_no_value) :-
    assertion(\+ threshold_value(no_such_threshold, [m1, any], _)).

:- end_tests(thresholds).
