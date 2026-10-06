import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.security.MessageDigest;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.semanticweb.HermiT.ReasonerFactory;
import org.semanticweb.owlapi.apibinding.OWLManager;
import org.semanticweb.owlapi.model.OWLOntology;
import org.semanticweb.owlapi.reasoner.OWLReasoner;
import org.semanticweb.owlapi.util.VersionInfo;

/**
 * Test runner entry point. Prints an environment header, then runs every registered {@link TestGroup},
 * writing tests/results/&lt;id&gt;.log per group and tests/results/summary.json; exits non-zero if any group fails.
 * Usage: java Main [project-root]
 */
public class Main {
    /** Add new test groups here. */
    static final List<TestGroup> GROUPS = List.of(
            new T01RequiredEntities(),
            new T02OntologyStructure(),
            new T03CompletenessCard(),
            new T04Reasoning(),
            new T05DlQueries());

    public static void main(String[] args) throws Exception {
        Path root = Paths.get(args.length > 0 ? args[0] : ".").toAbsolutePath().normalize();
        Support.setRoot(root);
        PrintStream out = System.out;

        printHeader(out, root);

        int failed = 0;
        Map<String, Map<String, String>> summary = new LinkedHashMap<>();
        for (TestGroup group : GROUPS) {
            out.println();
            boolean ok;
            // Per-group log: relative paths and no timestamps, so reruns diff cleanly.
            try (PrintStream log = Support.tee(out, Support.resultsDir().resolve(group.id() + ".log"))) {
                log.println("== " + group.name() + " ==");
                try {
                    ok = group.run(log);
                } catch (Throwable t) {
                    t.printStackTrace(log);
                    ok = false;
                }
                log.println(group.id() + ": " + (ok ? "PASS" : "FAIL"));
            }
            Map<String, String> entry = new LinkedHashMap<>();
            entry.put("status", ok ? "PASS" : "FAIL");
            entry.put("note", group.note());
            summary.put(group.id(), entry);
            if (!ok) failed++;
        }
        writeSummary(Support.resultsDir().resolve("summary.json"), summary);

        out.println();
        out.println("SUMMARY: " + (GROUPS.size() - failed) + "/" + GROUPS.size() + " groups passed");
        System.exit(failed == 0 ? 0 : 1);
    }

    private static void writeSummary(Path file, Map<String, Map<String, String>> summary) throws IOException {
        String json = new ObjectMapper().writerWithDefaultPrettyPrinter().writeValueAsString(summary);
        Files.writeString(file, json + "\n", StandardCharsets.UTF_8);
    }

    private static void printHeader(PrintStream out, Path root) throws Exception {
        out.println("VideoCardOntology v1.0.0 test run");
        out.println("OWL API:  " + VersionInfo.getVersionInfo().getVersion());
        out.println("HermiT:   " + Support.hermitJarVersion() + " (Reasoner.getReasonerVersion() self-reports "
                + hermitSelfReportedVersion() + ")");
        out.println("Java:     " + System.getProperty("java.version") + " (" + System.getProperty("java.vendor") + ")");
        out.println("OS:       " + System.getProperty("os.name") + " " + System.getProperty("os.version")
                + " " + System.getProperty("os.arch"));
        Path owl = root.resolve("ontology").resolve("videocard.owl");
        out.println("videocard.owl SHA-256: " + (Files.isRegularFile(owl) ? sha256(owl) : "(file not present)"));
    }

    private static String hermitSelfReportedVersion() throws Exception {
        OWLOntology empty = OWLManager.createOWLOntologyManager().createOntology();
        OWLReasoner r = new ReasonerFactory().createReasoner(empty);
        try {
            return r.getReasonerVersion().toString();
        } finally {
            r.dispose();
        }
    }

    private static String sha256(Path file) throws IOException, java.security.NoSuchAlgorithmException {
        byte[] digest = MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(file));
        StringBuilder sb = new StringBuilder();
        for (byte b : digest) sb.append(String.format("%02x", b));
        return sb.toString();
    }
}
