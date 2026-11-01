import java.io.PrintStream;
import java.util.Set;
import org.semanticweb.owlapi.model.OWLAxiom;
import org.semanticweb.owlapi.model.OWLClassAssertionAxiom;
import org.semanticweb.owlapi.model.OWLOntology;

/**
 * T06 (spec 4.4.2, 4.4.6): in a copy one individual is both ActiveCooling and PassiveCooling (disjoint classes);
 * HermiT must report the copy inconsistent. The final ontology stays consistent and free of the test fact.
 * Doubles as the permanent negative control "HermiT does detect inconsistency".
 */
public class T06ActiveAndPassive extends NegativeCopyTest {
    private static final String COOLING = "Cooling_Active_2fan";

    @Override
    public String id() {
        return "T06";
    }

    @Override
    public String name() {
        return "T06 negative: individual in ActiveCooling and PassiveCooling";
    }

    @Override
    String copyFileName() {
        return "T06_active_and_passive.owl";
    }

    @Override
    Set<OWLAxiom> addedByMutation() {
        return Set.of(Support.DF.getOWLClassAssertionAxiom(Support.cls("PassiveCooling"), Support.ind(COOLING)));
    }

    @Override
    Set<OWLAxiom> removedByMutation() {
        return Set.of();
    }

    @Override
    void checkCopy(OWLOntology copy, Checks c, PrintStream out) {
        c.check(COOLING + " is asserted ActiveCooling and PassiveCooling in the copy",
                hasType(copy, "ActiveCooling") && hasType(copy, "PassiveCooling"));
        out.println("  expected: inconsistent=true (ActiveCooling and PassiveCooling are disjoint)");
        boolean consistent = hermitConsistent(copy, out);
        c.check("HermiT reports the copy inconsistent (negative control: the reasoner detects inconsistency)",
                !consistent);
    }

    @Override
    void checkFinal(OWLOntology fin, Checks c, PrintStream out) {
        out.println("  expected: consistent=true");
        c.check("HermiT reports the final ontology consistent", hermitConsistent(fin, out));
        c.check(COOLING + " is not asserted PassiveCooling in the final ontology", !hasType(fin, "PassiveCooling"));
        c.check(COOLING + " is still asserted ActiveCooling in the final ontology", hasType(fin, "ActiveCooling"));
        boolean anyActiveAndPassive = false;
        for (OWLClassAssertionAxiom ax : fin.getClassAssertionAxioms(Support.cls("PassiveCooling"))) {
            if (ax.getIndividual().isNamed() && fin.containsAxiom(Support.DF.getOWLClassAssertionAxiom(
                    Support.cls("ActiveCooling"), ax.getIndividual()))) anyActiveAndPassive = true;
        }
        c.check("no individual is asserted both ActiveCooling and PassiveCooling in the final ontology",
                !anyActiveAndPassive);
    }

    private static boolean hasType(OWLOntology ont, String cls) {
        return ont.containsAxiom(Support.DF.getOWLClassAssertionAxiom(Support.cls(cls), Support.ind(COOLING)));
    }

    @Override
    String summaryText() {
        return "copy inconsistent (HermiT negative control), final consistent and clean";
    }
}
