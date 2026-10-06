:- encoding(utf8).

:- module(domain, [
    question/3,
    known_question_key/1,
    required_key/1,
    fuel_specific/2,
    question_applies/2,
    valid_value/2,
    validate_answers/2,
    answer_hint/2,
    key_label/2,
    value_label/3,
    value_text/3,
    group_label/2,
    severity_label/2,
    verdict_label/2,
    action_label/2
]).

:- use_module(library(lists)).
:- use_module(library(apply)).

/** <module> Предметная модель экспертной системы технического осмотра

Модуль описывает входные признаки (28 штук), допустимые значения и диапазоны,
русские подписи для диалога и объяснений, а также проверку допустимости
данных, переданных программным вызовом (п. 5.1.3, 5.2.1 ТЗ).
*/

% Признаки перечислены в порядке диалога. Kind описывает допустимые значения:
%   choice(Values)      — одно из перечисленных значений;
%   int_range(Min,Max)  — целое число в пределах Min..Max включительно;
%   num_range(Min,Max)  — число в пределах Min..Max включительно.

% Общие сведения.
question(category, "Категория транспортного средства",
         choice([m1, m2_m3, n1, n2_n3])).
question(year, "Год выпуска", int_range(1950, 2026)).
question(fuel, "Тип топлива", choice([petrol, diesel, gas, electric])).

% Тормозная система.
question(brake_force, "Удельная тормозная сила рабочей тормозной системы",
         num_range(0, 1.2)).
question(brake_imbalance, "Неравномерность тормозных сил колёс оси, %",
         num_range(0, 100)).
question(parking_brake, "Стояночная тормозная система",
         choice([holds, weak, fails])).
question(brake_leak, "Герметичность тормозного привода",
         choice([tight, minor, major])).

% Рулевое управление.
question(steering_play, "Суммарный люфт рулевого управления, °",
         num_range(0, 90)).
question(steering_joints, "Шарниры и тяги рулевого привода",
         choice([ok, worn, broken])).

% Внешние световые приборы.
question(headlights, "Фары ближнего и дальнего света",
         choice([ok, one_faulty, not_working])).
question(headlight_aim, "Регулировка фар", choice([ok, misaligned])).
question(signal_lights, "Сигнальные фонари",
         choice([ok, partial, not_working])).
question(reflectors, "Световозвращатели", choice([present, missing])).

% Шины и колёса.
question(tread_depth, "Глубина протектора шин, мм", num_range(0, 15)).
question(tire_condition, "Состояние шин",
         choice([ok, damaged, cord_visible])).
question(wheel_fasteners, "Крепление колёс", choice([ok, missing])).

% Приборы обзора и стеклоочистители.
question(windshield, "Ветровое стекло",
         choice([intact, chips, driver_crack])).
question(wipers, "Стеклоочистители", choice([ok, worn, not_working])).
question(mirrors, "Зеркала заднего вида", choice([ok, damaged, missing])).

% Экологические показатели (спрашиваются по типу топлива).
question(co, "Содержание CO в отработавших газах, %", num_range(0, 10)).
question(ch, "Содержание CH в отработавших газах, ppm", num_range(0, 5000)).
question(smoke, "Дымность отработавших газов, 1/м", num_range(0, 10)).

% Прочие элементы конструкции и обязательная комплектация.
question(seat_belts, "Ремни безопасности", choice([ok, faulty, missing])).
question(first_aid_kit, "Аптечка", choice([yes, no])).
question(fire_extinguisher, "Огнетушитель", choice([yes, no])).
question(warning_triangle, "Знак аварийной остановки", choice([yes, no])).
question(structure, "Несущие элементы конструкции",
         choice([ok, corrosion, destroyed])).
question(fluid_leaks, "Утечки эксплуатационных жидкостей",
         choice([none, traces, dripping, fuel])).

known_question_key(Key) :-
    question(Key, _, _).

% От категории, года и типа топлива зависят пороги и набор вопросов, поэтому
% ответ «неизвестно» для них недопустим.
required_key(category).
required_key(year).
required_key(fuel).

