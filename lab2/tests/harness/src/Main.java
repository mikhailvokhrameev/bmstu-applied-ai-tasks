import java.io.IOException;
import java.io.InputStream;
import java.io.PrintStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.security.MessageDigest;
import java.util.List;
import java.util.Properties;
import org.semanticweb.HermiT.ReasonerFactory;
import org.semanticweb.owlapi.apibinding.OWLManager;
import org.semanticweb.owlapi.model.OWLOntology;
import org.semanticweb.owlapi.reasoner.OWLReasoner;
import org.semanticweb.owlapi.util.VersionInfo;

/**
 * Test runner entry point. Prints an environment header, then runs every
 * registered {@link TestGroup} and exits non-zero if any group fails.
 * Usage: java Main [project-root]
 */
public class Main {
    /** Add new test groups here. */
    static final List<TestGroup> GROUPS = List.of(new Smoke());

    public static void main(String[] args) throws Exception {
        Path root = Paths.get(args.length > 0 ? args[0] : ".").toAbsolutePath().normalize();
        PrintStream out = System.out;

        printHeader(out, root);

        int failed = 0;
        for (TestGroup group : GROUPS) {
            out.println();
            out.println("== " + group.name() + " ==");
            boolean ok;
            try {
                ok = group.run(out);
            } catch (Throwable t) {
                t.printStackTrace(out);
                ok = false;
            }
            out.println(group.name() + ": " + (ok ? "PASS" : "FAIL"));
            if (!ok) failed++;
        }

        out.println();
        out.println("SUMMARY: " + (GROUPS.size() - failed) + "/" + GROUPS.size() + " groups passed");
        System.exit(failed == 0 ? 0 : 1);
    }

    private static void printHeader(PrintStream out, Path root) throws Exception {
        out.println("VideoCardOntology v1.0.0 test run");
        out.println("OWL API:  " + VersionInfo.getVersionInfo().getVersion());
        out.println("HermiT:   " + hermitJarVersion() + " (Reasoner.getReasonerVersion() self-reports "
                + hermitSelfReportedVersion() + ")");
        out.println("Java:     " + System.getProperty("java.version") + " (" + System.getProperty("java.vendor") + ")");
        out.println("OS:       " + System.getProperty("os.name") + " " + System.getProperty("os.version")
                + " " + System.getProperty("os.arch"));
        Path owl = root.resolve("ontology").resolve("videocard.owl");
        out.println("videocard.owl SHA-256: " + (Files.isRegularFile(owl) ? sha256(owl) : "(file not present)"));
    }

    /** The 1.4.3.456 jar still self-reports an older version, so read the real one from its Maven metadata. */
    private static String hermitJarVersion() throws IOException {
        String res = "/META-INF/maven/net.sourceforge.owlapi/org.semanticweb.hermit/pom.properties";
        try (InputStream in = ReasonerFactory.class.getResourceAsStream(res)) {
            if (in == null) return "unknown";
            Properties p = new Properties();
            p.load(in);
            return p.getProperty("version", "unknown");
        }
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
