import java.io.OutputStream;
import java.io.PrintStream;
import java.nio.ByteBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;
import org.semanticweb.HermiT.ReasonerFactory;
import org.semanticweb.owlapi.apibinding.OWLManager;
import org.semanticweb.owlapi.formats.RDFXMLDocumentFormat;
import org.semanticweb.owlapi.io.FileDocumentSource;
import org.semanticweb.owlapi.model.AxiomType;
import org.semanticweb.owlapi.model.MissingImportHandlingStrategy;
import org.semanticweb.owlapi.model.OWLAnnotationAssertionAxiom;
import org.semanticweb.owlapi.model.OWLAxiom;
import org.semanticweb.owlapi.model.OWLLiteral;
import org.semanticweb.owlapi.model.OWLOntology;
import org.semanticweb.owlapi.model.OWLOntologyLoaderConfiguration;

/**
 * T10 (spec Table 6, 4.6.4): the final ontology survives a save/reload round trip. videocard.owl is loaded, saved
 * with OWL API as RDF/XML (UTF-8) to tests/results/T10_resaved.owl (regenerated every run, not committed) and
 * reloaded from that file. Entity counts per type, the complete axiom sets (logical axioms, declarations and
 * annotation assertions) and the ontology annotations must be EQUAL as sets, ontology IRI and version IRI must match
 * and no imports may exist. Then the T04 (reasoning) and T05 (DL queries) logic is re-run on the reloaded copy.
 *
 * <p>Both loads use MissingImportHandlingStrategy.THROW_EXCEPTION, so an unresolvable import would fail the load
 * instead of being silently dropped. Strict equality is required: no ontology-header difference is tolerated.
 * The Cyrillic rdfs:label/rdfs:comment literals are covered by the axiom-set equality (annotation assertions compare
 * their literal values); in addition the file is checked to be valid UTF-8 containing every ru label verbatim.
 */
public class T10RoundTrip implements TestGroup {
    static final String RESAVED_NAME = "T10_resaved.owl";

    private String note = "";

    @Override
    public String id() {
        return "T10";
    }

    @Override
    public String name() {
        return "T10 RDF/XML save and reload round trip";
    }

    @Override
    public String note() {
        return note;
    }

    static Path resavedFile() {
        return Support.resultsDir().resolve(RESAVED_NAME);
    }

    /** Loader configuration that fails on an unresolvable import instead of ignoring it. */
    private static OWLOntologyLoaderConfiguration strictConfig() {
        return new OWLOntologyLoaderConfiguration()
                .setMissingImportHandlingStrategy(MissingImportHandlingStrategy.THROW_EXCEPTION);
    }

    @Override
    public boolean run(PrintStream out) throws Exception {
        Checks c = new Checks(out);
        Path original = Support.ontologyFile();
        Path resaved = resavedFile();
        Files.createDirectories(resaved.getParent());
        Files.deleteIfExists(resaved); // never leave a stale copy from an earlier run

        OWLOntology before = OWLManager.createOWLOntologyManager()
                .loadOntologyFromOntologyDocument(new FileDocumentSource(original.toFile()), strictConfig());
        c.check("videocard.owl loads (missing imports = THROW_EXCEPTION)", true);

        var manager = before.getOWLOntologyManager();
        try (OutputStream os = Files.newOutputStream(resaved)) {
            manager.saveOntology(before, new RDFXMLDocumentFormat(), os);
        }
        out.println("saved: tests/results/" + RESAVED_NAME + " (" + Files.size(resaved) + " bytes, RDF/XML)");

        OWLOntology after = OWLManager.createOWLOntologyManager()
                .loadOntologyFromOntologyDocument(new FileDocumentSource(resaved.toFile()), strictConfig());
        c.check("re-saved file loads (missing imports = THROW_EXCEPTION)", true);

        checkUtf8(before, resaved, c);
        compare(before, after, c, out);

        out.println("-- T04 logic on the reloaded copy --");
        T04Reasoning.verify(after, new ReasonerFactory(), c, out);
        out.println("-- T05 logic on the reloaded copy --");
        T05DlQueries.verify(after, new ReasonerFactory(), Support.expectedFile(), c, out);

        note = c.summary() + "; " + before.getAxiomCount() + " axioms identical after RDF/XML round trip";
        return c.ok();
    }

