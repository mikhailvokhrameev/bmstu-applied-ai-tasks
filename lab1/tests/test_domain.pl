:- encoding(utf8).

:- use_module('../src/domain').

:- begin_tests(domain).

test(at_least_fifteen_questions) :-
    findall(Key, question(Key, _, _), Keys),
    length(Keys, Count),
    assertion(Count >= 15).

test(twenty_eight_questions_in_total) :-
    findall(Key, question(Key, _, _), Keys),
    length(Keys, Count),
    assertion(Count =:= 28),
    sort(Keys, Unique),
    assertion(length(Unique, 28)).

test(inspection_size_depends_on_fuel) :-
    forall(member(Fuel-Expected, [electric-25, diesel-26, petrol-27, gas-27]),
           (   findall(Key, (question(Key, _, _), question_applies(Key, Fuel)), Keys),
               length(Keys, Count),
               assertion(Count =:= Expected)
           )).

test(mandatory_features_are_covered) :-
    forall(member(Key, [category, year, brake_force, parking_brake, brake_leak,
                        steering_play, headlights, headlight_aim, tread_depth,
                        tire_condition, windshield, mirrors, wipers, co, smoke,
                        seat_belts, first_aid_kit, fire_extinguisher,
                        warning_triangle, structure, fluid_leaks]),
           assertion(known_question_key(Key))).

test(choice_value_is_accepted) :-
    assertion(valid_value(parking_brake, weak)).

test(value_outside_choice_is_rejected) :-
    assertion(\+ valid_value(parking_brake, broken)).

test(number_in_range_is_accepted) :-
    assertion(valid_value(brake_force, 0.8)),
    assertion(valid_value(brake_force, 0)),
    assertion(valid_value(brake_force, 1.2)).

test(number_out_of_range_is_rejected) :-
    assertion(\+ valid_value(brake_force, 1.3)),
    assertion(\+ valid_value(brake_force, -0.1)),
    assertion(\+ valid_value(tread_depth, 16)).

test(text_is_not_a_number) :-
    assertion(\+ valid_value(steering_play, abc)).

test(year_is_integer_in_range) :-
    assertion(valid_value(year, 2010)),
    assertion(\+ valid_value(year, 1949)),
    assertion(\+ valid_value(year, 2027)),
    assertion(\+ valid_value(year, 2010.5)).

test(unknown_is_allowed_except_required_keys) :-
    assertion(valid_value(brake_force, unknown)),
    assertion(valid_value(parking_brake, unknown)),
    assertion(\+ valid_value(category, unknown)),
    assertion(\+ valid_value(year, unknown)),
    assertion(\+ valid_value(fuel, unknown)).

test(hints_list_labels_and_unknown) :-
    answer_hint(parking_brake, H1),
    assertion(H1 == "удерживает / слабо / не удерживает / неизвестно"),
    answer_hint(fuel, H2),
    assertion(H2 == "бензин / дизель / газ / электро"),
    answer_hint(brake_force, H3),
    assertion(H3 == "число от 0 до 1.2 / неизвестно"),
    answer_hint(year, H4),
    assertion(H4 == "целое число от 1950 до 2026").

test(value_text_uses_label_or_number) :-
    value_text(parking_brake, weak, T1),
    assertion(T1 == "слабо"),
    value_text(brake_force, 0.8, T2),
    assertion(T2 == "0.8"),
    value_text(first_aid_kit, yes, T3),
    assertion(T3 == "да").

test(validate_accepts_partial_list_with_required_keys) :-
    validate_answers([category-m1, year-2015, fuel-petrol], Errors),
    assertion(Errors == []).

test(validate_reports_unknown_key) :-
    validate_answers([category-m1, year-2015, fuel-petrol, colour-red], Errors),
    assertion(length(Errors, 1)).

test(validate_reports_bad_value_and_out_of_range) :-
    validate_answers([category-m1, year-2015, fuel-petrol,
                      brake_force-9, parking_brake-broken], Errors),
    assertion(length(Errors, 2)).

test(validate_reports_duplicate_key_once) :-
    validate_answers([category-m1, year-2015, fuel-petrol,
                      brake_leak-tight, brake_leak-major], Errors),
    assertion(length(Errors, 1)).

test(validate_reports_missing_required_key) :-
    validate_answers([category-m1, year-2015], Errors),
    assertion(length(Errors, 1)).

test(validate_rejects_unknown_for_required_key) :-
    validate_answers([category-unknown, year-2015, fuel-petrol], Errors),
    assertion(length(Errors, 1)).

test(validate_reports_non_pair_and_non_list) :-
    validate_answers([category-m1, year-2015, fuel-petrol, oops], E1),
    assertion(length(E1, 1)),
    validate_answers(not_a_list, E2),
    assertion(length(E2, 1)).

:- end_tests(domain).
