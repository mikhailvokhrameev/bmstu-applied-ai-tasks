import java.io.PrintStream;

/** A named group of checks. Register new groups in {@link Main#GROUPS}. */
public interface TestGroup {
    String name();

    /** Runs the checks, printing details to {@code out}; returns true if all passed. */
    boolean run(PrintStream out) throws Exception;
}
