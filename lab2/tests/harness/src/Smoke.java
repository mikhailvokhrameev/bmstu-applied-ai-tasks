import java.io.PrintStream;
import org.semanticweb.HermiT.ReasonerFactory;
import org.semanticweb.owlapi.apibinding.OWLManager;
import org.semanticweb.owlapi.model.IRI;
import org.semanticweb.owlapi.model.OWLClass;
import org.semanticweb.owlapi.model.OWLDataFactory;
import org.semanticweb.owlapi.model.OWLNamedIndividual;
import org.semanticweb.owlapi.model.OWLOntology;
import org.semanticweb.owlapi.model.OWLOntologyManager;
import org.semanticweb.owlapi.reasoner.OWLReasoner;

/** Toolchain check: HermiT must find a consistent ontology consistent and a contradictory one inconsistent. */
public class Smoke implements TestGroup {
    private static final String NS = "urn:smoke#";

    @Override
    public String name() {
        return "Smoke";
    }

    @Override
    public boolean run(PrintStream out) throws Exception {
        OWLOntologyManager m = OWLManager.createOWLOntologyManager();
        OWLDataFactory f = m.getOWLDataFactory();
        OWLClass a = f.getOWLClass(IRI.create(NS + "A"));
        OWLClass b = f.getOWLClass(IRI.create(NS + "B"));
        OWLNamedIndividual x = f.getOWLNamedIndividual(IRI.create(NS + "x"));

        OWLOntology o = m.createOntology(IRI.create("urn:smoke"));
        m.addAxiom(o, f.getOWLDisjointClassesAxiom(a, b));
        m.addAxiom(o, f.getOWLClassAssertionAxiom(a, x));

        boolean consistent = isConsistent(o);
        out.println("A disjoint B, x : A          -> consistent = " + consistent + " (expected true)");

        m.addAxiom(o, f.getOWLClassAssertionAxiom(b, x));
        boolean inconsistent = !isConsistent(o);
        out.println("A disjoint B, x : A, x : B   -> consistent = " + !inconsistent + " (expected false)");

        return consistent && inconsistent;
    }

    private static boolean isConsistent(OWLOntology o) {
        OWLReasoner r = new ReasonerFactory().createReasoner(o);
        try {
            return r.isConsistent();
        } finally {
            r.dispose();
        }
    }
}
