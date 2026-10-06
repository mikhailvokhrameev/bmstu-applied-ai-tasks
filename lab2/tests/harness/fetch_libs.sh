#!/usr/bin/env bash
# Downloads the pinned OWL API 4.5.29 + HermiT 1.4.3.456 jars (and their
# transitive runtime dependencies) from Maven Central into tests/harness/lib/.
# Needs only bash + curl (no Maven). Idempotent: jars already present and
# matching their verified checksum are skipped without touching the network.
# Every downloaded jar is verified against the .sha1 that Maven Central
# publishes next to it.
#
# The list below was produced once with `mvn dependency:list` for
#   net.sourceforge.owlapi:owlapi-distribution:4.5.29
#   net.sourceforge.owlapi:org.semanticweb.hermit:1.4.3.456
# The owlapi-* sub-modules (api, impl, parsers, ...) are omitted on purpose:
# owlapi-distribution already embeds them.
set -euo pipefail

LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib"
CENTRAL="https://repo1.maven.org/maven2"

# groupId:artifactId:version
JARS='
net.sourceforge.owlapi:owlapi-distribution:4.5.29
net.sourceforge.owlapi:org.semanticweb.hermit:1.4.3.456
com.github.ben-manes.caffeine:caffeine:2.9.3
javax.inject:javax.inject:1
com.fasterxml.jackson.core:jackson-core:2.16.1
com.fasterxml.jackson.core:jackson-databind:2.16.1
com.fasterxml.jackson.core:jackson-annotations:2.16.1
org.tukaani:xz:1.9
org.slf4j:slf4j-api:2.0.11
org.slf4j:jcl-over-slf4j:2.0.11
org.eclipse.rdf4j:rdf4j-model:3.7.7
org.eclipse.rdf4j:rdf4j-model-api:3.7.7
org.eclipse.rdf4j:rdf4j-model-vocabulary:3.7.7
org.eclipse.rdf4j:rdf4j-rio-api:3.7.7
javax.xml.bind:jaxb-api:2.3.1
javax.activation:javax.activation-api:1.2.0
org.eclipse.rdf4j:rdf4j-rio-languages:3.7.7
org.eclipse.rdf4j:rdf4j-rio-datatypes:3.7.7
org.eclipse.rdf4j:rdf4j-rio-binary:3.7.7
org.eclipse.rdf4j:rdf4j-rio-n3:3.7.7
org.eclipse.rdf4j:rdf4j-rio-nquads:3.7.7
org.eclipse.rdf4j:rdf4j-rio-ntriples:3.7.7
org.eclipse.rdf4j:rdf4j-rio-rdfjson:3.7.7
org.eclipse.rdf4j:rdf4j-rio-jsonld:3.7.7
org.eclipse.rdf4j:rdf4j-rio-rdfxml:3.7.7
org.eclipse.rdf4j:rdf4j-rio-trix:3.7.7
org.eclipse.rdf4j:rdf4j-rio-turtle:3.7.7
org.eclipse.rdf4j:rdf4j-rio-trig:3.7.7
org.eclipse.rdf4j:rdf4j-util:3.7.7
org.apache.httpcomponents:httpclient:4.5.13
org.apache.httpcomponents:httpcore:4.4.13
org.apache.httpcomponents:httpclient-cache:4.5.13
org.apache.httpcomponents:httpclient-osgi:4.5.13
org.apache.httpcomponents:httpmime:4.5.13
org.apache.httpcomponents:fluent-hc:4.5.13
org.apache.httpcomponents:httpcore-osgi:4.4.14
org.apache.httpcomponents:httpcore-nio:4.4.14
com.github.jsonld-java:jsonld-java:0.13.6
commons-codec:commons-codec:1.11
commons-io:commons-io:2.15.1
commons-logging:commons-logging:1.1.3
com.github.vsonnier:hppcrt:0.7.5
com.google.guava:guava:33.0.0-jre
com.google.guava:failureaccess:1.0.2
com.google.guava:listenablefuture:9999.0-empty-to-avoid-conflict-with-guava
org.checkerframework:checker-qual:3.41.0
com.google.errorprone:error_prone_annotations:2.23.0
com.google.j2objc:j2objc-annotations:2.8
com.google.code.findbugs:jsr305:3.0.2
org.apache.ws.commons.axiom:axiom-api:1.2.14
org.apache.ws.commons.axiom:axiom-c14n:1.2.14
org.apache.ws.commons.axiom:axiom-impl:1.2.14
org.apache.ws.commons.axiom:axiom-dom:1.2.14
org.apache.geronimo.specs:geronimo-activation_1.1_spec:1.1
org.apache.geronimo.specs:geronimo-javamail_1.4_spec:1.7.1
org.apache.geronimo.specs:geronimo-stax-api_1.0_spec:1.0.1
org.apache.james:apache-mime4j-core:0.7.2
org.codehaus.woodstox:woodstox-core-asl:4.1.4
org.codehaus.woodstox:stax2-api:3.1.1
jaxen:jaxen:1.1.4
dk.brics.automaton:automaton:1.11-8
gnu.getopt:java-getopt:1.0.13
'

sha1_of() {
  if command -v sha1sum >/dev/null 2>&1; then
    sha1sum "$1" | cut -d' ' -f1
  else
    shasum -a 1 "$1" | cut -d' ' -f1
  fi
}

mkdir -p "$LIB_DIR"
downloaded=0
kept=0
while IFS=: read -r group artifact version; do
  [ -n "$group" ] || continue
  file="$artifact-$version.jar"
  dest="$LIB_DIR/$file"
  url="$CENTRAL/${group//.//}/$artifact/$version/$file"

  # Present and matching the checksum recorded when it was last verified.
  if [ -f "$dest" ] && [ -f "$dest.sha1" ] && [ "$(sha1_of "$dest")" = "$(cat "$dest.sha1")" ]; then
    kept=$((kept + 1))
    continue
  fi

  echo "fetch $file"
  tmp="$dest.part"
  curl -fsSL --retry 3 -o "$tmp" "$url"
  expected="$(curl -fsSL --retry 3 "$url.sha1" | tr -d '[:space:]' | cut -c1-40)"
  actual="$(sha1_of "$tmp")"
  if [ "$expected" != "$actual" ]; then
    rm -f "$tmp"
    echo "SHA-1 mismatch for $file: expected $expected, got $actual" >&2
    exit 1
  fi
  mv "$tmp" "$dest"
  echo "$actual" > "$dest.sha1"
  downloaded=$((downloaded + 1))
done <<< "$JARS"

echo "libs ready in $LIB_DIR (downloaded $downloaded, already present $kept)"
