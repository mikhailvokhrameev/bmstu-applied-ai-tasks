:- encoding(utf8).

:- module(project_paths, [project_file/2]).

:- use_module(library(filesex)).

/** <module> Пути к файлам проекта для тестов

Тесты открывают исходники и документы по пути от корня проекта, поэтому
результат не зависит от каталога, из которого запущен swipl.
*/

:- dynamic root_dir/1.

% tests/project_paths.pl лежит в <корень>/tests.
:- prolog_load_context(directory, Dir),
   file_directory_name(Dir, Root),
   assertz(root_dir(Root)).

%! project_file(+Relative, -Absolute) is det.
project_file(Relative, Absolute) :-
    root_dir(Root),
    directory_file_path(Root, Relative, Absolute).
