import java.util.*;
import org.semanticweb.owlapi.model.*;
import com.fasterxml.jackson.databind.*;
public final class ProposalSyntax {
 public static void main(String[] args) throws Exception {
  ObjectMapper json = new ObjectMapper();
  JsonNode input = json.readTree(System.in);
  Set<OWLAxiom> add = new HashSet<>(), remove = new HashSet<>();
  try {
   for (String field : Arrays.asList("add", "remove")) {
    Set<OWLAxiom> target = field.equals("add") ? add : remove;
    for (JsonNode item : input.get(field)) {
     for (OWLAxiom axiom : OntologyEvaluator.parse(Collections.singletonList(item.asText()))) {
      if (!target.add(axiom)) throw new IllegalArgumentException("Repeated axiom");
     }
    }
   }
   if (!Collections.disjoint(add, remove)) throw new IllegalArgumentException("Conflicting add/remove");
  } catch (OWLOntologyCreationException | IllegalArgumentException error) {
   System.out.println(json.writeValueAsString(Map.of("status", "invalid", "detail", String.valueOf(error.getMessage()))));
   return;
  }
  Set<OWLAxiom> unique = new HashSet<>(add);
  unique.addAll(remove);
  long count = unique.stream().filter(OWLAxiom::isLogicalAxiom).count();
  System.out.println(json.writeValueAsString(Map.of("status", "ok", "logical_count", count)));
 }
}
