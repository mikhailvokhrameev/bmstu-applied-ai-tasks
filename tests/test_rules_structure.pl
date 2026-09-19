:- encoding(utf8).

:- use_module('../src/knowledge_base').
:- use_module('../src/domain').
:- use_module('../src/thresholds').
:- use_module('../src/inference',
              [rule_count/1, rule_count_by_group/2, verdict_rule_count/1]).
:- use_module(project_paths).

:- begin_tests(rules_structure).

numbered_ids(Prefix, Count, Ids) :-
    findall(Id,
            (   between(1, Count, N),
                (   N < 10
                ->  format(atom(Id), '~w0~d', [Prefix, N])
                ;   format(atom(Id), '~w~d', [Prefix, N])
                )
            ),
            Ids).

test(layer1_has_at_least_fifty_rules) :-
    rule_count(Count),
    assertion(Count >= 50).

test(layer1_has_52_and_layer2_has_8_rules) :-
    rule_count(Layer1),
    verdict_rule_count(Layer2),
    assertion(Layer1 =:= 52),
    assertion(Layer2 =:= 8),
    assertion(Layer1 + Layer2 =:= 60).

test(rule_counts_by_group) :-
    forall(member(Group-Expected,
                  [brakes-10, steering-5, lighting-7, tires-5,
                   visibility-6, ecology-6, other-13]),
           (   rule_count_by_group(Group, Count),
               assertion(Count =:= Expected)
           )).

test(layer1_ids_are_unique_and_sequential) :-
    findall(Id, production_rule(Id, _, _, _, _), Ids),
    numbered_ids(p, 52, Expected),
    assertion(Ids == Expected).

test(layer2_ids_are_unique_and_sequential) :-
    findall(Id, verdict_rule(Id, _, _, _), Ids),
    numbered_ids(v, 8, Expected),
    assertion(Ids == Expected).

test(every_rule_has_known_group_severity_and_text) :-
    forall(production_rule(Id, Group, Severity, Conditions, Text),
           (   assertion(rule_group(Group)),
               assertion(memberchk(Severity, [critical, major, minor])),
               assertion(string(Text)),
               assertion(Text \== ""),
               assertion(Conditions \== []),
               assertion(atom(Id))
           )).

test(all_severities_and_groups_are_used) :-
    forall(member(Severity, [critical, major, minor]),
           assertion(production_rule(_, _, Severity, _, _))),
    forall(rule_group(Group),
           (   assertion(production_rule(_, Group, _, _, _)),
               assertion(group_label(Group, _))
           )).

test(condition_keys_are_known_features) :-
    forall((production_rule(_, _, _, Conditions, _), member(Condition, Conditions)),
           (   arg(1, Condition, Key),
               assertion(known_question_key(Key))
           )).

test(every_feature_is_used_by_rules_except_fuel) :-
    findall(Key,
            (   production_rule(_, _, _, Conditions, _),
                member(Condition, Conditions),
                arg(1, Condition, Key)
            ),
            Used0),
    sort(Used0, Used),
    findall(Key, (question(Key, _, _), \+ memberchk(Key, Used)), Unused),
    % Тип топлива не входит в условия правил: он выбирает набор вопросов
    % и проверяется в consistency.pl.
    assertion(Unused == [fuel]).

test(every_referenced_threshold_exists_for_every_category_and_year) :-
    forall((   production_rule(_, _, _, Conditions, _),
               member(Condition, Conditions),
               memberchk(Condition, [lt_t(_, _), le_t(_, _), gt_t(_, _), ge_t(_, _)]),
               arg(2, Condition, Name)
           ),
           forall((   member(Category, [m1, m2_m3, n1, n2_n3]),
                      member(YearColumn, [before_2000, from_2000])
                  ),
                  assertion(threshold_value(Name, [Category, YearColumn, any], _)))).

test(layer2_results_cover_all_verdicts_and_actions) :-
    forall(member(Verdict, [not_admitted, admitted_with_remarks, admitted]),
           (   assertion(verdict_rule(_, _, verdict(Verdict), _)),
               assertion(verdict_label(Verdict, _))
           )),
    forall(member(Action, [prohibited, fix_before_reinspection, allowed]),
           (   assertion(verdict_rule(_, _, action(Action), _)),
               assertion(action_label(Action, _))
           )).

test(knowledge_base_source_has_group_comments) :-
    project_file('src/knowledge_base.pl', Path),
    read_file_to_string(Path, Source, [encoding(utf8)]),
    forall(member(Header,
                  ["% P01–P10.", "% P11–P15.", "% P16–P22.", "% P23–P27.",
                   "% P28–P33.", "% P34–P39.", "% P40–P52.",
                   "% V01–V03", "% V04–V06", "% V07, V08."]),
           assertion(sub_string(Source, _, _, _, Header))).

:- end_tests(rules_structure).
