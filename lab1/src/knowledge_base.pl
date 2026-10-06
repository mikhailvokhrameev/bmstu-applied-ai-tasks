:- encoding(utf8).

:- module(knowledge_base, [
    rule_group/1,
    production_rule/5,
    verdict_rule/4
]).

/** <module> База знаний технического осмотра автомобилей

Правила хранятся фактами двух видов (п. 5.8.1 ТЗ):

  * verdict_rule(Id, Premises, Result, Text) — слой 2, V01–V08:
    «состояние осмотра → заключение и рекомендуемое действие».
    Состояние — множество флагов critical, major, minor, complete,
    contradiction. Правила V01–V03, V07, V08 взаимоисключающи по построению:
    в каждом состоянии срабатывает ровно одно из них.
  * production_rule(Id, Group, Severity, Conditions, Text) — слой 1, P01–P52:
    «признаки → несоответствие» с группой и степенью критичности.

Условия правил слоя 1:
  eq(Key, Value)          ответ равен значению;
  in(Key, [Value, ...])   ответ — одно из значений;
  ge(Key, N), lt(Key, N)  число из ответа не меньше / меньше N;
  lt_t, le_t, gt_t, ge_t (Key, Name)
                          число из ответа сравнивается с порогом Name из
                          модуля thresholds (значение по категории или году).
Полосы правил одного признака не пересекаются, поэтому одно значение не даёт
двух разных степеней критичности; это проверяет tests/conflict_check.pl.
Факты rule_group/1 и служебные предикаты в подсчёт правил не входят.
*/

rule_group(brakes).
rule_group(steering).
rule_group(lighting).
rule_group(tires).
rule_group(visibility).
rule_group(ecology).
rule_group(other).

% ============================================================================
% СЛОЙ 2. Правила заключения V01–V08.
% ============================================================================

% V01–V03, V07, V08. Состояние осмотра → итоговое заключение или статус.
verdict_rule(v01, [has(critical), lacks(contradiction)],
    verdict(not_admitted),
    "Есть критическое несоответствие: транспортное средство не допускается независимо от состояния остальных узлов (п. 5.2.5 ТЗ).").
verdict_rule(v02, [has(major), lacks(critical), has(complete), lacks(contradiction)],
    verdict(admitted_with_remarks),
    "Есть существенные несоответствия и нет критических, данные полны: допуск с замечаниями (п. 5.2.6 ТЗ).").
verdict_rule(v03, [lacks(critical), lacks(major), has(complete), lacks(contradiction)],
    verdict(admitted),
    "Несоответствий нет или они только незначительные, данные полны: допуск (п. 5.2.6 ТЗ).").

% V04–V06. Заключение → рекомендуемое действие владельцу.
verdict_rule(v04, [verdict(not_admitted)],
    action(prohibited),
    "Не допущен: эксплуатация запрещена.").
verdict_rule(v05, [verdict(admitted_with_remarks)],
    action(fix_before_reinspection),
    "Допущен с замечаниями: устранить несоответствия до повторного осмотра.").
verdict_rule(v06, [verdict(admitted)],
    action(allowed),
    "Допущен: эксплуатация разрешена.").

% V07, V08. Диагностика неполных и противоречивых данных (п. 5.1.9 ТЗ).
verdict_rule(v07, [lacks(critical), lacks(complete), lacks(contradiction)],
    status(insufficient_data),
    "Критических несоответствий нет, но часть признаков неизвестна: допускающее заключение не формируется.").
verdict_rule(v08, [has(contradiction)],
    status(contradiction),
    "Входные данные противоречивы: заключение не формируется.").

% ============================================================================
% СЛОЙ 1. Правила несоответствий P01–P52.
% ============================================================================

% P01–P10. Тормозная система.
production_rule(p01, brakes, critical,
    [lt_t(brake_force, brake_force_min)],
    "Удельная тормозная сила ниже минимально допустимой для категории ТС.").
production_rule(p02, brakes, minor,
    [ge_t(brake_force, brake_force_min), lt_t(brake_force, brake_force_warn)],
    "Малый запас удельной тормозной силы до минимально допустимой.").
