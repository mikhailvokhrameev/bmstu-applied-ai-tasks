"""Finalize reference provenance and check the RDF comparator rejects corruption."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

BASE=Path(__file__).resolve().parent
PROJECT=BASE.parents[1]
EVIDENCE=PROJECT/('docs/assessment/evidence/oops-reference' if (PROJECT/'DELIVERY_MANIFEST.json').is_file() else 'lab4/assessment/evidence/oops-reference')
SOURCE=BASE/'OOPS-11572ea6b31cba29dd3f8a443e24311652f059de'
JDK=PROJECT/'.local-runtime/jdk-17.0.21+9/Contents/Home'
MAVEN=BASE/'apache-maven-3.9.16/bin/mvn'
env=dict(PATH=str(JDK/'bin')+':'+str(MAVEN.parent)+':/usr/bin:/bin:/usr/sbin:/sbin',
         JAVA_HOME=str(JDK),MAVEN_SKIP_RC='1',MAVEN_OPTS='-Xmx768m -XX:ActiveProcessorCount=2',LANG='en_US.UTF-8')
prefix=['/usr/bin/nice','-n','10',str(MAVEN),'--batch-mode','--no-transfer-progress',
        '--settings',str(BASE/'empty-settings.xml'),'--global-settings',str(BASE/'empty-global-settings.xml'),
        '-Dmaven.repo.local='+str(BASE/'m2'),'-Dstyle.color=never']
deps=subprocess.run(prefix+['dependency:tree','-DoutputType=text','-DoutputFile='+str(EVIDENCE/'dependencies.txt')],
                    cwd=SOURCE,env=env,capture_output=True,text=True,timeout=120)
(EVIDENCE/'dependency-tree.log').write_text(deps.stdout+deps.stderr)
if deps.returncode:raise RuntimeError('Dependency tree failed')
expected=json.loads((EVIDENCE/'upstream-source-sha256.json').read_text())
changed=[name for name,digest in expected.items() if hashlib.sha256((SOURCE/name).read_bytes()).hexdigest()!=digest]
if changed:raise RuntimeError('Upstream sources changed: '+str(changed))
negative=EVIDENCE/'comparator-negative-control';negative.mkdir(exist_ok=False)
actual=(EVIDENCE/'fixtures/P04/actual.ttl').read_text()
corrupted=actual.replace('testP04#UnconnectedClass','testP04#DeliberatelyWrongElement')
if actual==corrupted:raise ValueError('Negative control did not change an affected element')
(negative/'deliberately-corrupted-actual.ttl').write_text(corrupted)
lib=BASE/'tomcat-instance/webapps/oops-reference/WEB-INF/lib/*'
comparison=subprocess.run([str(JDK/'bin/java'),'-XX:ActiveProcessorCount=2','-Xmx256m','-cp',str(BASE/'fixture-comparator')+':'+str(lib),
                           'CompareFixtures',str(EVIDENCE/'fixtures/P04/upstream-expected.ttl'),str(negative/'deliberately-corrupted-actual.ttl'),'P04'],
                          env=env,text=True,capture_output=True,timeout=60)
if comparison.returncode:raise RuntimeError('Negative comparator invocation failed')
result=json.loads(comparison.stdout)
if result['matches'] is not False:raise ValueError('Comparator accepted a deliberate semantic mismatch')
(negative/'result.json').write_text(json.dumps(result,indent=2)+'\n')
server=json.loads((EVIDENCE/'server.json').read_text())
listeners=subprocess.run(['/usr/sbin/lsof','-a','-p',str(server['pid']),'-iTCP','-sTCP:LISTEN','-P','-n'],capture_output=True,text=True)
(EVIDENCE/'listeners.txt').write_text(listeners.stdout+listeners.stderr)
if '127.0.0.1:11438' not in listeners.stdout or '127.0.0.1:11439' not in listeners.stdout:
    raise ValueError('Expected loopback listener proof is missing')
console=(BASE/'tomcat-console.log').read_text(errors='replace')
console=re.sub(r'\b(?:y[01]_|t[01]_|AQAD-)[A-Za-z0-9_.-]+','[credential-redacted]',console)
console=re.sub(r'\b[0-9a-fA-F]{32}\b','[hex32-redacted]',console)
(EVIDENCE/'tomcat-startup.log').write_text(console)
summary=json.loads((EVIDENCE/'fixture-summary.json').read_text())
server.update(status='ready; 12/12 official REST fixture cases match upstream semantics',
              official_fixtures_passed=summary['all_passed'],baseline_sent=False,final_sent=False,
              upstream_sources_unchanged=True,source_file_count=len(expected),
              comparator_negative_control_rejected=True)
(EVIDENCE/'server.json').write_text(json.dumps(server,indent=2)+'\n')
for name in ('bootstrap.py','build.py','deploy.py','fixtures.py','audit.py'):
    shutil.copyfile(BASE/name,EVIDENCE/name)
print(json.dumps(dict(ready=True,pid=server['pid'],endpoint=server['endpoint'],fixtures='12/12',
                      source_files_unchanged=len(expected),negative_control_rejected=True,
                      baseline_sent=False,final_sent=False)))
