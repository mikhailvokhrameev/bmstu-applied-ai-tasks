import java.io.PrintStream;
import java.util.List;

/** Records and prints individual check outcomes of one test group run. */
final class Checks {
    private final PrintStream out;
    private int total;
    private int failed;

    Checks(PrintStream out) {
        this.out = out;
    }

    boolean check(String description, boolean ok) {
        return check(description, ok, null);
    }

    /** {@code detail} is printed only on failure. */
    boolean check(String description, boolean ok, String detail) {
        total++;
        if (!ok) failed++;
        out.println("  [" + (ok ? "PASS" : "FAIL") + "] " + description
                + (!ok && detail != null ? " -- " + detail : ""));
        return ok;
    }

    boolean eq(String description, Object expected, Object actual) {
        return check(description, expected.equals(actual), "expected " + expected + " but was " + actual);
    }

    /** One line for a batch of {@code totalItems} sub-checks; {@code failures} lists the ones that failed. */
    boolean checkAll(String description, int totalItems, List<String> failures) {
        return check(description + " (" + (totalItems - failures.size()) + "/" + totalItems + ")",
                failures.isEmpty(), String.join("; ", failures));
    }

    int total() {
        return total;
    }

    int failures() {
        return failed;
    }

    boolean ok() {
        return failed == 0;
    }

    /** "N/N checks passed" or "F of N checks failed". */
    String summary() {
        return failed == 0 ? total + "/" + total + " checks passed" : failed + " of " + total + " checks failed";
    }
}
