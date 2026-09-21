:- encoding(utf8).

:- use_module('../src/inference').
:- use_module(fixtures).

:- begin_tests(inference).

test(clean_car_is_admitted) :-
    clean_answers(Answers),
    inspect_answers(Answers, Report),
    assertion(Report.status == ok),
    assertion(Report.verdict == admitted),
    assertion(Report.action == allowed),
    assertion(Report.findings == []),
    assertion(Report.verdict_rules == [v03, v06]),
    assertion(Report.unknown == []),
    assertion(Report.diagnostics == []).

test(critical_finding_gives_not_admitted) :-
    clean_answers(Base),
    with_answers([brake_force-0.4], Base, Answers),
    inspect_answers(Answers, Report),
    assertion(Report.status == ok),
    assertion(Report.verdict == not_admitted),
    assertion(Report.action == prohibited),
    assertion(Report.verdict_rules == [v01, v04]),
    report_ids(Report, Ids),
    assertion(Ids == [p01]).

test(major_finding_gives_admitted_with_remarks) :-
    clean_answers(Base),
    with_answers([brake_leak-minor], Base, Answers),
    inspect_answers(Answers, Report),
    assertion(Report.verdict == admitted_with_remarks),
    assertion(Report.action == fix_before_reinspection),
    assertion(Report.verdict_rules == [v02, v05]).

test(minor_finding_alone_still_admits) :-
    clean_answers(Base),
    with_answers([brake_force-0.6], Base, Answers),
    inspect_answers(Answers, Report),
    assertion(Report.verdict == admitted),
    assertion(Report.action == allowed),
    assertion(Report.verdict_rules == [v03, v06]),
    report_ids(Report, Ids),
    assertion(Ids == [p02]).

test(critical_wins_over_major_and_minor) :-
    clean_answers(Base),
    with_answers([brake_force-0.4, brake_leak-minor, brake_imbalance-16],
                 Base, Answers),
    inspect_answers(Answers, Report),
    assertion(Report.verdict == not_admitted),
    report_ids(Report, Ids),
    assertion(Ids == [p01, p03, p10]).

test(finding_carries_group_severity_text_and_evidence) :-
    clean_answers(Base),
    with_answers([brake_force-0.4], Base, Answers),
    inspect_answers(Answers, Report),
    [Finding] = Report.findings,
    assertion(Finding.group == brakes),
    assertion(Finding.severity == critical),
    assertion(string(Finding.text)),
    assertion(memberchk(brake_force-0.4, Finding.evidence)),
    assertion(memberchk(category-m1, Finding.evidence)).

test(unknown_answer_blocks_admission) :-
    clean_answers(Base),
    with_answers([brake_force-unknown], Base, Answers),
    inspect_answers(Answers, Report),
    assertion(Report.status == insufficient_data),
    assertion(Report.verdict == none),
    assertion(Report.action == none),
    assertion(Report.unknown == [brake_force]),
    assertion(Report.verdict_rules == [v07]),
    assertion(Report.diagnostics \== []).

test(missing_answer_is_treated_as_unknown) :-
    clean_answers(Base),
    without_answers([brake_force], Base, Answers),
    inspect_answers(Answers, Report),
    assertion(Report.status == insufficient_data),
    assertion(Report.unknown == [brake_force]).

test(unknown_with_only_minor_findings_is_insufficient) :-
    clean_answers(Base),
    with_answers([brake_force-unknown, brake_imbalance-16], Base, Answers),
    inspect_answers(Answers, Report),
    assertion(Report.status == insufficient_data),
    assertion(Report.verdict == none),
    report_ids(Report, Ids),
    assertion(Ids == [p03]).

test(critical_finding_is_issued_despite_unknown_data) :-
    clean_answers(Base),
    with_answers([brake_force-unknown, brake_leak-major], Base, Answers),
    inspect_answers(Answers, Report),
    assertion(Report.status == ok),
    assertion(Report.verdict == not_admitted),
    assertion(Report.action == prohibited),
    assertion(Report.unknown == [brake_force]),
    assertion(Report.diagnostics \== []).

test(electric_car_is_not_asked_about_exhaust) :-
    clean_answers(Base),
    with_answers([fuel-electric], Base, A1),
    without_answers([co, ch], A1, Answers),
    inspect_answers(Answers, Report),
    assertion(Report.status == ok),
    assertion(Report.verdict == admitted),
    assertion(Report.unknown == []).

test(diesel_needs_smoke_not_co_and_ch) :-
    clean_answers(Base),
    with_answers([fuel-diesel, smoke-1.0], Base, A1),
    without_answers([co, ch], A1, Answers),
    inspect_answers(Answers, Report),
    assertion(Report.status == ok),
    assertion(Report.verdict == admitted),
    assertion(Report.unknown == []).

test(diesel_without_smoke_is_incomplete) :-
    clean_answers(Base),
    with_answers([fuel-diesel], Base, A1),
    without_answers([co, ch], A1, Answers),
    inspect_answers(Answers, Report),
    assertion(Report.status == insufficient_data),
    assertion(Report.unknown == [smoke]).

test(contradictory_input_gives_diagnostic_and_no_verdict) :-
    clean_answers(Base),
    with_answers([fuel-diesel, co-0.3], Base, Answers),
    inspect_answers(Answers, Report),
    assertion(Report.status == contradiction),
    assertion(Report.verdict == none),
    assertion(Report.action == none),
    assertion(Report.findings == []),
    assertion(Report.verdict_rules == [v08]),
    assertion(Report.diagnostics \== []).

test(invalid_value_gives_invalid_input_status) :-
    inspect_answers([category-m1, year-2015, fuel-petrol, brake_force-9], Report),
    assertion(Report.status == invalid_input),
    assertion(Report.verdict == none),
    assertion(Report.findings == []),
    assertion(Report.diagnostics \== []).

test(missing_required_key_gives_invalid_input_status) :-
    inspect_answers([brake_force-0.8], Report),
    assertion(Report.status == invalid_input).

test(answers_are_cleared_after_inspection) :-
    clean_answers(Answers),
    inspect_answers(Answers, _),
    assertion(\+ current_answer(_, _)).

test(invalid_call_also_clears_previous_state) :-
    set_answers([brake_leak-major]),
    inspect_answers([brake_force-9], Report),
    assertion(Report.status == invalid_input),
    assertion(\+ current_answer(_, _)).

test(inspect_current_uses_stored_answers) :-
    clean_answers(Answers),
    set_answers(Answers),
    inspect_current(Report),
    clear_answers,
    assertion(Report.verdict == admitted),
    assertion(\+ current_answer(_, _)).

:- end_tests(inference).
