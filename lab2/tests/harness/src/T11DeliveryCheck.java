import java.io.IOException;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Stream;
import org.semanticweb.owlapi.util.VersionInfo;

/**
 * T11 (spec Table 6, 4.6.3): checks the delivered folder as a whole. Every item is its own named check so that a
 * failing run lists exactly what is missing. Must be registered LAST in {@link Main#GROUPS}: it reads the logs that
 * T01-T10 wrote earlier in the same invocation. Needs the documentation (README, docs/) to pass.
 */
public class T11DeliveryCheck implements TestGroup {
    /** Pinned tool versions (global constraints); the runtime must match, and fetch_libs.sh must state them. */
    private static final String OWLAPI_VERSION = "4.5.29";
    private static final String HERMIT_VERSION = "1.4.3.456";

    private static final String[] REQUIRED_PATHS = {
        "ontology/videocard.owl",
        "ontology/src/build_ontology.py",
        "ontology/src/ontology_data.py",
        "ontology/src/build.sh",
        "docs/ontology_description.md",
        "docs/test_protocol.md",
        "README.md",
        "tests/run_tests.sh",
        "tests/expected.json",
        "tests/harness/fetch_libs.sh",
        "tests/harness/src",
        "tests/negative/T06_active_and_passive.owl",
        "tests/negative/T07_two_gpus.owl",
        "tests/negative/T08_negative_volume.owl",
        "tests/negative/T09_missing_hasMemory.owl",
        "tests/results",
    };
    private static final String[] NEGATIVES = {
        "T06_active_and_passive.owl", "T07_two_gpus.owl", "T08_negative_volume.owl", "T09_missing_hasMemory.owl"
    };
    private static final Pattern HEX64 = Pattern.compile("\\b[0-9a-fA-F]{64}\\b");

    private String note = "";

    @Override
    public String id() {
        return "T11";
    }

    @Override
    public String name() {
        return "T11 delivered folder structure and consistency";
    }

    @Override
    public String note() {
        return note;
    }

    @Override
    public boolean run(PrintStream out) throws Exception {
        Path root = Support.root();
        Checks c = new Checks(out);

        for (String p : REQUIRED_PATHS) {
            c.check("path exists: " + p, Files.exists(root.resolve(p)));
        }
        c.check("tests/harness/src contains Java sources", countFiles(root.resolve("tests/harness/src"), ".java") > 0);

        for (int i = 1; i <= 10; i++) {
            String id = String.format("T%02d", i);
            c.check("results log " + id + ".log ends with '" + id + ": PASS'",
                    lastNonEmptyLine(Support.resultsDir().resolve(id + ".log")).equals(id + ": PASS"),
                    "last line was '" + lastNonEmptyLine(Support.resultsDir().resolve(id + ".log")) + "'");
        }

        checkOwlFiles(root, c);
        checkReadme(root, c);
        checkToolVersions(root, c, out);
        checkDocs(root, c);

        note = c.summary();
        return c.ok();
    }

    // ---- b: where .owl files live --------------------------------------------------------------------

    private static void checkOwlFiles(Path root, Checks c) throws Exception {
        Path ontology = root.resolve("ontology/videocard.owl");
        Path negDir = root.resolve("tests/negative");
        Path resaved = root.resolve("tests/results").resolve(T10RoundTrip.RESAVED_NAME);
        List<String> stray = new ArrayList<>();
        try (Stream<Path> walk = Files.walk(root)) {
            walk.filter(Files::isRegularFile).filter(p -> p.getFileName().toString().endsWith(".owl"))
                    .filter(p -> !isExcluded(root.relativize(p)))
                    .filter(p -> !p.equals(ontology) && !p.equals(resaved) && !p.getParent().equals(negDir))
                    .forEach(p -> stray.add(root.relativize(p).toString()));
        }
        c.check("no .owl files besides videocard.owl, tests/negative/*.owl and the T10 re-saved copy",
                stray.isEmpty(), "stray: " + stray);

        if (!Files.isRegularFile(ontology)) {
            c.check("negative copies differ from videocard.owl", false, "videocard.owl missing");
            return;
        }
        String finalHash = sha256(ontology);
        List<String> same = new ArrayList<>();
        for (String n : NEGATIVES) {
            Path f = negDir.resolve(n);
            if (!Files.isRegularFile(f) || sha256(f).equals(finalHash)) same.add(n);
        }
        c.checkAll("each negative copy exists and differs from videocard.owl (SHA-256)", NEGATIVES.length, same);
    }

    /** Dependency/build/VCS directories that are not part of the delivery. */
    private static boolean isExcluded(Path rel) {
        String s = rel.toString().replace('\\', '/');
        return s.startsWith(".git/") || s.startsWith(".superpowers/") || s.startsWith("tests/harness/lib/")
                || s.startsWith("tests/harness/out/");
    }

