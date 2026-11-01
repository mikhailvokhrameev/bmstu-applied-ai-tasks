import java.io.PrintStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Set;
import java.util.TreeSet;
import org.semanticweb.HermiT.ReasonerFactory;
import org.semanticweb.owlapi.model.OWLAxiom;
import org.semanticweb.owlapi.model.OWLOntology;
import org.semanticweb.owlapi.reasoner.OWLReasoner;

/**
 * Template for the negative tests T06-T09 (spec Table 6): a defect copy under tests/negative/ must differ from the
 * final ontology ONLY by the intended mutation (axiom-set symmetric difference), the behaviour of HermiT / the
 * completeness card on the copy is checked by the subclass, and the final ontology must stay clean ("rollback").
 */
abstract class NegativeCopyTest implements TestGroup {
    private String note = "";

    /** File name of the copy in tests/negative/. */
    abstract String copyFileName();

    /** Axioms the copy has and the final ontology lacks. */
    abstract Set<OWLAxiom> addedByMutation();

    /** Axioms the final ontology has and the copy lacks. */
    abstract Set<OWLAxiom> removedByMutation();

    /** Behaviour on the defect copy (reasoner and/or completeness card). */
    abstract void checkCopy(OWLOntology copy, Checks c, PrintStream out) throws Exception;

    /** The final ontology: consistent, and none of the test facts is present. */
    abstract void checkFinal(OWLOntology finalOnt, Checks c, PrintStream out) throws Exception;

    /** One-line summary of what the test established, appended to the check counts in summary.json. */
    abstract String summaryText();

    @Override
    public String note() {
        return note;
    }

    @Override
    public final boolean run(PrintStream out) throws Exception {
        Path copyFile = Support.negativeFile(copyFileName());
        Checks c = new Checks(out);
        out.println("defect copy: tests/negative/" + copyFileName());
        if (!c.check("defect copy file exists", Files.isRegularFile(copyFile))) {
            note = c.summary();
            return false;
        }
        OWLOntology fin = Support.load(Support.ontologyFile().toFile());
        OWLOntology copy = Support.load(copyFile.toFile());

        out.println();
        out.println("-- the copy differs from ontology/videocard.owl only by the intended mutation");
        Set<OWLAxiom> added = new TreeSet<>(copy.getAxioms());
        added.removeAll(fin.getAxioms());
        Set<OWLAxiom> removed = new TreeSet<>(fin.getAxioms());
        removed.removeAll(copy.getAxioms());
        for (OWLAxiom ax : removed) out.println("    - " + ax);
        for (OWLAxiom ax : added) out.println("    + " + ax);
        c.eq("axioms only in the copy (+" + addedByMutation().size() + ")", new TreeSet<>(addedByMutation()), added);
        c.eq("axioms only in the final ontology (-" + removedByMutation().size() + ")",
                new TreeSet<>(removedByMutation()), removed);

        out.println();
        out.println("-- defect copy");
        checkCopy(copy, c, out);

        out.println();
        out.println("-- rollback: ontology/videocard.owl");
        checkFinal(fin, c, out);

        note = c.summary() + "; " + summaryText();
        return c.ok();
    }

    /** HermiT's isConsistent verdict for {@code ont}. */
    static boolean hermitConsistent(OWLOntology ont, PrintStream out) {
        OWLReasoner reasoner = new ReasonerFactory().createReasoner(ont);
        try {
            boolean consistent = reasoner.isConsistent();
            out.println("    HermiT " + Support.hermitJarVersion() + " isConsistent = " + consistent);
            return consistent;
        } catch (java.io.IOException e) {
            throw new IllegalStateException(e);
        } finally {
            reasoner.dispose();
        }
    }
}
