"""Build upstream unchanged using isolated Maven settings/cache and two CPUs."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time

BASE=Path(__file__).resolve().parent
PROJECT=BASE.parents[1]
EVIDENCE=PROJECT/('docs/assessment/evidence/oops-reference' if (PROJECT/'DELIVERY_MANIFEST.json').is_file() else 'lab4/assessment/evidence/oops-reference')
COMMIT='11572ea6b31cba29dd3f8a443e24311652f059de'
SOURCE=BASE/('OOPS-'+COMMIT)
JDK=PROJECT/'.local-runtime/jdk-17.0.21+9/Contents/Home'
MAVEN=BASE/'apache-maven-3.9.16/bin/mvn'

def mask(text):
    text=re.sub(r'\b(?:y[01]_|t[01]_|AQAD-)[A-Za-z0-9_.-]+','[credential-redacted]',text)
    text=re.sub(r'(?i)(Bearer\s+|Api-Key\s+)[^\s]+',r'\1[redacted]',text)
    return re.sub(r'\b[0-9a-fA-F]{32}\b','[hex32-redacted]',text)

settings=b'<settings xmlns="http://maven.apache.org/SETTINGS/1.2.0"/>\n'
for name in ('empty-settings.xml','empty-global-settings.xml'):
    path=BASE/name
    if not path.exists():path.write_bytes(settings)
    if path.read_bytes()!=settings:raise ValueError('Unexpected nonempty Maven settings')
env=dict(PATH=str(JDK/'bin')+':'+str(MAVEN.parent)+':/usr/bin:/bin:/usr/sbin:/sbin',
         JAVA_HOME=str(JDK), MAVEN_SKIP_RC='1',
         MAVEN_OPTS='-Xmx768m -XX:ActiveProcessorCount=2',LANG='en_US.UTF-8')
prefix=['/usr/bin/nice','-n','10',str(MAVEN),'--batch-mode','--no-transfer-progress',
        '--settings',str(BASE/'empty-settings.xml'),'--global-settings',str(BASE/'empty-global-settings.xml'),
        '-Dmaven.repo.local='+str(BASE/'m2'),'-Dstyle.color=never']
files={path.relative_to(SOURCE).as_posix():hashlib.sha256(path.read_bytes()).hexdigest()
       for path in SOURCE.rglob('*') if path.is_file() and 'target' not in path.relative_to(SOURCE).parts}
(EVIDENCE/'upstream-source-sha256.json').write_text(json.dumps(files,indent=2)+'\n')
versions=subprocess.run([str(MAVEN),'-version'],cwd=SOURCE,env=env,capture_output=True,text=True)
(EVIDENCE/'maven-version.txt').write_text(mask(versions.stdout+versions.stderr))
command=prefix+['package','-Dmaven.test.skip=true']
started=time.time()
process=subprocess.Popen(command,cwd=SOURCE,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
state=dict(pid=process.pid,started_at=started,command=command,source_commit=COMMIT,
           settings='explicit empty user and global settings',maven_skip_rc=True,
           environment='explicit minimal environment; no inherited tokens',active_processors=2,nice=10)
(EVIDENCE/'build-state.json').write_text(json.dumps(state,indent=2)+'\n')
with (EVIDENCE/'build.log').open('x') as log:
    for line in process.stdout:log.write(mask(line));log.flush()
status=process.wait()
state.update(exit_code=status,ended_at=time.time(),seconds=time.time()-started)
war=SOURCE/'target/oops-0.3.0-SNAPSHOT.war'
if status==0 and war.is_file():
    state.update(war_sha256=hashlib.sha256(war.read_bytes()).hexdigest(),war_bytes=war.stat().st_size)
(EVIDENCE/'build-state.json').write_text(json.dumps(state,indent=2)+'\n')
print(json.dumps(state))
raise SystemExit(status)
