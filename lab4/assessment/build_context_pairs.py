"""Freeze ontology-grounded label.comment datasets without model access.

Mappings depend on the phrase's meaning, not its pair ID or model score.
The original short-phrase dataset is read only.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path

from lab4.optimizer.bridge import CORE, CORE_SHA256, ROOT
from lab4.optimizer.prepare import ontology_inventory
from lab4.optimizer.paths import ASSESSMENT


PREFIX = 'https://example.org/ontologies/videocard#'
PHRASES = {
    'Видеокарта': 'VideoCardModel', 'Графическая плата': 'VideoCardModel',
    'Графический процессор': 'GPUModel', 'GPU': 'GPUModel',
    'Видеопамять': 'MemoryConfiguration', 'Графическая память': 'MemoryConfiguration',
    'Объём видеопамяти': 'volumeGiB', 'Ёмкость видеопамяти': 'volumeGiB',
    'Ширина шины памяти': 'busWidthBit', 'Разрядность шины памяти': 'busWidthBit',
    'Активное охлаждение': 'ActiveCooling', 'Охлаждение с вентилятором': 'ActiveCooling',
    'Пассивное охлаждение': 'PassiveCooling', 'Безвентиляторное охлаждение': 'PassiveCooling',
    'Производитель видеокарты': 'producedByManufacturer',
    'Изготовитель графической платы': 'producedByManufacturer',
    'Видеовыход': 'VideoOutput', 'Выход видеосигнала': 'VideoOutput',
    'Частота графического процессора': 'frequencyMHz', 'Тактовая частота GPU': 'frequencyMHz',
    'Производитель GPU': 'gpuProducedBy', 'Интерфейс подключения': 'ConnectionInterface',
    'Частота GPU': 'frequencyMHz', 'Потребляемая мощность': 'powerW',
    'Тип памяти': 'MemoryType', 'Объём памяти': 'volumeGiB',
    'Архитектура GPU': 'GPUArchitecture', 'Модель GPU': 'GPUModel',
    'Длина видеокарты': 'lengthMM', 'Число вентиляторов': 'fanCount',
    'Назначение видеокарты': 'Purpose',
    # Holdout phrases denote additional concepts not used by calibration pairs.
    'Система охлаждения': 'CoolingSystem', 'Охлаждающая система': 'CoolingSystem',
    'Компонент модели': 'ModelComponent', 'Составная часть модели': 'ModelComponent',
    'Карта с памятью от 8 ГиБ': 'CardWith8GBMemory',
    'Карта с объёмом видеопамяти не менее 8 ГиБ': 'CardWith8GBMemory',
    'Карта с активным охлаждением': 'CardWithActiveCooling',
    'Видеокарта с вентиляторным охлаждением': 'CardWithActiveCooling',
    'Имеет архитектуру': 'hasArchitecture', 'Построен на архитектуре': 'hasArchitecture',
    'Имеет охлаждение': 'hasCooling', 'Оснащена системой охлаждения': 'hasCooling',
    'Имеет интерфейс': 'hasInterface', 'Подключается через интерфейс': 'hasInterface',
    'Имеет память': 'hasMemory', 'Оснащена конфигурацией видеопамяти': 'hasMemory',
    'Имеет тип памяти': 'hasMemoryType', 'Использует технологию видеопамяти': 'hasMemoryType',
    'Имеет назначение': 'hasPurpose', 'Предназначена для применения': 'hasPurpose',
    'Использует GPU': 'usesGPU', 'Имеет видеовыход': 'hasVideoOutput',
}

HOLDOUT = [
    ('Система охлаждения', 'Охлаждающая система', 1),
    ('Компонент модели', 'Составная часть модели', 1),
    ('Карта с памятью от 8 ГиБ', 'Карта с объёмом видеопамяти не менее 8 ГиБ', 1),
    ('Карта с активным охлаждением', 'Видеокарта с вентиляторным охлаждением', 1),
    ('Имеет архитектуру', 'Построен на архитектуре', 1),
    ('Имеет охлаждение', 'Оснащена системой охлаждения', 1),
    ('Имеет интерфейс', 'Подключается через интерфейс', 1),
    ('Имеет память', 'Оснащена конфигурацией видеопамяти', 1),
    ('Имеет тип памяти', 'Использует технологию видеопамяти', 1),
    ('Имеет назначение', 'Предназначена для применения', 1),
    ('Система охлаждения', 'Компонент модели', 0),
    ('Карта с памятью от 8 ГиБ', 'Карта с активным охлаждением', 0),
    ('Система охлаждения', 'Карта с активным охлаждением', 0),
    ('Компонент модели', 'Карта с памятью от 8 ГиБ', 0),
    ('Имеет архитектуру', 'Имеет охлаждение', 0),
    ('Имеет интерфейс', 'Имеет память', 0),
    ('Имеет тип памяти', 'Имеет назначение', 0),
    ('Имеет память', 'Имеет охлаждение', 0),
    ('Использует GPU', 'Имеет архитектуру', 0),
    ('Имеет видеовыход', 'Имеет интерфейс', 0),
]


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def contextualize(pairs, entities):
    dictionary = {entity['iri']: entity for entity in entities}
    result = []
    for pair in pairs:
        row = {key: pair[key] for key in ('id', 'synonym', 'review_status')}
        for side in ('left', 'right'):
            label = pair[side]
            iri = PREFIX + PHRASES[label]
            entity = dictionary[iri]
            row.update({side: label + '. ' + entity['comment'],
                        side + '_label': label, side + '_comment': entity['comment'],
                        side + '_category': entity['category'], side + '_iri': iri})
        row['same_category'] = str(row['left_category'] == row['right_category']).lower()
        result.append(row)
    return result


def csv_bytes(rows):
    buffer = io.StringIO(newline='')
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]), lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode('utf-8')


def build(output_dir):
    output_dir = Path(output_dir)
    source_path = ASSESSMENT / 'concept_pairs.csv'
    raw = source_path.read_bytes()
    if sha256(CORE.read_bytes()) != CORE_SHA256:
        raise ValueError('Original ontology checksum mismatch')
    original = list(csv.DictReader(io.StringIO(raw.decode('utf-8'))))
    _, entities = ontology_inventory()
    calibration = contextualize(original, entities)
    holdout_source = [dict(id='HOLDOUT' + str(index + 1).zfill(2), left=left, right=right,
                           synonym=str(label), review_status='approved')
                      for index, (left, right, label) in enumerate(HOLDOUT)]
    holdout = contextualize(holdout_source, entities)
    calibration_iris = {row[side + '_iri'] for row in calibration for side in ('left', 'right')}
    holdout_iris = {row[side + '_iri'] for row in holdout for side in ('left', 'right')}
    if calibration_iris & holdout_iris:
        raise ValueError('Holdout concepts overlap calibration concepts')
    datasets = {'concept_pairs_context.csv': csv_bytes(calibration),
                'concept_pairs_holdout.csv': csv_bytes(holdout)}
    registration = dict(
        schema=1, frozen_at_utc=datetime.now(timezone.utc).isoformat(),
        reviewed_by='AI', stage='Frozen before any context/holdout embedding measurement',
        core_sha256=CORE_SHA256, original_pairs_sha256=sha256(raw),
        builder_sha256=sha256(Path(__file__).read_bytes()),
        datasets={name: dict(sha256=sha256(content), count=20, synonyms=10, distinct=10)
                  for name, content in datasets.items()},
        protocol=dict(
            text='label + ". " + exact Russian ontology comment; shared definition per actual entity IRI',
            embedding_inputs='Only left/right; no pair ID, expected label, category or score is embedded',
            labels='Original 20 labels and phrases preserved; all 20 pairs embedding-scored without category skips',
            categories='Taken from actual OWL entity type; cross-category negative pairs remain scored',
            threshold='Try 0.90; if errors, choose midpoint of nonempty separating interval; otherwise report blocker',
            holdout='20 additional balanced pairs with disjoint concept IRIs; fixed calibration threshold, no tuning',
            no_adaptation='Do not rewrite definitions, remove pairs, or relabel after scores; retain every measured attempt',
            limitations='Ontology-grounded semisynthetic definitions; synonyms share comments; holdout shares construction method and is not independent human validation',
            acceptance='No success assumed; T04 still requires zero errors on mandatory pairs and >=70% valid first responses'),
        cross_category_calibration_ids=[row['id'] for row in calibration if row['same_category'] == 'false'],
        calibration_holdout_iri_overlap=[])
    output_dir.mkdir(parents=True, exist_ok=True)
    registration_name = 'CONTEXT_PREREGISTRATION.json'
    if any((output_dir / name).exists() for name in [*datasets, registration_name]):
        raise FileExistsError('Frozen dataset/registration already exists')
    for name, content in datasets.items():
        with (output_dir / name).open('xb') as output:
            output.write(content)
    with (output_dir / registration_name).open('x', encoding='utf-8') as output:
        output.write(json.dumps(registration, ensure_ascii=False, indent=2) + '\n')
    return registration


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ASSESSMENT)
    args = parser.parse_args()
    print(json.dumps(build(args.output_dir), ensure_ascii=False, indent=2))
