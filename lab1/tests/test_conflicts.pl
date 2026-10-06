:- encoding(utf8).

:- use_module(conflict_check).

% Испытание 12 (п. 5.2.4 ТЗ): проверка базы знаний на противоречивость.
:- begin_tests(conflicts).

test(layer1_has_pairs_to_check) :-
    layer1_pairs(Pairs),
    length(Pairs, Count),
    assertion(Count >= 20).

test(layer1_rules_with_a_common_feature_never_match_together) :-
    layer1_conflicts(Conflicts),
    assertion(Conflicts == []).

test(checker_finds_an_overlap_when_bands_overlap) :-
    overlap_witness([gt_t(steering_play, steering_play_max)],
                    [gt_t(steering_play, steering_play_crit)],
                    Answers),
    assertion(memberchk(steering_play-_, Answers)).

test(checker_finds_no_overlap_for_disjoint_bands) :-
    assertion(\+ overlap_witness([le_t(steering_play, steering_play_max)],
                                 [gt_t(steering_play, steering_play_max)],
                                 _)).

test(checker_respects_category_conditions) :-
    assertion(\+ overlap_witness([eq(reflectors, missing), in(category, [m1, n1])],
                                 [eq(reflectors, missing), in(category, [m2_m3, n2_n3])],
                                 _)),
    assertion(overlap_witness([eq(reflectors, missing), in(category, [m1, n1])],
                              [eq(reflectors, missing), in(category, [m1])],
                              _)).

test(layer2_covers_all_32_states) :-
    layer2_states(States),
    length(States, Count),
    assertion(Count =:= 32),
    sort(States, Unique),
    assertion(length(Unique, 32)).

test(layer2_gives_exactly_one_outcome_in_every_state) :-
    layer2_violations(Violations),
    assertion(Violations == []).

:- end_tests(conflicts).
