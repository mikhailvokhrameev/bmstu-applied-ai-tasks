import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import com.fasterxml.jackson.databind.*;

/** One process, isolated ontology managers and disposed reasoners per request. */
public final class StreamWorker {
    public static void main(String[] args) throws Exception {
        ObjectMapper json = new ObjectMapper();
        BufferedReader input = new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8));
        for (String line; (line = input.readLine()) != null;) {
            Map<String,Object> response = new TreeMap<>();
            try {
                JsonNode envelope = json.readTree(line);
                JsonNode request = envelope.get("payload");
                Object result;
                switch (envelope.get("command").asText()) {
                    case "evaluate":
                        result = OntologyEvaluator.evaluate(request.get("base_path").asText(),
                            OntologyEvaluator.readList(request.get("add")),
                            OntologyEvaluator.readList(request.get("remove")));
                        break;
                    case "inspect": result = CandidateValidator.inspect(request); break;
                    case "syntax": result = ProposalSyntax.inspect(request); break;
                    default: throw new IllegalArgumentException("Unknown worker command");
                }
                response.put("ok", true);
                response.put("result", result);
            } catch (Exception error) {
                response.put("ok", false);
                response.put("error", error.getClass().getSimpleName() + ": " + error.getMessage());
            }
            System.out.println(json.writeValueAsString(response));
            System.out.flush();
        }
    }
}
