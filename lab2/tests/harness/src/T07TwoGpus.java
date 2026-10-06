import java.io.PrintStream;
import java.util.Set;
import java.util.TreeSet;
import org.semanticweb.owlapi.model.OWLAxiom;
import org.semanticweb.owlapi.model.OWLObjectPropertyAssertionAxiom;
import org.semanticweb.owlapi.model.OWLOntology;

/**
 * T07 (spec 4.4.4, 4.4.7): in a copy U01 uses two different GPUs (the GPUs are pairwise different via
 * DifferentIndividuals), violating {@code usesGPU exactly 1}; HermiT must report the copy inconsistent.
 */
public class T07TwoGpus extends NegativeCopyTest {
    private static final String MODEL = "U01";
    private static final String ORIGINAL_GPU = "GPU_G1";
    private static final String SECOND_GPU = "GPU_G2";

    @Override
    public String id() {
        return "T07";
    }

    @Override
    public String name() {
        return "T07 negative: model linked to two different GPUs (usesGPU exactly 1)";
    }

    @Override
    String copyFileName() {
        return "T07_two_gpus.owl";
    }

    @Override
    Set<OWLAxiom> addedByMutation() {
        return Set.of(Support.DF.getOWLObjectPropertyAssertionAxiom(
                Support.op("usesGPU"), Support.ind(MODEL), Support.ind(SECOND_GPU)));
    }

    @Override
    Set<OWLAxiom> removedByMutation() {
        return Set.of();
    }

    @Override
    void checkCopy(OWLOntology copy, Checks c, PrintStream out) {
        c.eq(MODEL + " usesGPU values in the copy", new TreeSet<>(Set.of(ORIGINAL_GPU, SECOND_GPU)), gpus(copy));
        out.println("  expected: inconsistent=true (usesGPU exactly 1 on VideoCardModel, GPUs pairwise different)");
        c.check("HermiT reports the copy inconsistent", !hermitConsistent(copy, out));
    }

    @Override
    void checkFinal(OWLOntology fin, Checks c, PrintStream out) {
        out.println("  expected: consistent=true");
        c.check("HermiT reports the final ontology consistent", hermitConsistent(fin, out));
        c.eq(MODEL + " usesGPU values in the final ontology", new TreeSet<>(Set.of(ORIGINAL_GPU)), gpus(fin));
        boolean twoGpuModel = false;
        for (String m : Oracle.MODELS) {
            Set<String> g = new TreeSet<>();
            for (OWLObjectPropertyAssertionAxiom ax : fin.getObjectPropertyAssertionAxioms(Support.ind(m))) {
                if (ax.getProperty().equals(Support.op("usesGPU"))) g.add(Support.local(ax.getObject().asOWLNamedIndividual().getIRI()));
            }
            if (g.size() != 1) twoGpuModel = true;
        }
        c.check("every model has exactly one asserted usesGPU value in the final ontology", !twoGpuModel);
    }

    private static Set<String> gpus(OWLOntology ont) {
        Set<String> values = new TreeSet<>();
        for (OWLObjectPropertyAssertionAxiom ax : ont.getObjectPropertyAssertionAxioms(Support.ind(MODEL))) {
            if (ax.getProperty().equals(Support.op("usesGPU"))) {
                values.add(Support.local(ax.getObject().asOWLNamedIndividual().getIRI()));
            }
        }
        return values;
    }

    @Override
    String summaryText() {
        return "copy inconsistent (usesGPU exactly 1), final consistent with one GPU per model";
    }
}
