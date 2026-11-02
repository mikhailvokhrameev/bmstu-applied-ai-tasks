import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;
import com.fasterxml.jackson.databind.*;
import org.semanticweb.owlapi.apibinding.OWLManager;
import org.semanticweb.owlapi.formats.RDFXMLDocumentFormat;
import org.semanticweb.owlapi.model.*;
import org.semanticweb.owlapi.util.VersionInfo;

/** Isolated RDF/XML materialization and shared engine checks, never GUI evidence. */
public final class OntologyRelease {
    static final ObjectMapper JSON = new ObjectMapper();

    static String sha256(byte[] content) throws Exception {
        StringBuilder result = new StringBuilder();
        for (byte value : MessageDigest.getInstance("SHA-256").digest(content)) result.append(String.format("%02x", value & 255));
        return result.toString();
    }

    static List<String> strings(JsonNode values) {
        if (values == null || !values.isArray()) throw new IllegalArgumentException("Expected axiom array");
        List<String> result = new ArrayList<>();
        for (JsonNode value : values) {
            if (!value.isTextual()) throw new IllegalArgumentException("Expected axiom text");
            result.add(value.asText());
        }
        return result;
    }

    static byte[] rdfxml(OWLOntology ontology) throws Exception {
        try (ByteArrayOutputStream output = new ByteArrayOutputStream()) {
            ontology.getOWLOntologyManager().saveOntology(ontology, new RDFXMLDocumentFormat(), output);
            return output.toByteArray();
        }
    }

    static void writeNew(Path path, byte[] content) throws Exception {
        Files.createDirectories(path.getParent());
        Files.write(path, content, StandardOpenOption.CREATE_NEW);
    }

    static Map<String,Object> export(JsonNode request) throws Exception {
        Path corePath = Path.of(request.get("core").asText());
        if (!sha256(Files.readAllBytes(corePath)).equals(request.get("core_sha256").asText())) throw new IllegalArgumentException("CORE_CHECKSUM");
        if (!request.get("version").asText().equals("2.0.0")) throw new IllegalArgumentException("Version must be 2.0.0");
        OWLOntologyManager manager = OWLManager.createOWLOntologyManager();
        OWLOntology ontology = manager.loadOntologyFromOntologyDocument(corePath.toFile());
        if (!ontology.getImportsDeclarations().isEmpty()) throw new IllegalArgumentException("External imports are unsupported");
        Set<OWLAxiom> core = new HashSet<>(ontology.getAxioms());
        JsonNode delta = request.get("delta");
        Set<OWLAxiom> additions = OntologyEvaluator.parse(strings(delta.get("add")));
        Set<OWLAxiom> removals = OntologyEvaluator.parse(strings(delta.get("remove")));
        if (removals.stream().anyMatch(core::contains)) throw new IllegalArgumentException("CORE_REMOVAL");
        manager.addAxioms(ontology, additions);
        manager.removeAxioms(ontology, removals);
        if (!ontology.getOntologyID().getOntologyIRI().isPresent()) throw new IllegalArgumentException("Missing ontology IRI");
        IRI ontologyIRI = ontology.getOntologyID().getOntologyIRI().get();
        IRI versionIRI = IRI.create("https://example.org/ontologies/videocard/2.0.0");
        manager.applyChange(new SetOntologyID(ontology, new OWLOntologyID(ontologyIRI, versionIRI)));
        OWLAnnotationProperty versionInfo = manager.getOWLDataFactory().getOWLVersionInfo();
        for (OWLAnnotation annotation : new HashSet<>(ontology.getAnnotations())) {
            if (annotation.getProperty().equals(versionInfo)) manager.applyChange(new RemoveOntologyAnnotation(ontology, annotation));
        }
        manager.applyChange(new AddOntologyAnnotation(ontology, manager.getOWLDataFactory().getOWLAnnotation(versionInfo, manager.getOWLDataFactory().getOWLLiteral("2.0.0"))));
        byte[] document = rdfxml(ontology);
        OWLOntology restored = OWLManager.createOWLOntologyManager().loadOntologyFromOntologyDocument(new ByteArrayInputStream(document));
        if (!ontology.getAxioms().equals(restored.getAxioms())) throw new IllegalStateException("RDF/XML axiom roundtrip mismatch");
        if (!ontology.getOntologyID().equals(restored.getOntologyID())) throw new IllegalStateException("RDF/XML identity roundtrip mismatch");
        if (!ontology.getAnnotations().equals(restored.getAnnotations())) throw new IllegalStateException("RDF/XML header roundtrip mismatch");
        if (!restored.getAxioms().containsAll(core)) throw new IllegalStateException("Immutable core changed");
        Map<String,Long> counts = OntologyEvaluator.audit(ontology).counts;
        if (!counts.equals(OntologyEvaluator.audit(restored).counts)) throw new IllegalStateException("RDF/XML count roundtrip mismatch");
        Map<String,Object> result = new LinkedHashMap<>();
        result.put("document_base64", Base64.getEncoder().encodeToString(document));
        result.put("sha256", sha256(document));
        result.put("core_sha256", request.get("core_sha256").asText());
        result.put("ontology_iri", ontologyIRI.toString());
        result.put("version_iri", versionIRI.toString());
        result.put("version_info", "2.0.0");
        result.put("core_preserved", true);
        result.put("roundtrip_verified", true);
        result.put("counts", counts);
        return result;
    }