    // ---- c: README -----------------------------------------------------------------------------------

    private static void checkReadme(Path root, Checks c) throws Exception {
        Path readmeFile = root.resolve("README.md");
        String readme = readText(readmeFile);
        c.check("README.md contains version string 1.0.0", readme.contains("1.0.0"));
        c.check("README.md mentions run_tests.sh", readme.contains("run_tests.sh"));

        // A 64-hex digest within 200 characters after an occurrence of "SHA-256".
        List<String> digests = new ArrayList<>();
        Matcher m = Pattern.compile("SHA-256").matcher(readme);
        while (m.find()) {
            Matcher h = HEX64.matcher(readme.substring(m.end(), Math.min(readme.length(), m.end() + 200)));
            if (h.find()) digests.add(h.group().toLowerCase());
        }
        c.check("README.md contains 'SHA-256' followed by a 64-hex digest", !digests.isEmpty());
        Path ontology = root.resolve("ontology/videocard.owl");
        String actual = Files.isRegularFile(ontology) ? sha256(ontology) : "(videocard.owl missing)";
        c.check("README.md SHA-256 equals the actual SHA-256 of ontology/videocard.owl", digests.contains(actual),
                "README digests " + digests + ", actual " + actual);
    }

    // ---- d: pinned tool versions ---------------------------------------------------------------------

    private static void checkToolVersions(Path root, Checks c, PrintStream out) throws Exception {
        // getVersion() is "4.5.29.<build timestamp>": keep the major.minor.patch part.
        String owlApi = VersionInfo.getVersionInfo().getVersion().replaceFirst("^(\\d+\\.\\d+\\.\\d+).*$", "$1");
        String hermit = Support.hermitJarVersion();
        out.println("runtime: OWL API " + owlApi + ", HermiT jar " + hermit + ", Java " + System.getProperty("java.version"));
        c.check("runtime OWL API is the pinned " + OWLAPI_VERSION, OWLAPI_VERSION.equals(owlApi), "was " + owlApi);
        c.check("runtime HermiT jar is the pinned " + HERMIT_VERSION, HERMIT_VERSION.equals(hermit), "was " + hermit);
        c.check("Java version is available (" + System.getProperty("java.version") + ")",
                !System.getProperty("java.version", "").isEmpty());

        String t04 = readText(Support.resultsDir().resolve("T04.log"));
        c.check("T04.log records the HermiT jar version " + hermit, t04.contains("jar version " + hermit));

        // The header of fetch_libs.sh is its first comment block.
        StringBuilder header = new StringBuilder();
        for (String line : readText(root.resolve("tests/harness/fetch_libs.sh")).split("\n")) {
            if (!line.startsWith("#")) break;
            header.append(line).append('\n');
        }
        String h = header.toString().replaceAll("\\s*\n#\\s*", " ");
        c.check("fetch_libs.sh header pins OWL API " + owlApi, h.contains("OWL API " + owlApi));
        c.check("fetch_libs.sh header pins HermiT " + hermit, h.contains("HermiT " + hermit));
    }

    // ---- e: documentation ----------------------------------------------------------------------------

    private static void checkDocs(Path root, Checks c) throws Exception {
        String protocol = readText(root.resolve("docs/test_protocol.md"));
        for (int i = 1; i <= 11; i++) {
            String id = String.format("T%02d", i);
            c.check("docs/test_protocol.md mentions " + id, protocol.contains(id));
        }
        c.check("docs/test_protocol.md records the tool versions (OWL API " + OWLAPI_VERSION + ", HermiT "
                + HERMIT_VERSION + ", Java)",
                protocol.contains(OWLAPI_VERSION) && protocol.contains(HERMIT_VERSION) && protocol.contains("Java"));
        c.check("docs/ontology_description.md is non-empty", !readText(root.resolve("docs/ontology_description.md")).isBlank());
    }

    // ---- helpers -------------------------------------------------------------------------------------

    /** File content, or "" if the file does not exist (the missing file is reported by its own check). */
    private static String readText(Path file) throws IOException {
        return Files.isRegularFile(file) ? Files.readString(file, StandardCharsets.UTF_8) : "";
    }

    private static String lastNonEmptyLine(Path file) throws IOException {
        String last = "";
        for (String line : readText(file).split("\n")) {
            if (!line.isBlank()) last = line.strip();
        }
        return last;
    }

    private static long countFiles(Path dir, String suffix) throws IOException {
        if (!Files.isDirectory(dir)) return 0;
        try (Stream<Path> s = Files.list(dir)) {
            return s.filter(p -> p.getFileName().toString().endsWith(suffix)).count();
        }
    }

    private static String sha256(Path file) throws Exception {
        byte[] digest = MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(file));
        StringBuilder sb = new StringBuilder();
        for (byte b : digest) sb.append(String.format("%02x", b));
        return sb.toString();
    }
}
