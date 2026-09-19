:- encoding(utf8).

% Точка входа автоматических проверок. Каждый файл test_*.pl объявляет
% свой блок plunit; run_tests/0 запускает все загруженные блоки.
:- use_module(library(plunit)).
:- consult(test_domain).
