import java.io.PrintStream;

/** A named group of checks. Register new groups in {@link Main#GROUPS}. */
public interface TestGroup {
    /** Short id such as "T01"; names the log file tests/results/&lt;id&gt;.log and the key in summary.json. */
    String id();

    String name();

    /** Runs the checks, printing details to {@code out}; returns true if all passed. */
    boolean run(PrintStream out) throws Exception;

    /** One-line, deterministic result note for summary.json; called after {@link #run}. */
    String note();
}
