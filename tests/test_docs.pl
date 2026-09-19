:- encoding(utf8).

:- use_module(project_paths).
:- use_module(library(readutil)).

% Испытание 13 (п. 6.1, 6.2 ТЗ): комментарии в исходном тексте и комплект документации.
:- begin_tests(docs).

file_text(Relative, Text) :-
    project_file(Relative, Path),
    read_file_to_string(Path, Text, [encoding(utf8)]).

test(t13_documentation_kit_is_present) :-
    forall(member(File,
                  ['docs/tz_car_inspection_v1.0.docx',
                   'README.md',
                   'docs/report_draft.md',
                   'docs/control_examples.md',
                   'docs/classification_model.md',
                   'docs/requirements_traceability.md',
                   'docs/tester_handoff.md']),
           (   project_file(File, Path),
               assertion(exists_file(Path)),
               size_file(Path, Size),
               assertion(Size > 500)
           )).

test(t13_readme_has_the_start_command_and_test_command) :-
    file_text('README.md', Text),
    assertion(sub_string(Text, _, _, _, "swipl -q -s src/expert_system.pl -g start -t halt")),
    assertion(sub_string(Text, _, _, _, "scripts/run_tests.sh")),
    assertion(sub_string(Text, _, _, _, "SWI-Prolog 10.0.2")).

test(t13_control_examples_have_expected_and_actual_results) :-
    file_text('docs/control_examples.md', Text),
    forall(member(Part,
                  ["Ожидаемый результат", "Фактический результат",
                   "Проверка разработчиков", "Приёмочный результат",
                   "Проверка базы знаний на конфликты"]),
           assertion(sub_string(Text, _, _, _, Part))),
    assertion(\+ sub_string(Text, _, _, _, "НЕ ПРОЙДЕНО")).

test(t13_traceability_mentions_every_requirement) :-
    file_text('docs/requirements_traceability.md', Text),
    forall(member(Point,
                  ["5.1.1", "5.1.2", "5.1.3", "5.1.4", "5.1.5", "5.1.6",
                   "5.1.7", "5.1.8", "5.1.9", "5.1.10", "5.1.11",
                   "5.2.1", "5.2.2", "5.2.3", "5.2.4", "5.2.5", "5.2.6",
                   "5.5.1", "5.5.2", "5.5.3", "5.5.4",
                   "5.8.1", "5.8.2", "5.8.3", "5.8.4", "6.1", "6.2"]),
           assertion(sub_string(Text, _, _, _, Point))).

test(t13_every_source_file_has_a_module_comment) :-
    forall(member(File,
                  ['src/domain.pl', 'src/thresholds.pl', 'src/consistency.pl',
                   'src/knowledge_base.pl', 'src/inference.pl',
                   'src/expert_system.pl']),
           (   file_text(File, Text),
               assertion(sub_string(Text, _, _, _, "/** <module>"))
           )).

test(t13_report_draft_has_the_expected_sections) :-
    file_text('docs/report_draft.md', Text),
    forall(member(Heading,
                  ["## 1. Постановка задачи", "## 2. Предметная область",
                   "## 3. Классификация результата", "## 4. База знаний",
                   "## 5. Неполные и противоречивые данные",
                   "## 6. Диалог и объяснение", "## 7. Тестирование",
                   "## 8. Ограничения"]),
           assertion(sub_string(Text, _, _, _, Heading))).

:- end_tests(docs).
