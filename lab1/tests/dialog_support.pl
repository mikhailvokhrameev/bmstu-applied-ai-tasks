:- encoding(utf8).

:- module(dialog_support, [
    dialog_input/3,
    run_dialog/2,
    report_output/2
]).

:- use_module('../src/domain').
:- use_module('../src/expert_system').
:- use_module(library(lists)).

/** <module> Вспомогательные предикаты для проверки диалога */

%! dialog_input(+Answers, +Inserts, -Text:string) is det.
%
%  Text — ввод пользователя для осмотра с ответами Answers. Inserts —
%  список особых строк:
%    Key-Line   строка Line подаётся перед корректным ответом на вопрос Key
%               (проверка повторного запроса);
%    Key=Line   строка Line подаётся вместо корректного ответа на вопрос Key
%               (проверка разбора ввода).
dialog_input(Answers, Inserts, Text) :-
    memberchk(fuel-Fuel, Answers),
    findall(Line,
            (   question(Key, _, _),
                question_applies(Key, Fuel),
                (   member(Key-Line, Inserts)
                ;   valid_line(Key, Answers, Inserts, Line)
                )
            ),
            Lines),
    atomic_list_concat(Lines, '\n', Atom),
    atom_concat(Atom, '\n', WithNewline),
    atom_string(WithNewline, Text).

valid_line(Key, Answers, Inserts, Line) :-
    (   member(Key=Replacement, Inserts)
    ->  Line = Replacement
    ;   memberchk(Key-Value, Answers),
        value_text(Key, Value, Line)
    ).

%! run_dialog(+Input:string, -Output:string) is det.
run_dialog(Input, Output) :-
    open_string(Input, In),
    current_input(Old),
    with_output_to(string(Output),
        setup_call_cleanup(
            set_input(In),
            run_session,
            ( set_input(Old), close(In) ))).

%! report_output(+Report, -Output:string) is det.
report_output(Report, Output) :-
    with_output_to(string(Output), print_report(Report)).
