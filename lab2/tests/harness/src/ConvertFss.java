import java.io.File;
import java.io.FileOutputStream;
import java.io.OutputStream;
import org.semanticweb.owlapi.apibinding.OWLManager;
import org.semanticweb.owlapi.formats.RDFXMLDocumentFormat;
import org.semanticweb.owlapi.formats.PrefixDocumentFormat;
import org.semanticweb.owlapi.model.OWLDocumentFormat;
import org.semanticweb.owlapi.model.OWLOntology;
import org.semanticweb.owlapi.model.OWLOntologyManager;
import org.semanticweb.owlapi.profiles.OWL2DLProfile;
import org.semanticweb.owlapi.profiles.OWLProfileReport;

/**
 * Converts an OWL 2 Functional Syntax file to RDF/XML (UTF-8), preserving the
 * ontology IRI, version IRI and prefixes. Fails (exit 1) if the ontology has
 * imports or is not OWL 2 DL.
 * Usage: java ConvertFss input.fss output.owl
 */
public class ConvertFss {
    public static void main(String[] args) throws Exception {
        if (args.length != 2) {
            System.err.println("usage: ConvertFss input.fss output.owl");
            System.exit(2);
        }
        OWLOntologyManager m = OWLManager.createOWLOntologyManager();
        OWLOntology o = m.loadOntologyFromOntologyDocument(new File(args[0]));

        if (!o.getImportsDeclarations().isEmpty()) {
            System.err.println("ERROR: ontology has imports: " + o.getImportsDeclarations());
            System.exit(1);
        }
        OWLProfileReport report = new OWL2DLProfile().checkOntology(o);
        if (!report.isInProfile()) {
            System.err.println("ERROR: not OWL 2 DL: " + report);
            System.exit(1);
        }

        OWLDocumentFormat src = m.getOntologyFormat(o);
        RDFXMLDocumentFormat out = new RDFXMLDocumentFormat();
        if (src instanceof PrefixDocumentFormat) {
            out.copyPrefixesFrom((PrefixDocumentFormat) src);
        }
        try (OutputStream os = new FileOutputStream(args[1])) {
            m.saveOntology(o, out, os);
        }
        System.out.println("ConvertFss: " + o.getOntologyID() + " -> " + args[1]
                + " (" + o.getAxiomCount() + " axioms, OWL 2 DL, no imports)");
    }
}
