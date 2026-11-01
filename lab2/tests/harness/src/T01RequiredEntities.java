import java.io.PrintStream;
import java.util.ArrayList;
import java.util.List;
import org.semanticweb.owlapi.model.OWLEntity;
import org.semanticweb.owlapi.model.OWLOntology;

/**
 * T01 (spec 4.1.1-4.1.4), automatic part: every required class and property of Tables 1-3 is declared.
 * The manual sheet-vs-diagram reconciliation is recorded in docs/ontology_description.md (Task 7).
 */
public class T01RequiredEntities implements TestGroup {
    private String note = "";

    @Override
    public String id() {
        return "T01";
    }

    @Override
    public String name() {
        return "T01 required classes and properties (automatic part)";
    }

    @Override
    public String note() {
        return note;
    }

    @Override
    public boolean run(PrintStream out) throws Exception {
        OWLOntology ont = Support.load(Support.ontologyFile().toFile());
        Checks c = new Checks(out);
        verify(ont, c);
        out.println();
        out.println("Status: AUTOMATIC PART " + (c.ok() ? "PASS" : "FAIL") + ". The manual reconciliation of the"
                + " description, vocabulary and both diagrams (4.1.1-4.1.4) is recorded in"
                + " docs/ontology_description.md (written in Task 7) and is not evaluated here.");
        note = c.summary() + "; manual reconciliation recorded in docs/ontology_description.md";
        return c.ok();
    }

    /** Declared-entity checks against the {@link Oracle} tables. */
    static void verify(OWLOntology ont, Checks c) {
        List<String> classes = new ArrayList<>(Oracle.CLASSES);
        classes.addAll(Oracle.DEFINED_CLASSES);
        c.checkAll("required classes declared: " + String.join(", ", classes), classes.size(),
                undeclared(ont, classes, Kind.CLASS));

        List<String> objectProps = new ArrayList<>();
        for (String[] p : Oracle.OBJECT_PROPERTIES) objectProps.add(p[0]);
        c.checkAll("required object properties declared: " + String.join(", ", objectProps), objectProps.size(),
                undeclared(ont, objectProps, Kind.OBJECT_PROPERTY));

        c.checkAll("required data properties declared: " + String.join(", ", Oracle.DATA_PROPERTIES),
                Oracle.DATA_PROPERTIES.size(), undeclared(ont, Oracle.DATA_PROPERTIES, Kind.DATA_PROPERTY));
    }

    private enum Kind { CLASS, OBJECT_PROPERTY, DATA_PROPERTY }

    private static List<String> undeclared(OWLOntology ont, List<String> names, Kind kind) {
        List<String> missing = new ArrayList<>();
        for (String n : names) {
            OWLEntity e;
            switch (kind) {
                case CLASS:
                    e = Support.cls(n);
                    break;
                case OBJECT_PROPERTY:
                    e = Support.op(n);
                    break;
                default:
                    e = Support.dp(n);
            }
            if (ont.getDeclarationAxioms(e).isEmpty()) missing.add(n + " (no " + kind + " declaration)");
        }
        return missing;
    }
}
