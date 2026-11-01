import java.io.PrintStream;
import java.util.List;
import java.util.Set;
import org.semanticweb.owlapi.model.OWLAxiom;
import org.semanticweb.owlapi.model.OWLOntology;

/**
 * T09 (spec 4.4.5, 4.4.7): in a copy U05 loses its hasMemory assertion. Under the open world assumption HermiT
 * stays consistent, so consistency alone does not count as completeness; the completeness card (T03 logic) must
 * report exactly that gap. The final ontology has the link and a clean card.
 */
public class T09MissingHasMemory extends NegativeCopyTest {
    private static final String MODEL = "U05";
    private static final String MEMORY = "Mem_6GiB_GDDR6";

    @Override
    public String id() {
        return "T09";
    }

    @Override
    public String name() {
        return "T09 negative: model without hasMemory (open world vs completeness card)";
    }

    @Override
    String copyFileName() {
        return "T09_missing_hasMemory.owl";
    }

    @Override
    Set<OWLAxiom> addedByMutation() {
        return Set.of();
    }

    @Override
    Set<OWLAxiom> removedByMutation() {
        return Set.of(Support.DF.getOWLObjectPropertyAssertionAxiom(
                Support.op("hasMemory"), Support.ind(MODEL), Support.ind(MEMORY)));
    }

    @Override
    void checkCopy(OWLOntology copy, Checks c, PrintStream out) {
        out.println("  expected: consistent=true (open world: U05 has some unknown memory configuration)");
        c.check("HermiT still reports the copy consistent (consistency is not completeness)", hermitConsistent(copy, out));

        T03CompletenessCard.Card card = T03CompletenessCard.build(copy);
        card.print(out);
        for (T03CompletenessCard.Problem p : card.problems) out.println("  card problem: " + p);
        c.eq("the card reports exactly one problem", 1, card.problems.size());
        c.eq("the problem is (" + MODEL + ", hasMemory, actual 0, expected 1)",
                List.of(new T03CompletenessCard.Problem(MODEL, "hasMemory", 0, "1")), card.problems);
    }

    @Override
    void checkFinal(OWLOntology fin, Checks c, PrintStream out) {
        out.println("  expected: consistent=true, completeness card without problems");
        c.check("HermiT reports the final ontology consistent", hermitConsistent(fin, out));
        c.check(MODEL + " hasMemory " + MEMORY + " is asserted in the final ontology", fin.containsAxiom(
                Support.DF.getOWLObjectPropertyAssertionAxiom(Support.op("hasMemory"), Support.ind(MODEL), Support.ind(MEMORY))));
        T03CompletenessCard.Card card = T03CompletenessCard.build(fin);
        for (T03CompletenessCard.Problem p : card.problems) out.println("  card problem: " + p);
        c.eq("the card of the final ontology has zero problems", 0, card.problems.size());
    }

    @Override
    String summaryText() {
        return "copy consistent (open world) but card flags U05 hasMemory 0 vs 1; final card clean";
    }
}
