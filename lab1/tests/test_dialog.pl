:- encoding(utf8).

:- use_module('../src/inference', [current_answer/2]).
:- use_module(fixtures).
:- use_module(dialog_support).

:- begin_tests(dialog).

clean_dialog(Inserts, Text) :-
    clean_answers(Answers),
    dialog_input(Answers, Inserts, Text).

test(first_question_is_printed) :-
    clean_dialog([], Text),
    run_dialog(Text, Output),
    assertion(sub_string(Output, _, _, _, "Категория транспортного средства")).

test(clean_inspection_runs_to_the_end) :-
    clean_dialog([], Body),
    string_concat(Body, "нет\n", Text),
    run_dialog(Text, Output),
    assertion(sub_string(Output, _, _, _, "допущен к эксплуатации")),
    assertion(sub_string(Output, _, _, _, "эксплуатация разрешена")),
    assertion(sub_string(Output, _, _, _, "Работа завершена.")).

test(all_28_questions_are_asked_for_petrol_only_27) :-
    clean_dialog([], Body),
    string_concat(Body, "нет\n", Text),
    run_dialog(Text, Output),
    assertion(sub_string(Output, _, _, _, "Содержание CO")),
    assertion(sub_string(Output, _, _, _, "Содержание CH")),
    assertion(\+ sub_string(Output, _, _, _, "Дымность")).

test(electric_car_is_not_asked_about_exhaust) :-
    clean_answers(Base),
    with_answers([fuel-electric], Base, A1),
    without_answers([co, ch], A1, Answers),
    dialog_input(Answers, [], Body),
    string_concat(Body, "нет\n", Text),
    run_dialog(Text, Output),
    assertion(\+ sub_string(Output, _, _, _, "Содержание CO")),
    assertion(\+ sub_string(Output, _, _, _, "Дымность")),
    assertion(sub_string(Output, _, _, _, "допущен к эксплуатации")).

test(diesel_car_is_asked_about_smoke) :-
    clean_answers(Base),
    with_answers([fuel-diesel, smoke-1.0], Base, A1),
    without_answers([co, ch], A1, Answers),
    dialog_input(Answers, [], Body),
    string_concat(Body, "нет\n", Text),
    run_dialog(Text, Output),
    assertion(sub_string(Output, _, _, _, "Дымность")),
    assertion(\+ sub_string(Output, _, _, _, "Содержание CO")).

test(invalid_choice_is_rejected_and_question_repeated) :-
    clean_dialog([category-"грузовик"], Body),
    string_concat(Body, "нет\n", Text),
    run_dialog(Text, Output),
    assertion(sub_string(Output, _, _, _, "Недопустимое значение")),
    assertion(sub_string(Output, _, _, _, "допущен к эксплуатации")).

test(out_of_range_number_is_rejected_and_question_repeated) :-
    clean_dialog([brake_force-"1.5", brake_force-"минус"], Body),
    string_concat(Body, "нет\n", Text),
    run_dialog(Text, Output),
    findall(x, sub_string(Output, _, _, _, "Недопустимое значение"), Rejections),
    assertion(length(Rejections, 2)),
    assertion(sub_string(Output, _, _, _, "допущен к эксплуатации")).

test(required_answer_cannot_be_unknown) :-
    clean_dialog([year-"неизвестно"], Body),
    string_concat(Body, "нет\n", Text),
    run_dialog(Text, Output),
    assertion(sub_string(Output, _, _, _, "обязателен")),
    assertion(sub_string(Output, _, _, _, "допущен к эксплуатации")).

test(unknown_is_accepted_for_optional_features) :-
    clean_answers(Base),
    with_answers([brake_force-unknown], Base, Answers),
    dialog_input(Answers, [], Body),
    string_concat(Body, "нет\n", Text),
    run_dialog(Text, Output),
    assertion(sub_string(Output, _, _, _, "Не определены признаки")),
    assertion(sub_string(Output, _, _, _, "Удельная тормозная сила")).

test(input_is_normalized) :-
    clean_dialog([category="  М1  ", brake_force="0,8"], Body),
    string_concat(Body, "нет\n", Text),
    run_dialog(Text, Output),
    assertion(\+ sub_string(Output, _, _, _, "Недопустимое значение")),
    assertion(sub_string(Output, _, _, _, "допущен к эксплуатации")).

test(latin_atoms_are_accepted_as_answers) :-
    clean_answers(Base),
    with_answers([parking_brake-weak], Base, Answers),
    dialog_input(Answers, [parking_brake-"weak"], Body),
    string_concat(Body, "нет\n", Text),
    run_dialog(Text, Output),
    assertion(sub_string(Output, _, _, _, "P07")).

test(end_of_input_mid_inspection_is_handled) :-
    run_dialog("м1\n2015\n", Output),
    assertion(sub_string(Output, _, _, _, "Ввод завершён")),
    assertion(\+ sub_string(Output, _, _, _, "Результат осмотра")).

test(empty_input_is_handled) :-
    run_dialog("", Output),
    assertion(sub_string(Output, _, _, _, "Ввод завершён")).

test(bad_next_action_answer_is_repeated) :-
    clean_dialog([], Body),
    string_concat(Body, "может быть\nнет\n", Text),
    run_dialog(Text, Output),
    assertion(sub_string(Output, _, _, _, "Введите «да» или «нет»")).

test(two_inspections_do_not_share_answers) :-
    clean_dialog([], First),
    clean_answers(Base),
    with_answers([wheel_fasteners-missing], Base, Second0),
    dialog_input(Second0, [], Second),
    atomic_list_concat([First, "да\n", Second, "нет\n"], Text),
    run_dialog(Text, Output),
    assertion(sub_string(Output, _, _, _, "Работа завершена.")),
    % В отчёте первого осмотра нет замечаний, в отчёте второго — только P27.
    sub_string(Output, Before, _, After, "Начать новый осмотр"),
    sub_string(Output, 0, Before, _, FirstPart),
    sub_string(Output, _, After, 0, SecondPart),
    !,
    assertion(\+ sub_string(FirstPart, _, _, _, "P27")),
    assertion(sub_string(SecondPart, _, _, _, "P27")),
    assertion(sub_string(SecondPart, _, _, _, "не допущен к эксплуатации")),
    assertion(\+ current_answer(_, _)).

test(report_shows_group_rule_number_severity_and_features) :-
    clean_answers(Base),
    with_answers([steering_play-34], Base, Answers),
    dialog_input(Answers, [], Body),
    string_concat(Body, "нет\n", Text),
    run_dialog(Text, Output),
    assertion(sub_string(Output, _, _, _, "Рулевое управление")),
    assertion(sub_string(Output, _, _, _, "P13")),
    assertion(sub_string(Output, _, _, _, "критическая")),
    assertion(sub_string(Output, _, _, _, "Суммарный люфт рулевого управления, °: 34")),
    assertion(sub_string(Output, _, _, _, "V01")),
    assertion(sub_string(Output, _, _, _, "V04")),
    assertion(sub_string(Output, _, _, _, "эксплуатация запрещена")).

test(reference_notice_is_printed_in_every_report) :-
    clean_dialog([], Body),
    string_concat(Body, "нет\n", Text),
    run_dialog(Text, Output),
    assertion(sub_string(Output, _, _, _, "носит справочный характер и не заменяет технический осмотр")).

:- end_tests(dialog).
