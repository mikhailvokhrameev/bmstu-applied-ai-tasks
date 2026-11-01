import java.util.*;
import org.semanticweb.owlapi.model.*;
import com.fasterxml.jackson.databind.*;
public final class ProposalSyntax {
 public static void main(String[] args) throws Exception {
  ObjectMapper json = new ObjectMapper();
  JsonNode input = json.readTree(System.in);
  int count = 0;
  for (String field : Arrays.asList("add", "remove")) {
   for (JsonNode item : input.get(field)) {
    Set<OWLAxiom> axioms = OntologyEvaluator.parse(Collections.singletonList(item.asText()));
    count += axioms.stream().filter(OWLAxiom::isLogicalAxiom).count();
   }
  }
  System.out.println(count);
 }
}
