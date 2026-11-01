import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.PrintStream;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;
import org.semanticweb.HermiT.ReasonerFactory;
import org.semanticweb.owlapi.apibinding.OWLManager;
import org.semanticweb.owlapi.expression.ShortFormEntityChecker;
import org.semanticweb.owlapi.model.OWLClassExpression;
import org.semanticweb.owlapi.model.OWLNamedIndividual;
import org.semanticweb.owlapi.model.OWLOntology;
import org.semanticweb.owlapi.reasoner.OWLReasoner;
import org.semanticweb.owlapi.reasoner.OWLReasonerFactory;
import org.semanticweb.owlapi.util.BidirectionalShortFormProvider;
import org.semanticweb.owlapi.util.BidirectionalShortFormProviderAdapter;
import org.semanticweb.owlapi.util.SimpleShortFormProvider;
import org.semanticweb.owlapi.util.mansyntax.ManchesterOWLSyntaxParser;

/**
 * T05 (spec 4.3, 4.4.3): the eight control questions as Manchester-syntax DL queries (local names, as typed in
 * the Protege DL Query tab), answered by HermiT and compared for exact set equality with tests/expected.json.
 */
public class T05DlQueries implements TestGroup {
    /** A query template; "%s" is replaced by each argument local name (templates without "%s" have no argument). */
    private record Question(String id, String template, List<String> arguments) {}

    /** The literal argument sets the questions must cover: expected.json must contain exactly these keys. */
    private static final List<Question> PARAMETRIC = List.of(
            new Question("Q1", "VideoCardModel and producedByManufacturer value %s", List.of("P1", "P2")),
            new Question("Q2", "VideoCardModel and usesGPU value %s",
                    List.of("GPU_G1", "GPU_G2", "GPU_G3", "GPU_G4", "GPU_G5")),
            new Question("Q4", "VideoCardModel and hasMemory some (hasMemoryType value %s)",
                    List.of("GDDR5", "GDDR6", "GDDR6X")),
            new Question("Q6", "VideoCardModel and hasVideoOutput value %s",
                    List.of("DVI", "DisplayPort", "HDMI", "VGA")),
            new Question("Q7", "VideoCardModel and hasInterface value %s",
                    List.of("PCIe_3_0_x16", "PCIe_4_0_x16", "PCIe_5_0_x16")));

    /** Argument-less questions: id, defined-class query, equivalent raw expression. */
    private static final String[][] DEFINED = {
        {"Q3", "CardWith8GBMemory", "VideoCardModel and hasMemory some (volumeGiB some xsd:integer[>= 8])"},
        {"Q5", "CardWithActiveCooling", "VideoCardModel and hasCooling some ActiveCooling"},
        {"Q8", "CardWith8GBMemory and CardWithActiveCooling",
            "VideoCardModel and hasMemory some (volumeGiB some xsd:integer[>= 8]) and hasCooling some ActiveCooling"},
    };

    private String note = "";

    @Override
    public String id() {
        return "T05";
    }

    @Override
    public String name() {
        return "T05 eight DL queries vs tests/expected.json";
    }

    @Override
    public String note() {
        return note;
    }

    @Override
    public boolean run(PrintStream out) throws Exception {
        OWLOntology ont = Support.load(Support.ontologyFile().toFile());
        Checks c = new Checks(out);
        verify(ont, new ReasonerFactory(), Support.expectedFile(), c, out);
        note = c.summary() + "; exact set equality with expected.json";
        return c.ok();
    }