% Признаки, которые спрашиваются только для указанных типов топлива.
fuel_specific(co, [petrol, gas]).
fuel_specific(ch, [petrol, gas]).
fuel_specific(smoke, [diesel]).

%! question_applies(+Key, +Fuel) is semidet.
%
%  Истинно, если признак Key нужно спрашивать при типе топлива Fuel.
question_applies(Key, Fuel) :-
    (   fuel_specific(Key, Fuels)
    ->  memberchk(Fuel, Fuels)
    ;   true
    ).

%! valid_value(+Key, +Value) is semidet.
valid_value(Key, unknown) :-
    known_question_key(Key),
    \+ required_key(Key).
valid_value(Key, Value) :-
    question(Key, _, Kind),
    valid_kind_value(Kind, Value).

valid_kind_value(choice(Allowed), Value) :-
    memberchk(Value, Allowed).
valid_kind_value(int_range(Min, Max), Value) :-
    integer(Value),
    Value >= Min,
    Value =< Max.
valid_kind_value(num_range(Min, Max), Value) :-
    number(Value),
    Value >= Min,
    Value =< Max.

%! validate_answers(+Answers, -Errors:list(string)) is det.
%
%  Проверка программного интерфейса до вывода: формат пар, известные
%  ключи, допустимость значений, повторы и наличие обязательных признаков.
validate_answers(Answers, Errors) :-
    (   is_list(Answers)
    ->  findall(Error, answer_error(Answers, Error), Raw),
        list_to_set(Raw, Errors)
    ;   Errors = ["Набор ответов должен быть списком пар Ключ-Значение."]
    ).

answer_error(Answers, Message) :-
    member(Item, Answers),
    \+ Item = _-_,
    format(string(Message), "Элемент ~q не является парой Ключ-Значение.", [Item]).
answer_error(Answers, Message) :-
    member(Key-_, Answers),
    \+ known_question_key(Key),
    format(string(Message), "Неизвестный входной признак: ~q.", [Key]).
answer_error(Answers, Message) :-
    member(Key-Value, Answers),
    known_question_key(Key),
    \+ valid_value(Key, Value),
    (   Value == unknown
    ->  format(string(Message),
               "Признак ~q обязателен: значение unknown недопустимо.", [Key])
    ;   format(string(Message),
               "Недопустимое значение ~q для признака ~q.", [Value, Key])
    ).
answer_error(Answers, Message) :-
    member(Key-_, Answers),
    include(pair_has_key(Key), Answers, Matches),
    length(Matches, Count),
    Count > 1,
    format(string(Message), "Признак ~q указан несколько раз.", [Key]).
answer_error(Answers, Message) :-
    required_key(Key),
    \+ memberchk(Key-_, Answers),
    format(string(Message), "Не указан обязательный признак ~q.", [Key]).

pair_has_key(Key, Key-_).

%! answer_hint(+Key, -Hint:string) is det.
%
%  Подсказка о допустимых ответах для диалога.
answer_hint(Key, Hint) :-
    question(Key, _, Kind),
    kind_hint(Key, Kind, Base),
    (   required_key(Key)
    ->  Hint = Base
    ;   string_concat(Base, " / неизвестно", Hint)
    ).

kind_hint(Key, choice(Values), Hint) :-
    maplist(value_text(Key), Values, Labels),
    atomic_list_concat(Labels, ' / ', Atom),
    atom_string(Atom, Hint).
kind_hint(_, int_range(Min, Max), Hint) :-
    format(string(Hint), "целое число от ~w до ~w", [Min, Max]).
kind_hint(_, num_range(Min, Max), Hint) :-
    format(string(Hint), "число от ~w до ~w", [Min, Max]).

%! key_label(+Key, -Text) is det.
%  Подпись признака в объяснениях совпадает с текстом вопроса.
key_label(Key, Text) :-
    question(Key, Text, _).

