import java.io.PrintStream;
import java.util.Set;
import java.util.TreeSet;
import org.semanticweb.HermiT.ReasonerFactory;
import org.semanticweb.owlapi.model.OWLAxiom;
import org.semanticweb.owlapi.model.OWLDataPropertyAssertionAxiom;
import org.semanticweb.owlapi.model.OWLDataPropertyRangeAxiom;
import org.semanticweb.owlapi.model.OWLLiteral;
import org.semanticweb.owlapi.model.OWLOntology;
import org.semanticweb.owlapi.reasoner.OWLReasoner;
import org.semanticweb.owlapi.vocab.OWL2Datatype;

/**
 * T08 (spec 4.2.3): in a copy the volume of Mem_4GiB_GDDR5 is REPLACED by "-8"^^xsd:integer, outside the range
 * xsd:positiveInteger; HermiT must report the copy inconsistent. volumeGiB stays single-valued, so functionality
 * is not the cause; the test also proves this by dropping the range axiom from a throwaway in-memory variant.
 */
public class T08NegativeVolume extends NegativeCopyTest {
    private static final String CONFIG = "Mem_4GiB_GDDR5";

    private static OWLLiteral original() {
        return Support.DF.getOWLLiteral("4", OWL2Datatype.XSD_POSITIVE_INTEGER);
    }

    private static OWLLiteral negative() {
        return Support.DF.getOWLLiteral("-8", OWL2Datatype.XSD_INTEGER);
    }

    @Override
    public String id() {
        return "T08";
    }

    @Override
    public String name() {
        return "T08 negative: negative volumeGiB typed xsd:integer vs range xsd:positiveInteger";
    }

    @Override
    String copyFileName() {
        return "T08_negative_volume.owl";
    }

    @Override
    Set<OWLAxiom> addedByMutation() {
        return Set.of(Support.DF.getOWLDataPropertyAssertionAxiom(Support.dp("volumeGiB"), Support.ind(CONFIG), negative()));
    }

    @Override
    Set<OWLAxiom> removedByMutation() {
        return Set.of(Support.DF.getOWLDataPropertyAssertionAxiom(Support.dp("volumeGiB"), Support.ind(CONFIG), original()));
    }

    @Override
    void checkCopy(OWLOntology copy, Checks c, PrintStream out) throws Exception {
        Set<String> values = volumes(copy);
        out.println("  volumeGiB of " + CONFIG + " in the copy: " + values);
        c.eq("exactly one volumeGiB value (replaced, not added: functionality is not violated)",
                new TreeSet<>(Set.of("\"-8\"^^xsd:integer")), values);
        out.println("  expected: inconsistent=true (value -8 is not in the range xsd:positiveInteger)");
        c.check("HermiT reports the copy inconsistent", !hermitConsistent(copy, out));

        // Throwaway variant: same copy without DataPropertyRange(volumeGiB xsd:positiveInteger).
        OWLOntology variant = Support.load(Support.negativeFile(copyFileName()).toFile());
        Set<OWLDataPropertyRangeAxiom> ranges = variant.getDataPropertyRangeAxioms(Support.dp("volumeGiB"));
        c.eq("the copy has one DataPropertyRange axiom for volumeGiB", 1, ranges.size());
        variant.getOWLOntologyManager().removeAxioms(variant, ranges);
        out.println("  in-memory variant without the volumeGiB range axiom (not written to disk):");
        c.check("without the range axiom HermiT finds the variant consistent: the range axiom is the only cause",
                hermitConsistent(variant, out));
    }

    @Override
    void checkFinal(OWLOntology fin, Checks c, PrintStream out) {
        out.println("  expected: consistent=true");
        c.check("HermiT reports the final ontology consistent", hermitConsistent(fin, out));
        Set<String> values = volumes(fin);
        out.println("  volumeGiB of " + CONFIG + " in the final ontology: " + values);
        c.eq(CONFIG + " volumeGiB in the final ontology is the original positive value",
                new TreeSet<>(Set.of("\"4\"^^xsd:positiveInteger")), values);
        boolean bad = false;
        for (OWLDataPropertyAssertionAxiom ax : fin.getAxioms(org.semanticweb.owlapi.model.AxiomType.DATA_PROPERTY_ASSERTION)) {
            if (ax.getProperty().equals(Support.dp("volumeGiB"))
                    && (ax.getObject().getLiteral().startsWith("-")
                            || !ax.getObject().getDatatype().equals(Support.DF.getOWLDatatype(OWL2Datatype.XSD_POSITIVE_INTEGER.getIRI())))) {
                bad = true;
            }
        }
        c.check("no negative or non-positiveInteger volumeGiB literal anywhere in the final ontology", !bad);
    }

    private static Set<String> volumes(OWLOntology ont) {
        Set<String> values = new TreeSet<>();
        for (OWLDataPropertyAssertionAxiom ax : ont.getDataPropertyAssertionAxioms(Support.ind(CONFIG))) {
            if (ax.getProperty().equals(Support.dp("volumeGiB"))) {
                OWLLiteral l = ax.getObject();
                values.add("\"" + l.getLiteral() + "\"^^xsd:" + l.getDatatype().getIRI().getRemainder().or("?"));
            }
        }
        return values;
    }

    @Override
    String summaryText() {
        return "copy inconsistent by range positiveInteger (not functionality), final holds the original positive value";
    }
}