    /** The saved file is strictly valid UTF-8, declares it, and contains every Russian label unescaped. */
    private static void checkUtf8(OWLOntology source, Path file, Checks c) throws Exception {
        byte[] bytes = Files.readAllBytes(file);
        String text = null;
        try {
            text = StandardCharsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT)
                    .onUnmappableCharacter(CodingErrorAction.REPORT).decode(ByteBuffer.wrap(bytes)).toString();
        } catch (CharacterCodingException e) {
            c.check("re-saved file is valid UTF-8", false, e.toString());
        }
        if (text == null) return;
        c.check("re-saved file is valid UTF-8", true);
        // OWL API writes a bare <?xml version="1.0"?>; per the XML spec an absent encoding means UTF-8.
        String decl = text.startsWith("<?xml") ? text.substring(0, text.indexOf("?>") + 2) : "";
        c.check("XML declaration is present and declares no encoding other than UTF-8 (no BOM)",
                !decl.isEmpty() && (!decl.contains("encoding") || decl.toUpperCase().contains("UTF-8")),
                "declaration: " + decl);
        Set<String> missing = new TreeSet<>();
        int labels = 0;
        for (OWLAnnotationAssertionAxiom ax : source.getAxioms(AxiomType.ANNOTATION_ASSERTION)) {
            if (!ax.getProperty().isLabel() || !(ax.getValue() instanceof OWLLiteral)) continue;
            OWLLiteral lit = (OWLLiteral) ax.getValue();
            if (!"ru".equals(lit.getLang())) continue;
            labels++;
            if (!text.contains(lit.getLiteral())) missing.add(lit.getLiteral());
        }
        c.check("re-saved file has ru labels (>0)", labels > 0);
        c.check("every ru rdfs:label appears verbatim in the re-saved file (" + labels + " labels)",
                missing.isEmpty(), "missing " + missing);
    }

    /** Strict comparison of two ontologies; differences are printed (first 10 per direction). */
    static void compare(OWLOntology a, OWLOntology b, Checks c, PrintStream out) {
        Map<String, int[]> counts = new LinkedHashMap<>();
        counts.put("classes", new int[] {a.getClassesInSignature().size(), b.getClassesInSignature().size()});
        counts.put("object properties",
                new int[] {a.getObjectPropertiesInSignature().size(), b.getObjectPropertiesInSignature().size()});
        counts.put("data properties",
                new int[] {a.getDataPropertiesInSignature().size(), b.getDataPropertiesInSignature().size()});
        counts.put("annotation properties",
                new int[] {a.getAnnotationPropertiesInSignature().size(), b.getAnnotationPropertiesInSignature().size()});
        counts.put("named individuals",
                new int[] {a.getIndividualsInSignature().size(), b.getIndividualsInSignature().size()});
        for (Map.Entry<String, int[]> e : counts.entrySet()) {
            int[] v = e.getValue();
            out.println("entities " + e.getKey() + ": before=" + v[0] + " after=" + v[1]);
            c.check("entity count equal: " + e.getKey() + " (" + v[0] + ")", v[0] == v[1], v[0] + " vs " + v[1]);
        }

        Set<OWLAxiom> axA = a.getAxioms();
        Set<OWLAxiom> axB = b.getAxioms();
        out.println("axioms (logical + declarations + annotation assertions): before=" + axA.size()
                + " after=" + axB.size());
        Set<OWLAxiom> lost = new TreeSet<>(axA);
        lost.removeAll(axB);
        Set<OWLAxiom> gained = new TreeSet<>(axB);
        gained.removeAll(axA);
        printDiff(out, "only before", lost);
        printDiff(out, "only after", gained);
        c.check("axiom sets are equal (" + axA.size() + " axioms)", axA.equals(axB),
                lost.size() + " lost, " + gained.size() + " gained");

        c.check("ontology annotations are equal", a.getAnnotations().equals(b.getAnnotations()),
                a.getAnnotations() + " vs " + b.getAnnotations());
        c.check("ontology IRI equal", a.getOntologyID().getOntologyIRI().equals(b.getOntologyID().getOntologyIRI()),
                a.getOntologyID().getOntologyIRI() + " vs " + b.getOntologyID().getOntologyIRI());
        c.check("version IRI equal", a.getOntologyID().getVersionIRI().equals(b.getOntologyID().getVersionIRI()),
                a.getOntologyID().getVersionIRI() + " vs " + b.getOntologyID().getVersionIRI());
        c.check("no imports in either copy", a.getImportsDeclarations().isEmpty() && b.getImportsDeclarations().isEmpty()
                && a.getImports().isEmpty() && b.getImports().isEmpty());
    }

    private static void printDiff(PrintStream out, String label, Set<OWLAxiom> axioms) {
        int n = 0;
        for (OWLAxiom ax : axioms) {
            if (n++ == 10) {
                out.println("  " + label + ": ... " + (axioms.size() - 10) + " more");
                break;
            }
            out.println("  " + label + ": " + ax);
        }
    }
}
