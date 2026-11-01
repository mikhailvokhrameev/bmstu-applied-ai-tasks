"""Check manually counted fixtures against OWL API, then their rational formula columns."""
from pathlib import Path
from fractions import Fraction
from collections import Counter
import json
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
EXPECTED_SHA = 'd8ac600a45ce642deee38be726ae5d0d81f9e47967a9e1bb07a66b5005ae3661'

def main():
    import hashlib
    source = ROOT / 'lab2/ontology/videocard.owl'
    if hashlib.sha256(source.read_bytes()).hexdigest() != EXPECTED_SHA:
        raise SystemExit('STOP: source SHA-256 mismatch')
    expected = json.loads((HERE / 'fixtures/expected.json').read_text())
    baseline = expected['baseline']
    def metrics(d):
        return [Fraction(d[a], d[b]) for a,b in [('H','C'), ('Po','denominator'), ('Pd','C'), ('E','C'), ('Al','A')]]
    baseline['denominator'] = baseline['H'] + baseline['Po']
    weights = list(map(Fraction, ['.15','.15','.10','.15','.15','.30']))
    logs = []
    with tempfile.TemporaryDirectory(prefix='videocard-reference-') as classes:
        libs = str(ROOT / 'lab2/tests/harness/lib/*')
        subprocess.run(['javac','-cp',libs,'-d',classes,str(HERE/'ReferenceAudit.java')],check=True)
        for row in [{'fixture':'baseline', **baseline}, *expected['cases']]:
            path = source if row['fixture']=='baseline' else HERE/'fixtures'/(row['fixture']+'.ofn')
            output = subprocess.check_output(['java','-Dslf4j.internal.verbosity=ERROR','-cp',classes+':'+libs,'ReferenceAudit',str(path)],text=True)
            logs += [row['fixture'], output]
            counts = dict(part.split('=') for part in output.splitlines()[0].split())
            for key in ['C','H','Po','Pd','E','Al','A']:
                assert int(counts[key]) == row[key], (row['fixture'],key,counts[key],row[key])
            violations = Counter(line.split()[0] for line in output.splitlines()[1:])
            assert sum(violations.values()) == row['Q'], (row['fixture'],violations)
            if row['fixture']=='baseline':
                assert violations == {'P13':10}
                continue
            for code in ['P04','P08','P10','P11','P13','P22']:
                assert violations[code] == row[code], (row['fixture'],code)
            d = dict(row, denominator=row['H']+row['Po'])
            measured = metrics(d)
            assert measured == [Fraction(row['M'+str(i)]) for i in range(1,6)]
            ratios = [min(a/b,Fraction(2)) for a,b in zip(measured,metrics(baseline))]
            ratios.append(min(Fraction(baseline['Q']+1,row['Q']+1),Fraction(2)))
            assert ratios == [Fraction(row['r'+str(i)]) for i in range(1,7)]
            score = sum(a*b for a,b in zip(weights,ratios))
            assert score == Fraction(row['F_exact'])
            assert abs(float(score)-row['F']) < 1e-12
    print('\n'.join(logs))
    print('PASS: source SHA-256; baseline and 3 hand-counted fixtures; six checks; exact M1–M6, capped ratios and F')

if __name__ == '__main__':
    main()