%! value_text(+Key, +Value, -Text:string) is det.
%  Русская подпись значения; для чисел и незнакомых значений — само значение.
value_text(Key, Value, Text) :-
    (   value_label(Key, Value, Label)
    ->  Text = Label
    ;   format(string(Text), "~w", [Value])
    ).

value_label(_, unknown, "неизвестно").
value_label(Key, yes, "да") :- yes_no_key(Key).
value_label(Key, no, "нет") :- yes_no_key(Key).
value_label(category, m1, "M1").
value_label(category, m2_m3, "M2-M3").
value_label(category, n1, "N1").
value_label(category, n2_n3, "N2-N3").
value_label(fuel, petrol, "бензин").
value_label(fuel, diesel, "дизель").
value_label(fuel, gas, "газ").
value_label(fuel, electric, "электро").
value_label(parking_brake, holds, "удерживает").
value_label(parking_brake, weak, "слабо").
value_label(parking_brake, fails, "не удерживает").
value_label(brake_leak, tight, "герметичен").
value_label(brake_leak, minor, "малая утечка").
value_label(brake_leak, major, "значительная утечка").
value_label(steering_joints, ok, "исправны").
value_label(steering_joints, worn, "изношены").
value_label(steering_joints, broken, "разрушены").
value_label(headlights, ok, "исправны").
value_label(headlights, one_faulty, "одна неисправна").
value_label(headlights, not_working, "не работают").
value_label(headlight_aim, ok, "в норме").
value_label(headlight_aim, misaligned, "нарушена").
value_label(signal_lights, ok, "исправны").
value_label(signal_lights, partial, "частично").
value_label(signal_lights, not_working, "не работают").
value_label(reflectors, present, "на месте").
value_label(reflectors, missing, "отсутствуют").
value_label(tire_condition, ok, "норма").
value_label(tire_condition, damaged, "повреждены").
value_label(tire_condition, cord_visible, "виден корд").
value_label(wheel_fasteners, ok, "в норме").
value_label(wheel_fasteners, missing, "нет крепёжных элементов").
value_label(windshield, intact, "целое").
value_label(windshield, chips, "сколы").
value_label(windshield, driver_crack, "трещина в зоне водителя").
value_label(wipers, ok, "исправны").
value_label(wipers, worn, "изношены").
value_label(wipers, not_working, "не работают").
value_label(mirrors, ok, "исправны").
value_label(mirrors, damaged, "повреждены").
value_label(mirrors, missing, "отсутствуют").
value_label(seat_belts, ok, "исправны").
value_label(seat_belts, faulty, "неисправны").
value_label(seat_belts, missing, "отсутствуют").
value_label(structure, ok, "норма").
value_label(structure, corrosion, "коррозия без потери несущей способности").
value_label(structure, destroyed, "разрушены").
value_label(fluid_leaks, none, "нет").
value_label(fluid_leaks, traces, "следы").
value_label(fluid_leaks, dripping, "капельные").
value_label(fluid_leaks, fuel, "топливо").

yes_no_key(first_aid_kit).
yes_no_key(fire_extinguisher).
yes_no_key(warning_triangle).

% Классы результата осмотра (п. 5.1.11 ТЗ).
group_label(brakes, "Тормозная система").
group_label(steering, "Рулевое управление").
group_label(lighting, "Внешние световые приборы и световозвращатели").
group_label(tires, "Шины и колёса").
group_label(visibility, "Приборы обзора и стеклоочистители").
group_label(ecology, "Экологические показатели").
group_label(other, "Прочие элементы конструкции и обязательная комплектация").

severity_label(critical, "критическая").
severity_label(major, "существенная").
severity_label(minor, "незначительная").

verdict_label(not_admitted, "не допущен к эксплуатации").
verdict_label(admitted_with_remarks,
              "допущен с замечаниями, требуется повторный осмотр").
verdict_label(admitted, "допущен к эксплуатации").

action_label(prohibited, "эксплуатация запрещена").
action_label(fix_before_reinspection,
             "устранить несоответствия до повторного осмотра").
action_label(allowed, "эксплуатация разрешена").
