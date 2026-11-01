import java.io.PrintStream;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import java.util.TreeSet;
import org.semanticweb.HermiT.ReasonerFactory;
import org.semanticweb.owlapi.model.OWLClass;
import org.semanticweb.owlapi.model.OWLOntology;
import org.semanticweb.owlapi.reasoner.OWLReasoner;
import org.semanticweb.owlapi.reasoner.OWLReasonerFactory;

/** T04 (spec 4.4.2, 4.4.6): HermiT finds the ontology consistent and every named class satisfiable. */
public class T04Reasoning implements TestGroup {
    private String note = "";

    @Override
    public String id() {
        return "T04";
    }

    @Override
    public String name() {
        return "T04 HermiT consistency and class satisfiability";
    }

    @Override
    public String note() {
        return note;
    }

    @Override
    public boolean run(PrintStream out) throws Exception {
        OWLOntology ont = Support.load(Support.ontologyFile().toFile());
        Checks c = new Checks(out);
        verify(ont, new ReasonerFactory(), c, out);
        note = c.summary() + "; HermiT " + Support.hermitJarVersion();
        return c.ok();
    }

    /** Reasoner-based checks on any ontology; {@code factory} chooses the reasoner (HermiT in this project). */
    static void verify(OWLOntology ont, OWLReasonerFactory factory, Checks c, PrintStream out) throws Exception {
        OWLReasoner reasoner = factory.createReasoner(ont);
        try {
            out.println("reasoner: " + reasoner.getReasonerName() + " " + reasoner.getReasonerVersion()
                    + " (self-reported; jar version " + Support.hermitJarVersion() + ")");
            if (!c.check("ontology is consistent (isConsistent)", reasoner.isConsistent())) return;

            Set<String> unsatisfiable = new TreeSet<>();
            reasoner.getUnsatisfiableClasses().getEntities().forEach(
                    cl -> unsatisfiable.add(cl.isOWLNothing() ? "owl:Nothing" : Support.local(cl.getIRI())));
            out.println("unsatisfiable classes (equivalent to owl:Nothing): " + unsatisfiable);
            c.eq("the only unsatisfiable class is owl:Nothing", Set.of("owl:Nothing"), unsatisfiable);

            List<String> unsat = new ArrayList<>();
            Set<String> checked = new TreeSet<>();
            for (OWLClass cl : ont.getClassesInSignature()) {
                if (cl.isOWLNothing()) continue;
                String local = cl.isOWLThing() ? "owl:Thing" : Support.local(cl.getIRI());
                boolean sat = reasoner.isSatisfiable(cl);
                checked.add(local + (sat ? "=sat" : "=UNSAT"));
                if (!sat) unsat.add(local);
            }
            out.println("per-class isSatisfiable: " + String.join(", ", checked));
            c.checkAll("every named class is individually satisfiable", checked.size(), unsat);

            List<String> notDisjoint = new ArrayList<>();
            List<String[]> pairs = Oracle.disjointPairs();
            for (String[] pair : pairs) {
                var axiom = Support.DF.getOWLDisjointClassesAxiom(Support.cls(pair[0]), Support.cls(pair[1]));
                if (!reasoner.isEntailed(axiom)) notDisjoint.add(pair[0] + " / " + pair[1]);
            }
            c.checkAll("reasoner entails disjointness of the required 4.4.2 pairs", pairs.size(), notDisjoint);
        } finally {
            reasoner.dispose();
        }
    }
}
