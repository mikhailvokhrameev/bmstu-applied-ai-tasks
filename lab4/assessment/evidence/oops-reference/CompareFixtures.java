import java.util.*;
import java.util.regex.Pattern;
import org.apache.jena.rdf.model.*;
import org.apache.jena.riot.RDFDataMgr;
import org.apache.jena.vocabulary.RDF;
import com.fasterxml.jackson.databind.ObjectMapper;

/** Report comparison only; does not implement or modify any OOPS pitfall. */
public final class CompareFixtures {
    static final String NS="http://oops.linkeddata.es/def#";
    static final Pattern GENERATED=Pattern.compile("http://oops\\.linkeddata\\.es/data/[0-9a-fA-F-]{36}");
    static final Property CODE=ResourceFactory.createProperty(NS+"hasCode");
    static boolean selected(String code,String family) {
        return code.equals(family)||code.startsWith(family+" ")||code.startsWith(family+"-");
    }
    static List<Resource> roots(Model model,String family) {
        List<Resource> result=new ArrayList<>();
        model.listSubjectsWithProperty(CODE).forEachRemaining(subject->{
            if(selected(subject.getProperty(CODE).getString(),family))result.add(subject);
        });
        return result;
    }
    static Model subset(Model input,String family) {
        Model result=ModelFactory.createDefaultModel();
        ArrayDeque<Resource> queue=new ArrayDeque<>(roots(input,family));
        Set<Resource> visited=new HashSet<>();
        while(!queue.isEmpty()) {
            Resource subject=queue.removeFirst();
            if(!visited.add(subject))continue;
            input.listStatements(subject,null,(RDFNode)null).forEachRemaining(statement->{
                result.add(statement);
                RDFNode object=statement.getObject();
                if(object.isResource()&&(object.isAnon()||GENERATED.matcher(object.asResource().getURI()).matches()))queue.add(object.asResource());
            });
        }
        Model normalized=ModelFactory.createDefaultModel();
        Map<Resource,Resource> mapping=new HashMap<>();
        java.util.function.Function<Resource,Resource> rename=resource->{
            if(resource.isAnon()||(resource.isURIResource()&&GENERATED.matcher(resource.getURI()).matches()))
                return mapping.computeIfAbsent(resource,key->normalized.createResource());
            return resource;
        };
        result.listStatements().forEachRemaining(statement->{
            RDFNode object=statement.getObject();
            if(object.isResource())object=rename.apply(object.asResource());
            normalized.add(rename.apply(statement.getSubject()),statement.getPredicate(),object);
        });
        return normalized;
    }
    public static void main(String[] args)throws Exception {
        Model expected=RDFDataMgr.loadModel(args[0]);
        Model actual=RDFDataMgr.loadModel(args[1]);
        String family=args[2];
        boolean response=actual.contains(null,RDF.type,ResourceFactory.createResource(NS+"response"));
        List<String> unexpected=new ArrayList<>();
        actual.listObjectsOfProperty(CODE).forEachRemaining(node->{if(!selected(node.asLiteral().getString(),family))unexpected.add(node.asLiteral().getString());});
        Model left=subset(expected,family),right=subset(actual,family);
        Map<String,Object> result=new LinkedHashMap<>();
        result.put("family",family);result.put("response_present",response);
        result.put("expected_pitfalls",roots(expected,family).size());
        result.put("actual_pitfalls",roots(actual,family).size());
        result.put("expected_triples",left.size());result.put("actual_triples",right.size());
        result.put("unexpected_codes",unexpected);
        result.put("matches",response&&unexpected.isEmpty()&&left.isIsomorphicWith(right));
        result.put("comparison","Selected pitfall rooted RDF subgraphs; only generated UUID resources become consistently mapped blank nodes; exact literal/predicate/relationship content retained");
        System.out.println(new ObjectMapper().writeValueAsString(result));
    }
}
