import java.util.*;
import org.semanticweb.owlapi.model.*;
import com.fasterxml.jackson.databind.*;
public final class ProposalSyntax {
 public static Map<String,Object> inspect(JsonNode input) throws Exception {
  Set<OWLAxiom> add = new HashSet<>(), remove = new HashSet<>();
  String fieldName = null, axiomText = null;
  int index = -1;
  try {
   for (String field : Arrays.asList("add", "remove")) {
    Set<OWLAxiom> target = field.equals("add") ? add : remove;
    fieldName = field;
    index = -1;
    for (JsonNode item : input.get(field)) {
     index++;
     axiomText = item.asText();
     Set<OWLAxiom> parsed = OntologyEvaluator.parse(Collections.singletonList(axiomText));
     if (parsed.size() != 1) throw new IllegalArgumentException("Exactly one axiom per array element required");
     for (OWLAxiom axiom : parsed) {
      if (!target.add(axiom)) throw new IllegalArgumentException("Repeated axiom");
     }
    }
   }
   fieldName = null;
   if (!Collections.disjoint(add, remove)) throw new IllegalArgumentException("Conflicting add/remove");
  } catch (OWLOntologyCreationException | IllegalArgumentException error) {
   Map<String,Object> failure = new TreeMap<>();
   failure.put("status", "invalid");
   failure.put("detail", String.valueOf(error.getMessage()));
   if (fieldName != null) {
    failure.put("field", fieldName);
    failure.put("index", index);
    failure.put("axiom", axiomText);
   }
   return failure;
  }
  Set<OWLAxiom> unique = new HashSet<>(add);
  unique.addAll(remove);
  long count = unique.stream().filter(OWLAxiom::isLogicalAxiom).count();
  return new TreeMap<>(Map.of("status", "ok", "logical_count", count));
 }
 public static void main(String[] args) throws Exception {
  ObjectMapper json = new ObjectMapper();
  System.out.println(json.writeValueAsString(inspect(json.readTree(System.in))));
 }
}
