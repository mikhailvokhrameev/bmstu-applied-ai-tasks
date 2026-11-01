import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.stream.*;
import org.semanticweb.owlapi.apibinding.OWLManager;
import org.semanticweb.owlapi.io.StringDocumentSource;
import org.semanticweb.owlapi.model.*;
import org.semanticweb.owlapi.profiles.OWL2DLProfile;
import org.semanticweb.owlapi.reasoner.OWLReasoner;
import org.semanticweb.HermiT.ReasonerFactory;
import com.fasterxml.jackson.databind.*;

/** OWL API / HermiT checks; exceptions propagate to the process boundary. */
public class CandidateValidator {
 static final String NS=Support.NS;
 static final PrintStream QUIET=new PrintStream(OutputStream.nullOutputStream());
 static final ObjectMapper JSON=new ObjectMapper();
 static Map<String,Object> fail(String code) { return new TreeMap<>(Map.of("code",code)); }
 static boolean consistent(OWLOntology o) { OWLReasoner r=new ReasonerFactory().createReasoner(o); try{return r.isConsistent();}finally{r.dispose();} }
 static OWLOntology copy(OWLOntology o) throws Exception {return OWLManager.createOWLOntologyManager().createOntology(o.getAxioms());}
 static Set<OWLAxiom> parse(JsonNode list) throws Exception {
  Set<OWLAxiom> out=new HashSet<>(); if(list==null)return out;
  for(JsonNode item:list){
   OWLOntology o=OWLManager.createOWLOntologyManager().loadOntologyFromOntologyDocument(new StringDocumentSource("Prefix(:=<"+NS+">) Prefix(rdfs:=<http://www.w3.org/2000/01/rdf-schema#>) Prefix(xsd:=<http://www.w3.org/2001/XMLSchema#>) Ontology("+item.asText()+")"));
   if(o.getAxiomCount()!=1)throw new IllegalArgumentException("one axiom required");out.addAll(o.getAxioms());
  }return out;
 }
 static String text(OWLOntology o, OWLEntity e,String kind){return o.getAnnotationAssertionAxioms(e.getIRI()).stream().filter(a->a.getProperty().getIRI().toString().equals("http://www.w3.org/2000/01/rdf-schema#"+kind)&&a.getValue().asLiteral().isPresent()&&a.getValue().asLiteral().get().hasLang("ru")).map(a->a.getValue().asLiteral().get().getLiteral()).filter(s->!s.trim().isEmpty()).sorted().collect(Collectors.joining(" "));}
 static OWLOntology loadCandidate(String path)throws Exception{
  OWLOntologyManager m=OWLManager.createOWLOntologyManager();
  m.setOntologyLoaderConfiguration(new OWLOntologyLoaderConfiguration().setMissingImportHandlingStrategy(MissingImportHandlingStrategy.SILENT));
  m.getIRIMappers().add(iri->IRI.create("file:/private/tmp/videocard-external-imports-disabled.owl"));
  return m.loadOntologyFromOntologyDocument(new File(path));
 }
 static Map<String,Object> inspect(JsonNode q) throws Exception {
  OWLOntology base=Support.load(new File(q.get("baseline").asText()));
  OWLOntology o;
  if(q.has("path"))o=loadCandidate(q.get("path").asText());else {o=copy(base);o.getOWLOntologyManager().addAxioms(o,parse(q.get("add")));o.getOWLOntologyManager().removeAxioms(o,parse(q.get("remove")));}
  if(!new OWL2DLProfile().checkOntology(o).isInProfile())return fail("OWL2_DL");
  OWLReasoner r=new ReasonerFactory().createReasoner(o);
  try{
   if(!r.isConsistent())return fail("CONSISTENCY");
   for(OWLClass c:o.getClassesInSignature())if(!c.isBuiltIn()&&!r.isSatisfiable(c))return fail("CONSISTENCY");
  }finally{r.dispose();}
  Checks queries=new Checks(QUIET); CandidateQueries.verify(o,new ReasonerFactory(),Path.of(q.get("expected").asText()),queries,QUIET);
  if(!queries.ok())return fail("QUERIES");
  for(NegativeCopyTest test:List.of(new T06ActiveAndPassive(),new T07TwoGpus(),new T08NegativeVolume(),new T09MissingHasMemory())){
   OWLOntology n=copy(o);n.getOWLOntologyManager().removeAxioms(n,test.removedByMutation());n.getOWLOntologyManager().addAxioms(n,test.addedByMutation());
   if(test instanceof T09MissingHasMemory){
    if(!consistent(n)||!T03CompletenessCard.build(n).problems.equals(List.of(new T03CompletenessCard.Problem("U05","hasMemory",0,"1"))))return fail("NEGATIVE_TESTS");
   } else if(consistent(n))return fail("NEGATIVE_TESTS");
  }
  if(!o.getAxioms().containsAll(base.getAxioms()))return fail("CORE");
  Set<OWLClass> defined=new HashSet<>();for(OWLEquivalentClassesAxiom a:o.getAxioms(AxiomType.EQUIVALENT_CLASSES))for(OWLClassExpression c:a.getClassExpressions())if(!c.isAnonymous())defined.add(c.asOWLClass());
  if(!o.getImportsDeclarations().isEmpty()||!o.getAxioms(AxiomType.SWRL_RULE).isEmpty()||o.getAxioms(AxiomType.CLASS_ASSERTION).stream().anyMatch(a->defined.contains(a.getClassExpression())))return fail("FORBIDDEN");
  Set<OWLEntity> fresh=new HashSet<>(o.getSignature());fresh.removeAll(base.getSignature());fresh.removeIf(OWLEntity::isBuiltIn);
  List<Map<String,String>> entities=new ArrayList<>();
  for(OWLEntity e:fresh){
   if(!e.getIRI().toString().startsWith(NS)||text(o,e,"label").isEmpty()||text(o,e,"comment").isEmpty())return fail("ANNOTATIONS");
   entities.add(Map.of("iri",e.getIRI().toString(),"category",e.getEntityType().toString(),"label",text(o,e,"label"),"comment",text(o,e,"comment")));
  }
  String change=changes(o,base,fresh);
  Map<String,Object> out=new TreeMap<>();out.put("counts",OntologyEvaluator.audit(o).counts);out.put("baseline_counts",OntologyEvaluator.audit(base).counts);out.put("new_entities",entities);out.put("change_violation",change);return out;
 }
 static String changes(OWLOntology o,OWLOntology b,Set<OWLEntity> fresh){
  OWLReasoner r=new ReasonerFactory().createReasoner(o);
  try{
   for(OWLEntity e:fresh){
    if(e.isOWLClass()){
     OWLClass c=e.asOWLClass();
     if(!o.getEquivalentClassesAxioms(c).isEmpty()){
      if(r.getInstances(c,false).getFlattened().stream().noneMatch(b.getIndividualsInSignature()::contains))return "defined class lacks teaching instance";
     }else if(o.getSubClassAxiomsForSubClass(c).stream().noneMatch(a->!a.getSuperClass().isAnonymous()&&b.containsClassInSignature(a.getSuperClass().asOWLClass().getIRI())))return "new class needs existing named superclass";
    }else if(e.isOWLDataProperty()){
     OWLDataProperty p=e.asOWLDataProperty();
     if(o.getDataPropertyDomainAxioms(p).isEmpty()||o.getDataPropertyRangeAxioms(p).isEmpty()||!e.getIRI().getRemainder().or("").matches(".*(?:GiB|MiB|MHz|GHz|Hz|Bit|Byte|MM|Cm|W|V|A|Percent|Count)$"))return "data property requires domain, range and unit suffix";
    }else if(e.isOWLObjectProperty()){
     if(o.getInverseObjectPropertyAxioms(e.asOWLObjectProperty()).isEmpty())return "new object property must be inverse";
    }else return "new individual or entity kind is not allowed";
   }
   for(OWLAxiom a:o.getAxioms())if(!b.containsAxiom(a)){
    if(a instanceof OWLDeclarationAxiom || a instanceof OWLAnnotationAssertionAxiom)continue;
    if(a instanceof OWLSubClassOfAxiom){OWLSubClassOfAxiom x=(OWLSubClassOfAxiom)a;if(x.getSubClass().isAnonymous()||!fresh.contains(x.getSubClass())||x.getSuperClass().isAnonymous()||!b.containsClassInSignature(x.getSuperClass().asOWLClass().getIRI()))return "subclass outside allowed template";}
    else if(a instanceof OWLEquivalentClassesAxiom){if(a.getClassesInSignature().stream().noneMatch(fresh::contains))return "definition must concern new class";}
    else if(a instanceof OWLInverseObjectPropertiesAxiom){
     OWLInverseObjectPropertiesAxiom x=(OWLInverseObjectPropertiesAxiom)a;OWLObjectProperty p=x.getFirstProperty().getNamedProperty(),s=x.getSecondProperty().getNamedProperty();
     Set<OWLClassExpression> pd=o.getObjectPropertyDomainAxioms(p).stream().map(OWLObjectPropertyDomainAxiom::getDomain).collect(Collectors.toSet()),pr=o.getObjectPropertyRangeAxioms(p).stream().map(OWLObjectPropertyRangeAxiom::getRange).collect(Collectors.toSet()),sd=o.getObjectPropertyDomainAxioms(s).stream().map(OWLObjectPropertyDomainAxiom::getDomain).collect(Collectors.toSet()),sr=o.getObjectPropertyRangeAxioms(s).stream().map(OWLObjectPropertyRangeAxiom::getRange).collect(Collectors.toSet());
     if(pd.isEmpty()||pr.isEmpty()||!pd.equals(sr)||!pr.equals(sd))return "inverse domain/range must mirror direct property";
    }else if(a instanceof OWLDataPropertyAssertionAxiom){OWLDataPropertyAssertionAxiom x=(OWLDataPropertyAssertionAxiom)a;if(!fresh.contains(x.getProperty())||!b.getIndividualsInSignature().contains(x.getSubject())||!text(o,x.getSubject().asOWLNamedIndividual(),"comment").toLowerCase(Locale.ROOT).contains("условн"))return "new teaching values need conditional-data comment";}
    else if(a instanceof OWLDisjointClassesAxiom){if(((OWLDisjointClassesAxiom)a).getClassExpressions().stream().anyMatch(c->!fresh.contains(c)))return "disjointness only for new classes";}
    else if(a instanceof OWLObjectPropertyDomainAxiom){if(!fresh.contains(((OWLObjectPropertyDomainAxiom)a).getProperty().getNamedProperty()))return "domain/range only for new properties";}
    else if(a instanceof OWLObjectPropertyRangeAxiom){if(!fresh.contains(((OWLObjectPropertyRangeAxiom)a).getProperty().getNamedProperty()))return "domain/range only for new properties";}
    else if(a instanceof OWLDataPropertyDomainAxiom){if(!fresh.contains(((OWLDataPropertyDomainAxiom)a).getProperty().asOWLDataProperty()))return "domain/range only for new properties";}
    else if(a instanceof OWLDataPropertyRangeAxiom){if(!fresh.contains(((OWLDataPropertyRangeAxiom)a).getProperty().asOWLDataProperty()))return "domain/range only for new properties";}
    else if(!(a instanceof OWLFunctionalObjectPropertyAxiom||a instanceof OWLInverseFunctionalObjectPropertyAxiom||a instanceof OWLAsymmetricObjectPropertyAxiom||a instanceof OWLIrreflexiveObjectPropertyAxiom||a instanceof OWLSubObjectPropertyOfAxiom||a instanceof OWLSubDataPropertyOfAxiom))return "axiom kind is not allowed: "+a.getAxiomType();
   }
  }finally{r.dispose();}return "";
 }
 public static void main(String[] args)throws Exception{try{System.out.println(JSON.writeValueAsString(inspect(JSON.readTree(System.in))));}catch(Exception e){System.err.println("VALIDATION_ERROR: "+e);System.exit(2);}}
}