production_rule(p03, brakes, minor,
    [gt_t(brake_imbalance, brake_imbalance_warn), le_t(brake_imbalance, brake_imbalance_max)],
    "Неравномерность тормозных сил колёс оси приближается к допустимому пределу.").
production_rule(p04, brakes, major,
    [gt_t(brake_imbalance, brake_imbalance_max), le_t(brake_imbalance, brake_imbalance_crit)],
    "Неравномерность тормозных сил колёс оси выше допустимой.").
production_rule(p05, brakes, critical,
    [gt_t(brake_imbalance, brake_imbalance_crit)],
    "Неравномерность тормозных сил колёс оси выше критической.").
production_rule(p06, brakes, critical,
    [eq(parking_brake, fails)],
    "Стояночная тормозная система не удерживает транспортное средство.").
production_rule(p07, brakes, major,
    [eq(parking_brake, weak), in(category, [m1, m2_m3, n1])],
    "Стояночная тормозная система удерживает слабо.").
production_rule(p08, brakes, critical,
    [eq(parking_brake, weak), eq(category, n2_n3)],
    "Стояночная тормозная система удерживает слабо: для тяжёлых грузовых ТС (N2–N3) это критическое несоответствие.").
production_rule(p09, brakes, critical,
    [eq(brake_leak, major)],
    "Значительная утечка из тормозного привода.").
production_rule(p10, brakes, major,
    [eq(brake_leak, minor)],
    "Малая утечка из тормозного привода.").

% P11–P15. Рулевое управление.
production_rule(p11, steering, minor,
    [gt_t(steering_play, steering_play_warn), le_t(steering_play, steering_play_max)],
    "Суммарный люфт рулевого управления приближается к предельному (80–100 % предела).").
production_rule(p12, steering, major,
    [gt_t(steering_play, steering_play_max), le_t(steering_play, steering_play_crit)],
    "Суммарный люфт рулевого управления выше предельного.").
production_rule(p13, steering, critical,
    [gt_t(steering_play, steering_play_crit)],
    "Суммарный люфт рулевого управления выше критического.").
production_rule(p14, steering, major,
    [eq(steering_joints, worn)],
    "Шарниры и тяги рулевого привода изношены.").
production_rule(p15, steering, critical,
    [eq(steering_joints, broken)],
    "Шарниры или тяги рулевого привода разрушены.").

% P16–P22. Внешние световые приборы и световозвращатели.
production_rule(p16, lighting, critical,
    [eq(headlights, not_working)],
    "Фары ближнего и дальнего света не работают.").
production_rule(p17, lighting, major,
    [eq(headlights, one_faulty)],
    "Неисправна одна из фар ближнего или дальнего света.").
production_rule(p18, lighting, major,
    [eq(headlight_aim, misaligned)],
    "Регулировка фар нарушена.").
production_rule(p19, lighting, critical,
    [eq(signal_lights, not_working)],
    "Сигнальные фонари не работают.").
production_rule(p20, lighting, major,
    [eq(signal_lights, partial)],
    "Сигнальные фонари работают частично.").
production_rule(p21, lighting, minor,
    [eq(reflectors, missing), in(category, [m1, n1])],
    "Световозвращатели отсутствуют (для M1 и N1 — незначительное несоответствие).").
production_rule(p22, lighting, major,
    [eq(reflectors, missing), in(category, [m2_m3, n2_n3])],
    "Световозвращатели отсутствуют (для M2–M3 и N2–N3 — существенное несоответствие).").

% P23–P27. Шины и колёса.
production_rule(p23, tires, critical,
    [lt_t(tread_depth, tread_min)],
    "Глубина протектора ниже минимально допустимой для категории ТС.").
production_rule(p24, tires, minor,
    [ge_t(tread_depth, tread_min), lt_t(tread_depth, tread_warn)],
    "Малый запас глубины протектора до минимально допустимой.").
production_rule(p25, tires, critical,
    [eq(tire_condition, cord_visible)],
    "На шине виден корд.").
production_rule(p26, tires, major,
    [eq(tire_condition, damaged)],
    "Шины имеют повреждения.").
