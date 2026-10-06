import java.io.PrintStream;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;
import org.semanticweb.owlapi.model.OWLClassAssertionAxiom;
import org.semanticweb.owlapi.model.OWLDataPropertyAssertionAxiom;
import org.semanticweb.owlapi.model.OWLLiteral;
import org.semanticweb.owlapi.model.OWLNamedIndividual;
import org.semanticweb.owlapi.model.OWLObjectPropertyAssertionAxiom;
import org.semanticweb.owlapi.model.OWLOntology;

/**
 * T03 (spec 4.2.5, 4.4.4-4.4.5): completeness card of the eight models, read from ASSERTED axioms only
 * (no reasoner). {@link #build(OWLOntology)} is reusable on any ontology, e.g. mutated copies (Task 5).
 */
public class T03CompletenessCard implements TestGroup {
    /** The five single-valued links: exactly one asserted value each. */
    static final List<String> SINGLE_LINKS =
            List.of("usesGPU", "hasMemory", "hasCooling", "hasInterface", "producedByManufacturer");
    /** The multi-valued link: at least one asserted value. */
    static final String MULTI_LINK = "hasVideoOutput";
    /** The six link columns of the card. */
    static final List<String> LINKS = List.of(
            "usesGPU", "hasMemory", "hasCooling", "hasInterface", "producedByManufacturer", MULTI_LINK);
    /** Numeric attributes on the model itself. */
    static final List<String> MODEL_ATTRIBUTES = List.of("powerW", "lengthMM");
    /** Numeric attributes on the linked components: attribute, link through which the component is reached. */
    static final String[][] COMPONENT_ATTRIBUTES = {
        {"volumeGiB", "hasMemory"}, {"busWidthBit", "hasMemory"}, {"frequencyMHz", "usesGPU"}, {"fanCount", "hasCooling"},
    };

    /** A violated expectation of the card. {@code expected} is "1" (exactly one), ">=1" or "0". */
    record Problem(String subject, String property, int actual, String expected) {
        @Override
        public String toString() {
            return subject + " " + property + ": " + actual + " asserted value(s), expected " + expected;
        }
    }

    /** The card: value counts per model and column, plus the list of problems found. */
    static final class Card {
        /** model -> column -> count; column order: the 6 links, then powerW, lengthMM, volumeGiB, busWidthBit,
         * frequencyMHz, fanCount. A component attribute count is -1 when the model has no single linked component. */
        final Map<String, Map<String, Integer>> counts = new TreeMap<>();
        final List<Problem> problems = new ArrayList<>();

        List<String> columns() {
            List<String> cols = new ArrayList<>(LINKS);
            cols.addAll(MODEL_ATTRIBUTES);
            for (String[] a : COMPONENT_ATTRIBUTES) cols.add(a[0]);
            return cols;
        }

        boolean complete() {
            return problems.isEmpty();
        }

        void print(PrintStream out) {
            List<String> cols = columns();
            out.println("Completeness card (cell = number of asserted values; '*' marks a violation; "
                    + "'-' = component not reachable through a single link)");
            StringBuilder head = new StringBuilder(String.format("  %-5s", "model"));
            for (String col : cols) head.append(String.format(" %" + width(col) + "s", col));
            out.println(head);
            for (Map.Entry<String, Map<String, Integer>> row : counts.entrySet()) {
                StringBuilder line = new StringBuilder(String.format("  %-5s", row.getKey()));
                for (String col : cols) {
                    int n = row.getValue().getOrDefault(col, 0);
                    String cell = n < 0 ? "-" : Integer.toString(n);
                    if (violates(row.getKey(), col)) cell += "*";
                    line.append(String.format(" %" + width(col) + "s", cell));
                }
                out.println(line);
            }
        }

        private int width(String col) {
            return Math.max(col.length(), 3);
        }

        private boolean violates(String model, String col) {
            for (Problem p : problems) if (p.subject().equals(model) && p.property().startsWith(col)) return true;
            return false;
        }
    }

    private String note = "";

    @Override
    public String id() {
        return "T03";
    }

    @Override
    public String name() {
        return "T03 completeness card of U01..U08 (asserted axioms only)";
    }

    @Override
    public String note() {
        return note;
    }

