#!/usr/bin/env python3
"""Compile a launch-only agent and start the unmodified installed Protégé GUI.

Only the requested ontology and its generated copies are inspected. This helper
does not attach to existing processes or use desktop/accessibility automation.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ontology', type=Path, required=True)
    parser.add_argument('--expected', type=Path, required=True)
    parser.add_argument('--protege', type=Path, required=True)
    parser.add_argument('--jdk', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--launch', action='store_true')
    args = parser.parse_args()
    args.ontology = args.ontology.resolve(strict=True)
    args.expected = args.expected.resolve(strict=True)
    args.protege = args.protege.resolve(strict=True)
    args.jdk = args.jdk.resolve(strict=True)
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=False)
    helper = Path(__file__).resolve().parent
    classes = args.output / 'agent-classes'
    classes.mkdir()
    subprocess.run([str(args.jdk / 'bin/javac'), '-encoding', 'UTF-8', '-d', str(classes),
                    str(helper / 'AcceptanceAgent.java')], check=True)
    agent = args.output / 'acceptance-agent.jar'
    subprocess.run([str(args.jdk / 'bin/jar'), 'cfm', str(agent),
                    str(helper / 'ACCEPTANCE-MANIFEST.MF'), '-C', str(classes), '.'], check=True)
    expected = json.loads(args.expected.read_text(encoding='utf-8'))
    templates = {
        'Q1': 'VideoCardModel and producedByManufacturer value %s',
        'Q2': 'VideoCardModel and usesGPU value %s',
        'Q4': 'VideoCardModel and hasMemory some (hasMemoryType value %s)',
        'Q6': 'VideoCardModel and hasVideoOutput value %s',
        'Q7': 'VideoCardModel and hasInterface value %s',
    }
    defined = {
        'Q3': ('CardWith8GBMemory', 'VideoCardModel and hasMemory some (volumeGiB some xsd:integer[>= 8])'),
        'Q5': ('CardWithActiveCooling', 'VideoCardModel and hasCooling some ActiveCooling'),
        'Q8': ('CardWith8GBMemory and CardWithActiveCooling',
               'VideoCardModel and hasMemory some (volumeGiB some xsd:integer[>= 8]) and hasCooling some ActiveCooling'),
    }
    lines = []
    for qid, question in expected['questions'].items():
        if qid in templates:
            for argument, members in question['expected'].items():
                lines.append('\t'.join((qid + ' [' + argument + ']', templates[qid] % argument,
                                        ','.join(sorted(members)))))
        else:
            for kind, query in zip(('defined', 'raw cross-check'), defined[qid]):
                lines.append('\t'.join((qid + ' [' + kind + ']', query,
                                        ','.join(sorted(question['expected'])))))
    queries = args.output / 'queries.tsv'
    queries.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    config = args.output / 'collector.properties'
    config.write_text('ontology=' + str(args.ontology) + '\nqueries=' + str(queries)
                      + '\noutput=' + str(args.output) + '\n', encoding='utf-8')
    bundles = ('guava.jar', 'logback-classic.jar', 'logback-core.jar', 'slf4j-api.jar',
               'glassfish-corba-orb.jar', 'org.apache.felix.main.jar', 'maven-artifact.jar',
               'protege-launcher.jar')
    command = [str(args.jdk / 'bin/java'), '-Xmx768m', '-XX:ActiveProcessorCount=2',
               '-DentityExpansionLimit=100000000', '-Dlogback.configurationFile=conf/logback.xml',
               '-Dfile.encoding=UTF-8', '-Duser.home=' + str(args.output / 'application-home'),
               '-Djava.util.prefs.userRoot=' + str(args.output / 'preferences'),
               '-XX:CompileCommand=exclude,javax/swing/text/GlyphView,getBreakSpot',
               '--add-opens=java.desktop/sun.swing=ALL-UNNAMED',
               '--add-opens=java.desktop/com.apple.laf=ALL-UNNAMED',
               '-javaagent:' + str(agent) + '=' + str(config), '-classpath',
               ':'.join('bundles/' + jar for jar in bundles),
               'org.protege.osgi.framework.Launcher', args.ontology.as_uri()]
    metadata = {
        'ontology': str(args.ontology), 'source_sha256': digest(args.ontology),
        'expected': str(args.expected), 'expected_sha256': digest(args.expected),
        'helper_sha256': digest(helper / 'AcceptanceAgent.java'),
        'agent_sha256': digest(agent), 'command': command,
        'cwd': str(args.protege), 'query_count': len(lines),
        'mode': 'real GUI, launch-only premain, public in-process API',
        'not_performed': 'No attachment, accessibility, desktop screenshots or independent HermiT instance',
    }
    if args.launch:
        with (args.output / 'application.log').open('wb') as log:
            process = subprocess.Popen(command, cwd=args.protege, stdout=log, stderr=subprocess.STDOUT,
                                       start_new_session=True)
        metadata['pid'] = process.pid
    (args.output / 'launch.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n',
                                           encoding='utf-8')
    print(json.dumps({'output': str(args.output), 'pid': metadata.get('pid'), 'query_count': len(lines)}))


if __name__ == '__main__':
    main()