    static Map<String,Object> acceptance(JsonNode request) throws Exception {
        Path root = Path.of(request.get("root").asText());
        Support.setRoot(root);
        OWLOntology finalOntology = Support.load(Support.ontologyFile().toFile());
        List<NegativeCopyTest> mutations = List.of(new T06ActiveAndPassive(), new T07TwoGpus(), new T08NegativeVolume(), new T09MissingHasMemory());
        Map<String,String> mutantHashes = new LinkedHashMap<>();
        for (NegativeCopyTest mutation : mutations) {
            OWLOntologyManager manager = OWLManager.createOWLOntologyManager();
            OWLOntology copy = manager.createOntology(finalOntology.getOntologyID());
            manager.addAxioms(copy, finalOntology.getAxioms());
            for (OWLAnnotation annotation : finalOntology.getAnnotations()) manager.applyChange(new AddOntologyAnnotation(copy, annotation));
            manager.removeAxioms(copy, mutation.removedByMutation());
            manager.addAxioms(copy, mutation.addedByMutation());
            byte[] content = rdfxml(copy);
            writeNew(Support.negativeFile(mutation.copyFileName()), content);
            mutantHashes.put(mutation.id(), sha256(content));
        }
        List<TestGroup> groups = List.of(new T04Reasoning(), new T05DlQueries(),
                new T06ActiveAndPassive(), new T07TwoGpus(), new T08NegativeVolume(),
                new T09MissingHasMemory(), new T10RoundTrip());
        Map<String,Object> outcomes = new LinkedHashMap<>();
        boolean allPassed = true;
        for (TestGroup group : groups) {
            boolean passed = false;
            String error = null;
            ByteArrayOutputStream bytes = new ByteArrayOutputStream();
            try (PrintStream log = new PrintStream(bytes, true, StandardCharsets.UTF_8)) {
                log.println("== " + group.name() + " ==");
                try { passed = group.run(log); }
                catch (Exception failure) { error = failure.toString(); failure.printStackTrace(log); }
                log.println(group.id() + ": " + (passed ? "PASS" : "FAIL"));
            }
            Path logPath = Support.resultsDir().resolve(group.id() + ".log");
            writeNew(logPath, bytes.toByteArray());
            Map<String,Object> outcome = new LinkedHashMap<>();
            outcome.put("passed", passed);
            outcome.put("error", error);
            outcome.put("note", group.note());
            outcome.put("log", root.relativize(logPath).toString());
            outcomes.put(group.id(), outcome);
            allPassed &= passed;
        }
        Map<String,Object> result = new LinkedHashMap<>();
        result.put("all_passed", allPassed);
        result.put("groups", outcomes);
        result.put("negative_copy_sha256", mutantHashes);
        result.put("ontology_sha256", sha256(Files.readAllBytes(Support.ontologyFile())));
        result.put("ontology_iri", finalOntology.getOntologyID().getOntologyIRI().isPresent() ? finalOntology.getOntologyID().getOntologyIRI().get().toString() : null);
        result.put("version_iri", finalOntology.getOntologyID().getVersionIRI().isPresent() ? finalOntology.getOntologyID().getVersionIRI().get().toString() : null);
        result.put("java", System.getProperty("java.version"));
        result.put("owl_api", VersionInfo.getVersionInfo().getVersion());
        result.put("hermit", Support.hermitJarVersion());
        return result;
    }

    public static void main(String[] args) {
        try {
            JsonNode request = JSON.readTree(System.in);
            String command = request.path("command").asText();
            Map<String,Object> result;
            if (command.equals("export")) result = export(request);
            else if (command.equals("acceptance")) result = acceptance(request);
            else throw new IllegalArgumentException("Unknown release command");
            System.out.println(JSON.writeValueAsString(result));
        } catch (Exception error) {
            System.err.println("RELEASE_ERROR: " + error);
            System.exit(2);
        }
    }
}