    @Override
    public boolean run(PrintStream out) throws Exception {
        OWLOntology ont = Support.load(Support.ontologyFile().toFile());
        Card card = build(ont);
        card.print(out);
        out.println();
        for (Problem p : card.problems) out.println("  [FAIL] " + p);
        out.println("Rule: exactly 1 value for " + String.join(", ", SINGLE_LINKS) + "; >= 1 for " + MULTI_LINK
                + "; exactly 1 for powerW, lengthMM (model), volumeGiB, busWidthBit (memory), frequencyMHz (GPU), "
                + "fanCount (cooling).");
        Checks c = new Checks(out);
        c.check("every model U01..U08 is complete (" + card.problems.size() + " problem(s))", card.complete());
        note = card.complete() ? "8 models x 12 columns complete, asserted axioms only"
                : card.problems.size() + " problem(s) in the completeness card";
        return card.complete();
    }

    /** Builds the card from the asserted axioms of {@code ont}; the VideoCardModel set must be exactly U01..U08. */
    static Card build(OWLOntology ont) {
        Card card = new Card();
        Set<String> models = new TreeSet<>();
        for (OWLClassAssertionAxiom ax : ont.getClassAssertionAxioms(Support.cls("VideoCardModel"))) {
            if (ax.getIndividual().isNamed()) models.add(Support.local(ax.getIndividual().asOWLNamedIndividual().getIRI()));
        }
        for (String expected : Oracle.MODELS) {
            if (!models.contains(expected)) card.problems.add(new Problem(expected, "ClassAssertion VideoCardModel", 0, "1"));
        }
        for (String found : models) {
            if (!Oracle.MODELS.contains(found)) card.problems.add(new Problem(found, "unexpected VideoCardModel", 1, "0"));
        }
        Set<String> rows = new TreeSet<>(models);
        rows.addAll(Oracle.MODELS);

        for (String model : rows) {
            Map<String, Integer> row = new LinkedHashMap<>();
            card.counts.put(model, row);
            OWLNamedIndividual m = Support.ind(model);

            Map<String, Set<OWLNamedIndividual>> linked = new LinkedHashMap<>();
            for (String link : LINKS) {
                Set<OWLNamedIndividual> values = linkValues(ont, m, link);
                linked.put(link, values);
                row.put(link, values.size());
                boolean single = SINGLE_LINKS.contains(link);
                if (single ? values.size() != 1 : values.isEmpty()) {
                    card.problems.add(new Problem(model, link, values.size(), single ? "1" : ">=1"));
                }
            }
            for (String attr : MODEL_ATTRIBUTES) {
                int n = attributeValues(ont, m, attr);
                row.put(attr, n);
                if (n != 1) card.problems.add(new Problem(model, attr, n, "1"));
            }
            for (String[] ca : COMPONENT_ATTRIBUTES) {
                Set<OWLNamedIndividual> components = linked.get(ca[1]);
                if (components.size() != 1) {
                    row.put(ca[0], -1);
                    continue; // the missing/duplicate link is already a problem of the model
                }
                OWLNamedIndividual component = components.iterator().next();
                int n = attributeValues(ont, component, ca[0]);
                row.put(ca[0], n);
                if (n != 1) {
                    card.problems.add(new Problem(model, ca[0] + " of " + Support.local(component.getIRI()), n, "1"));
                }
            }
        }
        return card;
    }

    /** Distinct named individuals asserted as values of {@code link} for {@code subject}. */
    private static Set<OWLNamedIndividual> linkValues(OWLOntology ont, OWLNamedIndividual subject, String link) {
        Set<OWLNamedIndividual> values = new TreeSet<>();
        for (OWLObjectPropertyAssertionAxiom ax : ont.getObjectPropertyAssertionAxioms(subject)) {
            if (ax.getProperty().equals(Support.op(link)) && ax.getObject().isNamed()) {
                values.add(ax.getObject().asOWLNamedIndividual());
            }
        }
        return values;
    }

    /** Number of distinct literals asserted for {@code attribute} on {@code subject}. */
    private static int attributeValues(OWLOntology ont, OWLNamedIndividual subject, String attribute) {
        Set<OWLLiteral> values = new TreeSet<>();
        for (OWLDataPropertyAssertionAxiom ax : ont.getDataPropertyAssertionAxioms(subject)) {
            if (ax.getProperty().equals(Support.dp(attribute))) values.add(ax.getObject());
        }
        return values.size();
    }
}
