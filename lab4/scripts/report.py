"""Build a factual experiment report from a completed, checked ten-run analysis."""
import argparse
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import sys
from urllib.parse import quote


_here = Path(__file__).resolve()
PROJECT = _here.parent.parent if (_here.parent.parent / 'DELIVERY_MANIFEST.json').is_file() else _here.parents[2]
sys.path.insert(0, str(PROJECT))
from lab4.optimizer.analysis import analyze_run, summarize


class ReportError(ValueError):
    pass


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def markdown_link(path, output, label):
    relative = os.path.relpath(Path(path).resolve(), Path(output).parent.resolve())
    return '[' + label + '](' + quote(Path(relative).as_posix(), safe='/.-_') + ')'


def number(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ReportError('Expected a finite numeric result')
    return format(value, '.9g')


def elapsed(value):
    number(value)
    if value < 0:
        raise ReportError('Negative elapsed time')
    seconds = round(value)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    return f'{hours:02d}:{minutes:02d}:{seconds:02d}'


def run_path(record, project_root, runs_root):
    if runs_root is not None:
        return (Path(runs_root) / f"{record['mode']}-{record['seed']}").resolve(strict=True)
    if (Path(project_root) / 'DELIVERY_MANIFEST.json').is_file():
        return (Path(project_root) / 'runs' / f"{record['mode']}-{record['seed']}").resolve(strict=True)
    path = Path(record['path'])
    return (path if path.is_absolute() else Path(project_root) / path).resolve(strict=True)


def checked_inputs(analysis_path, project_root, runs_root=None):
    """Read journals and graphics; never run a model, replay or ontology mutation."""
    data = read_json(analysis_path)
    records = data.get('runs')
    if not isinstance(records, list) or len(records) != 10 or not isinstance(data.get('series'), dict):
        raise ReportError('Expected finished --series analysis of exactly ten runs')
    expected = {('model', seed) for seed in range(101, 106)} | {('control', seed) for seed in range(201, 206)}
    if {(record.get('mode'), record.get('seed')) for record in records} != expected:
        raise ReportError('Expected model seeds 101–105 and control seeds 201–205')
    collected = []
    verified = {}
    for saved in sorted(records, key=lambda record: (record['mode'] != 'model', record['seed'])):
        if saved.get('phase', 'main') != 'main':
            raise ReportError('Debug cannot enter the experiment series')
        directory = run_path(saved, project_root, runs_root)
        actual = analyze_run(directory, replay=False)
        # The fresh analysis verifies metadata/checkpoint/log checksums, exact
        # 170-evaluation budgets, history and completion. Preserve only the
        # replay evidence already measured by the explicit input analysis.
        for key, value in actual.items():
            if key not in ('path', 'replay') and saved.get(key) != value:
                raise ReportError(f"Saved analysis differs from journal: {directory.name}: {key}")
        replay = saved.get('replay')
        if (not isinstance(replay, dict) or replay.get('matches') is not True
                or replay.get('axioms_match') is not True
                or str(replay.get('candidate')) != str(actual['best_id'])
                or replay.get('F') != actual['best_F']):
            raise ReportError('Missing or inconsistent best-candidate replay evidence: ' + directory.name)
        actual['replay'] = replay
        verified[(actual['mode'], actual['seed'])] = actual
        stem = f"{actual['mode']}-{actual['seed']}"
        csv_path = Path(analysis_path).parent / (stem + '.csv')
        graph_path = Path(analysis_path).parent / (stem + '.png')
        if not csv_path.is_file() or not graph_path.is_file():
            raise ReportError('Missing CSV/PNG produced by analysis: ' + stem)
        rows = [json.loads(line) for line in (directory / 'evaluations.jsonl').read_text(encoding='utf-8').splitlines()]
        rejected = Counter(str(row['code']) for row in rows if row['status'] == 'invalid')
        interruptions = directory / 'interruptions.jsonl'
        interruption_count = len(interruptions.read_text(encoding='utf-8').splitlines()) if interruptions.is_file() else 0
        collected.append(dict(result=actual, directory=directory, csv=csv_path, graph=graph_path,
                              rejected=rejected, interruptions=interruption_count))
    summary = summarize([verified[(record['mode'], record['seed'])] for record in records])
    if summary != data['series']:
        raise ReportError('Saved series summary differs from the checked run results')
    return collected, summary


def render(analysis_path, output, collected, summary):
    source_hash = hashlib.sha256(Path(analysis_path).read_bytes()).hexdigest()
    lines = ['# Отчёт об экспериментах', '',
             'Отчёт построен по завершённому анализу десяти основных запусков. '
             'Контрольные суммы, бюджеты и показатели повторно сверены с журналами; '
             'модели при подготовке этого текста не вызывались.', '',
             'Источник: ' + markdown_link(analysis_path, output, 'analysis.json') + '.',
             'SHA-256 источника: `' + source_hash + '`.',
             'Числа округлены до девяти значащих цифр; полная точность сохранена в JSON.', '',
             '## Запуски', '',
             'Каждый запуск содержит 170 оценок: 10 начальных и 20 поколений по 8. '
             'Указаны активное время выполнения программы и календарный интервал; график содержит лучший/медианный F '
             'и доли отклонений по поколениям.', '',
             '| Запуск / журнал | Лучший F | Поколение / ID | Активное / календарное время | Отклонено / 170 | Replay | График / CSV |',
             '|---|---:|---|---:|---:|---|---|']
    for item in collected:
        result = item['result']
        label = f"{result['mode']}-{result['seed']}"
        source = markdown_link(item['directory'] / 'evaluations.jsonl', output, label)
        graph = markdown_link(item['graph'], output, 'PNG')
        csv = markdown_link(item['csv'], output, 'CSV')
        lines.append(f"| {source} | {number(result['best_F'])} | {result['best_generation']} / {result['best_id']} | "
                     f"{elapsed(result['active_seconds']) if result.get('active_seconds') is not None else 'нет данных'} / "
                     f"{elapsed(result['wall_clock_seconds'])} | {sum(item['rejected'].values())} | совпадает | {graph} / {csv} |")
    lines.extend(['', 'Replay — фактическое свидетельство из входного анализа: '
                  'восстановленные аксиомы и F лучшего кандидата совпали без обращения к модели. '
                  'Генератор отчёта не выдаёт повторное чтение этого свидетельства за новый replay.', '',
                  '## Сравнение серий и критерии', '',
                  '| Показатель | Факт | Критерий выполнен |', '|---|---:|---|'])
    targets = summary['targets']
    criteria = [
        ('Максимальный F модельной серии ≥ 1.25', summary['model_max'], targets['maximum']),
        ('Медианный F модельной серии ≥ 1.15', summary['model_median'], targets['median']),
        ('Каждый лучший F модельной серии > 1', min(summary['model_best']), targets['each_above_one']),
        ('Медиана модели выше медианы контроля', summary['control_median'], targets['median_above_control']),
    ]
    for label, value, passed in criteria:
        lines.append(f"| {label} | {number(value)} | {'да' if passed else 'нет'} |")
    lines.extend(['', 'В строке «каждый > 1» показан минимум модельной серии; '
                  'в строке сравнения медиан показана медиана контроля. '
                  'Медиана модели приведена отдельно выше.', '', '## Фактическое время серий', '',
                  '| Серия | Активное время | Календарный интервал | Активное ≤8 ч | Календарное ≤8 ч |',
                  '|---|---:|---:|---|---|'])
    for mode in ('model', 'control'):
        timing = summary['series_timing'][mode]
        durations = [item['result'].get('active_seconds') for item in collected if item['result']['mode'] == mode]
        complete = all(type(value) in (int, float) and math.isfinite(value) and value >= 0 for value in durations)
        active = sum(durations) if complete else None
        duration = elapsed(timing['seconds']) if timing['seconds'] is not None else 'не подтверждён'
        wall_outcome = 'не подтверждено' if timing['within_eight_hours'] is None else ('да' if timing['within_eight_hours'] else 'нет')
        active_outcome = 'не подтверждено' if active is None else ('да' if active <= 8*3600 else 'нет')
        lines.append(f'| {mode} | {elapsed(active) if active is not None else "не подтверждено"} | {duration} | {active_outcome} | {wall_outcome} |')
    lines.extend(['', 'Для оценки производительности по п. 4.8.2 используется сумма активного времени '
                  'выполнения программы, записанного в timing.json. Календарный интервал измеряется '
                  'от первого старта до последнего завершения и приведён отдельно без изменения. '
                  'Оба показателя рассчитаны по фактическим журналам, а не по прогнозу.', '', '## Манн—Уитни', ''])
    test = summary['mann_whitney']
    lines.extend([f"U = {number(test['U'])}; p = {number(test['p'])}; α = {number(test['alpha'])}.",
                  'Альтернатива: лучшие F модельной серии выше контрольной. '
                  'Использован точный односторонний перестановочный тест: 252 разбиения, '
                  'средние ранги при совпадениях.',
                  'Результат: ' + ('есть статистические свидетельства превосходства модели.' if test['significant'] else
                                  'статистических свидетельств превосходства модели при α=0.05 недостаточно.'),
                  'Отсутствие значимости само по себе не означает невыполнение статистического Т09.', '',
                  '## Причины отклонения', '',
                  'Числа ниже подсчитаны по status=invalid и первому коду отказа в evaluations.jsonl. '
                  'Это точные количества оценок, а не число ошибок отдельных аксиом или retry.', '',
                  '| Код | Модель | Контроль | Всего |', '|---|---:|---:|---:|'])
    counts = {mode: Counter() for mode in ('model', 'control')}
    for item in collected:
        counts[item['result']['mode']].update(item['rejected'])
    for code in sorted(set(counts['model']) | set(counts['control'])):
        left, right = counts['model'][code], counts['control'][code]
        lines.append(f'| {code} | {left} | {right} | {left + right} |')
    left, right = sum(counts['model'].values()), sum(counts['control'].values())
    lines.append(f'| Всего | {left} | {right} | {left + right} |')
    lines.extend(['',
                  '## Границы результата', '',
                  'Числа относятся к сохранённым основным сериям. Они не подтверждают автоматически '
                  'предметное одобрение каждой дельты, выпуск финальной онтологии 2.0.0, '
                  'проверку в Protégé/OOPS! или приёмку Т01–Т12. '
                  'Финальные значения и экспертные решения должны быть оформлены по фактическому финалу отдельно.', ''])
    return '\n'.join(lines)


def build_report(analysis_path, output, project_root=PROJECT, runs_root=None):
    analysis_path, output = Path(analysis_path).resolve(strict=True), Path(output)
    if output.exists() or output.is_symlink():
        raise FileExistsError('Output already exists: ' + str(output))
    collected, summary = checked_inputs(analysis_path, Path(project_root).resolve(), runs_root)
    text = render(analysis_path, output, collected, summary)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8', newline='\n') as destination:
        destination.write(text)
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--analysis', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--project-root', type=Path, default=PROJECT)
    parser.add_argument('--runs-root', type=Path, help='Relocated directory containing model-101…105/control-201…205')
    args = parser.parse_args(argv)
    try:
        result = build_report(args.analysis, args.output, args.project_root, args.runs_root)
    except (OSError, ValueError, RuntimeError, KeyError, TypeError, IndexError) as error:
        print(type(error).__name__ + ': ' + str(error), file=sys.stderr)
        return 2
    print(str(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