production_rule(p27, tires, critical,
    [eq(wheel_fasteners, missing)],
    "Отсутствуют крепёжные элементы колёс.").

% P28–P33. Приборы обзора и стеклоочистители.
production_rule(p28, visibility, critical,
    [eq(windshield, driver_crack)],
    "Трещина ветрового стекла в зоне обзора водителя.").
production_rule(p29, visibility, minor,
    [eq(windshield, chips)],
    "Сколы ветрового стекла.").
production_rule(p30, visibility, critical,
    [eq(wipers, not_working)],
    "Стеклоочистители не работают.").
production_rule(p31, visibility, major,
    [eq(wipers, worn)],
    "Стеклоочистители изношены.").
production_rule(p32, visibility, major,
    [eq(mirrors, damaged)],
    "Зеркала заднего вида повреждены.").
production_rule(p33, visibility, critical,
    [eq(mirrors, missing)],
    "Зеркала заднего вида отсутствуют.").

% P34–P39. Экологические показатели. Пределы CO и CH выбирает год выпуска.
production_rule(p34, ecology, major,
    [gt_t(co, co_max)],
    "Содержание CO в отработавших газах выше предельного.").
production_rule(p35, ecology, major,
    [gt_t(ch, ch_max)],
    "Содержание CH в отработавших газах выше предельного.").
production_rule(p36, ecology, major,
    [gt_t(smoke, smoke_max)],
    "Дымность отработавших газов выше предельной.").
production_rule(p37, ecology, minor,
    [gt_t(co, co_warn), le_t(co, co_max)],
    "Содержание CO приближается к предельному (выше 90 % предела).").
production_rule(p38, ecology, minor,
    [gt_t(ch, ch_warn), le_t(ch, ch_max)],
    "Содержание CH приближается к предельному (выше 90 % предела).").
production_rule(p39, ecology, minor,
    [gt_t(smoke, smoke_warn), le_t(smoke, smoke_max)],
    "Дымность приближается к предельной (выше 90 % предела).").

% P40–P52. Прочие элементы конструкции и обязательная комплектация.
production_rule(p40, other, critical,
    [eq(seat_belts, missing), ge(year, 1991)],
    "Ремни безопасности отсутствуют на автомобиле, выпущенном с 1991 года.").
production_rule(p41, other, minor,
    [eq(seat_belts, missing), lt(year, 1991)],
    "Ремни безопасности отсутствуют на автомобиле, выпущенном до 1991 года.").
production_rule(p42, other, major,
    [eq(seat_belts, faulty)],
    "Ремни безопасности неисправны.").
production_rule(p43, other, minor,
    [eq(first_aid_kit, no)],
    "Отсутствует аптечка.").
production_rule(p44, other, minor,
    [eq(fire_extinguisher, no), in(category, [m1, n1])],
    "Отсутствует огнетушитель (для M1 и N1 — незначительное несоответствие).").
production_rule(p45, other, major,
    [eq(fire_extinguisher, no), in(category, [m2_m3, n2_n3])],
    "Отсутствует огнетушитель (для M2–M3 и N2–N3 — существенное несоответствие).").
production_rule(p46, other, minor,
    [eq(warning_triangle, no), in(category, [m1, n1])],
    "Отсутствует знак аварийной остановки (для M1 и N1 — незначительное несоответствие).").
production_rule(p47, other, major,
    [eq(warning_triangle, no), in(category, [m2_m3, n2_n3])],
    "Отсутствует знак аварийной остановки (для M2–M3 и N2–N3 — существенное несоответствие).").
production_rule(p48, other, minor,
    [eq(structure, corrosion)],
    "Коррозия несущих элементов без потери несущей способности.").
production_rule(p49, other, critical,
    [eq(structure, destroyed)],
    "Несущие элементы конструкции разрушены.").
production_rule(p50, other, minor,
    [eq(fluid_leaks, traces)],
    "Следы утечек эксплуатационных жидкостей.").
production_rule(p51, other, major,
    [eq(fluid_leaks, dripping)],
    "Капельные утечки эксплуатационных жидкостей.").
production_rule(p52, other, critical,
    [eq(fluid_leaks, fuel)],
    "Утечка топлива.").
