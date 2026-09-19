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
