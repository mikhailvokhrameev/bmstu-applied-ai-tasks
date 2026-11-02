import java.util.*;
import org.apache.jena.rdf.model.*;
import org.apache.jena.riot.RDFDataMgr;
import org.apache.jena.vocabulary.RDF;
import com.fasterxml.jackson.databind.ObjectMapper;

/** Read the official response as RDF, retaining affected counts and records. */
public final class SummarizeReport {
    static final String NS="http://oops.linkeddata.es/def#";
    public static void main(String[] args)throws Exception {
        Model model=RDFDataMgr.loadModel(args[0]);
        Property code=model.createProperty(NS+"hasCode");
        List<Map<String,Object>> findings=new ArrayList<>();
        Map<String,Integer> records=new TreeMap<>(),affectedCounts=new TreeMap<>();
        model.listSubjectsWithProperty(code).forEachRemaining(subject->{
            Map<String,Object> row=new LinkedHashMap<>();
            String codeText=subject.getProperty(code).getString();
            String family=codeText.substring(0,3);
            row.put("code",codeText);row.put("family",family);
            for(String name:List.of("hasName","hasDescription","hasImportanceLevel")) {
                Statement statement=subject.getProperty(model.createProperty(NS+name));
                if(statement!=null)row.put(name,statement.getString());
            }
            Statement number=subject.getProperty(model.createProperty(NS+"hasNumberAffectedElements"));
            int count=number==null?0:number.getInt();
            row.put("number_affected",count);
            List<String> affected=new ArrayList<>();
            subject.listProperties(model.createProperty(NS+"hasAffectedElement")).forEachRemaining(statement->{
                RDFNode value=statement.getObject();affected.add(value.isLiteral()?value.asLiteral().getLexicalForm():value.toString());
            });
            Collections.sort(affected);row.put("affected_elements",affected);
            records.merge(family,1,Integer::sum);affectedCounts.merge(family,count,Integer::sum);findings.add(row);
        });
        findings.sort(Comparator.comparing(row->row.get("code").toString()));
        Map<String,Object> result=new LinkedHashMap<>();
        result.put("response_present",model.contains(null,RDF.type,model.createResource(NS+"response")));
        result.put("rdf_triples",model.size());result.put("pitfall_records",findings.size());
        result.put("sum_number_affected",findings.stream().mapToInt(row->(Integer)row.get("number_affected")).sum());
        result.put("records_by_family",records);result.put("affected_counts_by_family",affectedCounts);
        result.put("findings",findings);
        System.out.println(new ObjectMapper().writeValueAsString(result));
    }
}