    /** Runs all queries on {@code ont} and compares with the expected sets in {@code expectedJson}. */
    static void verify(OWLOntology ont, OWLReasonerFactory factory, Path expectedJson, Checks c, PrintStream out)
            throws Exception {
        JsonNode questions = new ObjectMapper().readTree(expectedJson.toFile()).path("questions");

        checkNoAssertedMembership(ont, c);

        BidirectionalShortFormProvider shortForms = new BidirectionalShortFormProviderAdapter(
                ont.getOWLOntologyManager(), Collections.singleton(ont), new SimpleShortFormProvider());
        OWLReasoner reasoner = factory.createReasoner(ont);
        try {
            if (!c.check("ontology is consistent (queries are meaningful)", reasoner.isConsistent())) return;

            for (Question q : PARAMETRIC) {
                JsonNode expected = questions.path(q.id()).path("expected");
                Map<String, Set<String>> byArgument = argumentMap(expected);
                c.eq(q.id() + ": expected.json covers exactly the arguments " + q.arguments(),
                        new TreeSet<>(q.arguments()), new TreeSet<>(byArgument.keySet()));
                for (String arg : q.arguments()) {
                    compare(c, out, ont, reasoner, shortForms, q.id() + " [" + arg + "]",
                            String.format(q.template(), arg), byArgument.getOrDefault(arg, Set.of()));
                }
                checkRepresentative(c, questions.path(q.id()), byArgument);
            }
            for (String[] d : DEFINED) {
                JsonNode expectedNode = questions.path(d[0]).path("expected");
                Set<String> expected = new TreeSet<>();
                expectedNode.forEach(n -> expected.add(n.asText()));
                c.check(d[0] + ": expected.json has a non-empty list", !expected.isEmpty());
                compare(c, out, ont, reasoner, shortForms, d[0] + " (defined classes)", d[1], expected);
                compare(c, out, ont, reasoner, shortForms, d[0] + " (raw cross-check)", d[2], expected);
            }
        } finally {
            reasoner.dispose();
        }
    }

    /** The two defined classes must get their members by inference: no asserted ClassAssertion for them. */
    private static void checkNoAssertedMembership(OWLOntology ont, Checks c) {
        for (String defined : Oracle.DEFINED_CLASSES) {
            int n = ont.getClassAssertionAxioms(Support.cls(defined)).size();
            c.check("no ClassAssertion axiom for " + defined + " (found " + n + "); membership must be inferred", n == 0);
        }
    }

    private static Map<String, Set<String>> argumentMap(JsonNode expected) {
        Map<String, Set<String>> map = new LinkedHashMap<>();
        for (Iterator<Map.Entry<String, JsonNode>> it = expected.fields(); it.hasNext(); ) {
            Map.Entry<String, JsonNode> e = it.next();
            Set<String> members = new TreeSet<>();
            e.getValue().forEach(n -> members.add(n.asText()));
            map.put(e.getKey(), members);
        }
        return map;
    }

    /** The documented positive/negative example of the representative argument must agree with the expected set. */
    private static void checkRepresentative(Checks c, JsonNode question, Map<String, Set<String>> byArgument) {
        String rep = question.path("representative").asText();
        Set<String> members = byArgument.getOrDefault(rep, Set.of());
        String pos = question.path("positive_example").asText();
        String neg = question.path("negative_example").asText();
        c.check(question.path("question").asText() + ": representative " + rep + " has positive example " + pos
                + " (member) and negative example " + neg + " (non-member)",
                members.contains(pos) && !members.contains(neg), "expected set " + members);
    }

    private static void compare(Checks c, PrintStream out, OWLOntology ont, OWLReasoner reasoner,
            BidirectionalShortFormProvider shortForms, String label, String query, Set<String> expected) {
        Set<String> actual = new TreeSet<>();
        String error = null;
        try {
            OWLClassExpression expression = parse(ont, shortForms, query);
            for (OWLNamedIndividual i : reasoner.getInstances(expression, false).getFlattened()) {
                actual.add(Support.local(i.getIRI()));
            }
        } catch (RuntimeException e) {
            error = e.toString();
        }
        out.println(label);
        out.println("    query:    " + query);
        out.println("    expected: " + new ArrayList<>(new TreeSet<>(expected)));
        out.println("    actual:   " + new ArrayList<>(actual) + (error != null ? "  (query failed: " + error + ")" : ""));
        c.check(label + " exact set equality", error == null && expected.equals(actual),
                "expected " + new TreeSet<>(expected) + " but got " + actual);
    }

    private static OWLClassExpression parse(OWLOntology ont, BidirectionalShortFormProvider shortForms, String query) {
        ManchesterOWLSyntaxParser parser = OWLManager.createManchesterParser();
        parser.setStringToParse(query);
        parser.setDefaultOntology(ont);
        parser.setOWLEntityChecker(new ShortFormEntityChecker(shortForms));
        return parser.parseClassExpression();
    }
}
