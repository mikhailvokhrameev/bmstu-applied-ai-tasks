import java.io.*; import java.util.*; import java.util.stream.*;
import org.semanticweb.owlapi.apibinding.OWLManager; import org.semanticweb.owlapi.model.*;
public class ReferenceAudit {
public static void main(String[] args) throws Exception {
OWLOntology o=OWLManager.createOWLOntologyManager().loadOntologyFromOntologyDocument(new File(args[0]));
String ns="https://example.org/ontologies/videocard#";
Set<OWLEntity> es=o.getSignature().stream().filter(e->e.getIRI().toString().startsWith(ns)&&!e.isOWLNamedIndividual()&&!e.isOWLDatatype()&&!e.isOWLAnnotationProperty()).collect(Collectors.toSet());
long h=o.getAxioms(AxiomType.SUBCLASS_OF).stream().filter(a->!a.getSubClass().isAnonymous()&&!a.getSuperClass().isAnonymous()&&es.contains(a.getSubClass())&&es.contains(a.getSuperClass())).count();
Set<OWLClass> eq=new HashSet<>(); for(OWLEquivalentClassesAxiom a:o.getAxioms(AxiomType.EQUIVALENT_CLASSES)) for(OWLClassExpression c:a.getClassExpressions()) if(!c.isAnonymous()&&es.contains(c))eq.add(c.asOWLClass());
System.out.printf("A=%d Al=%d C=%d H=%d Po=%d Pd=%d E=%d Individuals=%d%n",o.getAxiomCount(),o.getLogicalAxiomCount(),es.stream().filter(OWLEntity::isOWLClass).count(),h,o.getObjectPropertiesInSignature().size(),o.getDataPropertiesInSignature().size(),eq.size(),o.getIndividualsInSignature().size());
for(OWLEntity e: new TreeSet<>(es)){
boolean connected=o.getLogicalAxioms().stream().anyMatch(a->a.getSignature().contains(e)&&a.getSignature().stream().filter(es::contains).count()>=2);
if(!connected)System.out.println("P04 "+e.getIRI());
for(String p:List.of("label","comment"))if(o.getAnnotationAssertionAxioms(e.getIRI()).stream().noneMatch(a->a.getProperty().getIRI().toString().equals("http://www.w3.org/2000/01/rdf-schema#"+p)&&a.getValue().asLiteral().isPresent()&&a.getValue().asLiteral().get().hasLang("ru")&&!a.getValue().asLiteral().get().getLiteral().trim().isEmpty()))System.out.println("P08 "+e.getIRI()+" "+p);
if(e.isOWLObjectProperty()) {OWLObjectProperty p=e.asOWLObjectProperty();if(o.getObjectPropertyDomainAxioms(p).isEmpty())System.out.println("P11 "+p+" domain");if(o.getObjectPropertyRangeAxioms(p).isEmpty())System.out.println("P11 "+p+" range");if(o.getInverseObjectPropertyAxioms(p).isEmpty()&&o.getSymmetricObjectPropertyAxioms(p).isEmpty())System.out.println("P13 "+p);}
if(e.isOWLDataProperty()){OWLDataProperty p=e.asOWLDataProperty();if(o.getDataPropertyDomainAxioms(p).isEmpty())System.out.println("P11 "+p+" domain");if(o.getDataPropertyRangeAxioms(p).isEmpty())System.out.println("P11 "+p+" range");}
String name=e.getIRI().getRemainder().or("");if(!name.matches(e.isOWLClass()?"[A-Z][A-Za-z0-9]*":"[a-z][A-Za-z0-9]*"))System.out.println("P22 "+e.getIRI());
}
Set<String> seen=new TreeSet<>();List<OWLSubClassOfAxiom> hs=o.getAxioms(AxiomType.SUBCLASS_OF).stream().filter(a->!a.getSubClass().isAnonymous()&&!a.getSuperClass().isAnonymous()).collect(Collectors.toList());
for(OWLSubClassOfAxiom a:hs)for(OWLSubClassOfAxiom b:hs)if(a.getSuperClass().equals(b.getSuperClass())&&!a.getSubClass().equals(b.getSubClass())){OWLClass x=a.getSubClass().asOWLClass(),y=b.getSubClass().asOWLClass();boolean dis=o.getAxioms(AxiomType.DISJOINT_CLASSES).stream().anyMatch(d->d.getClassExpressions().contains(x)&&d.getClassExpressions().contains(y));if(!dis){List<String> pair=new ArrayList<>(List.of(x.getIRI().toString(),y.getIRI().toString()));Collections.sort(pair);seen.add(pair.toString());}}for(String p:seen)System.out.println("P10 "+p);
}}
