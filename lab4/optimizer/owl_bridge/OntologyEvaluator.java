import java.io.*;
import java.util.*;
import java.util.stream.Collectors;
import org.semanticweb.owlapi.apibinding.OWLManager;
import org.semanticweb.owlapi.io.StringDocumentSource;
import org.semanticweb.owlapi.model.*;
import org.semanticweb.owlapi.formats.ManchesterSyntaxDocumentFormat;
import java.nio.charset.StandardCharsets;
import java.util.regex.Pattern;
import org.semanticweb.owlapi.util.OWLObjectDuplicator;
import org.semanticweb.owlapi.util.OWLObjectWalker;
import org.semanticweb.owlapi.util.OWLObjectVisitorAdapter;
import org.semanticweb.owlapi.manchestersyntax.renderer.ManchesterOWLSyntaxPrefixNameShortFormProvider;
import com.fasterxml.jackson.databind.*;

/** Stateless candidate construction: every request starts from the original OWL axiom set. */
public final class OntologyEvaluator {
    static final String NS = "https://example.org/ontologies/videocard#";
    static final ObjectMapper JSON = new ObjectMapper();

    public static final class EvaluationResult {
        public final Map<String,Long> counts = new TreeMap<>();
        public final List<Map<String,String>> violations = new ArrayList<>();
        public final List<String> axioms = new ArrayList<>();
        public boolean core_preserved;
        public String manchester;
    }

    static Set<OWLAxiom> parse(List<String> text) throws Exception {
        Set<OWLAxiom> result = new HashSet<>();
        for (String item : text) {
            OWLOntologyManager manager = OWLManager.createOWLOntologyManager();
            String doc = "Prefix(:=<"+NS+">)\nPrefix(owl:=<http://www.w3.org/2002/07/owl#>)\n"
                + "Prefix(rdfs:=<http://www.w3.org/2000/01/rdf-schema#>)\n"
                + "Prefix(xsd:=<http://www.w3.org/2001/XMLSchema#>)\nOntology(\n"+item+"\n)";
            OWLOntology parsed = manager.loadOntologyFromOntologyDocument(new StringDocumentSource(doc));
            if (!parsed.getImportsDeclarations().isEmpty() || !parsed.getAnnotations().isEmpty()
                || parsed.getAxiomCount() != 1) throw new IllegalArgumentException("AXIOM_SYNTAX: exactly one axiom per item required");
            result.addAll(parsed.getAxioms());
        }
        return result;
    }

    public static EvaluationResult evaluate(String base_path, List<String> add, List<String> remove) throws Exception {
        OWLOntologyManager manager = OWLManager.createOWLOntologyManager();
        OWLOntology base = manager.loadOntologyFromOntologyDocument(new File(base_path));
        if (!base.getImportsDeclarations().isEmpty()) throw new IllegalArgumentException("UNSUPPORTED_IMPORTS");
        Set<OWLAxiom> core = new HashSet<>(base.getAxioms());
        Set<OWLAxiom> additions = parse(add), removals = parse(remove);
        if (removals.stream().anyMatch(core::contains)) throw new IllegalArgumentException("CORE_REMOVAL");
        Set<OWLAxiom> candidate = new HashSet<>(core);
        candidate.addAll(additions);
        candidate.removeAll(removals);
        OWLOntologyManager isolated = OWLManager.createOWLOntologyManager();
        OWLOntology ontology = isolated.createOntology(base.getOntologyID());
        isolated.addAxioms(ontology, candidate);
        for (OWLAnnotation a : base.getAnnotations()) isolated.applyChange(new AddOntologyAnnotation(ontology, a));
        EvaluationResult result = audit(ontology);
        result.core_preserved = ontology.getAxioms().containsAll(core);
        return result;
    }

    static EvaluationResult audit(OWLOntology o) {
        EvaluationResult r = new EvaluationResult();
        Set<OWLEntity> entities = o.getSignature().stream().filter(e -> e.getIRI().toString().startsWith(NS)
            && (e.isOWLClass() || e.isOWLObjectProperty() || e.isOWLDataProperty())).collect(Collectors.toSet());
        if (o.getSignature().stream().anyMatch(e -> !e.isBuiltIn() && !e.isOWLDatatype() && !e.isOWLAnnotationProperty()
            && !e.getIRI().toString().startsWith(NS))) throw new IllegalArgumentException("UNSUPPORTED_NAMESPACE");
        List<OWLSubClassOfAxiom> hierarchy = o.getAxioms(AxiomType.SUBCLASS_OF).stream()
            .filter(a -> entities.contains(a.getSubClass()) && entities.contains(a.getSuperClass()))
            .collect(Collectors.toList());
        Set<OWLClass> equivalents = new HashSet<>();
        for (OWLEquivalentClassesAxiom a : o.getAxioms(AxiomType.EQUIVALENT_CLASSES))
            for (OWLClassExpression e : a.getClassExpressions()) if (entities.contains(e)) equivalents.add(e.asOWLClass());
        r.counts.put("C", entities.stream().filter(OWLEntity::isOWLClass).count());
        r.counts.put("Po", entities.stream().filter(OWLEntity::isOWLObjectProperty).count());
        r.counts.put("Pd", entities.stream().filter(OWLEntity::isOWLDataProperty).count());
        r.counts.put("H", (long)hierarchy.size()); r.counts.put("E", (long)equivalents.size());
        r.counts.put("A", (long)o.getAxiomCount()); r.counts.put("Al", (long)o.getLogicalAxiomCount());
        r.counts.put("Individuals", o.getIndividualsInSignature().stream().filter(e -> e.getIRI().toString().startsWith(NS)).count());
        r.counts.put("SubClassOf", (long)o.getAxioms(AxiomType.SUBCLASS_OF).size());
        r.counts.put("EquivalentClasses", (long)o.getAxioms(AxiomType.EQUIVALENT_CLASSES).size());
        r.counts.put("DisjointClasses", (long)o.getAxioms(AxiomType.DISJOINT_CLASSES).size());
        Map<String,Map<String,String>> violations = new TreeMap<>();
        for (OWLEntity e : entities) {
            String iri = e.getIRI().toString();
            boolean connected = o.getLogicalAxioms().stream().anyMatch(a -> a.getSignature().contains(e)
                && a.getSignature().stream().filter(entities::contains).count() >= 2);
            if (!connected) violation(violations,"P04",iri);
            for (String kind : Arrays.asList("label","comment")) {
                boolean present = o.getAnnotationAssertionAxioms(e.getIRI()).stream().anyMatch(a ->
                    a.getProperty().getIRI().toString().equals("http://www.w3.org/2000/01/rdf-schema#"+kind)
                    && a.getValue().asLiteral().isPresent() && a.getValue().asLiteral().get().hasLang("ru")
                    && !a.getValue().asLiteral().get().getLiteral().trim().isEmpty());
                if (!present) violation(violations,"P08",iri+"|"+kind);
            }
            if (e.isOWLObjectProperty()) {
                OWLObjectProperty p = e.asOWLObjectProperty();
                if (o.getObjectPropertyDomainAxioms(p).isEmpty()) violation(violations,"P11",iri+"|domain");
                if (o.getObjectPropertyRangeAxioms(p).isEmpty()) violation(violations,"P11",iri+"|range");
                if (o.getInverseObjectPropertyAxioms(p).isEmpty() && o.getSymmetricObjectPropertyAxioms(p).isEmpty()) violation(violations,"P13",iri);
            } else if (e.isOWLDataProperty()) {
                OWLDataProperty p = e.asOWLDataProperty();
                if (o.getDataPropertyDomainAxioms(p).isEmpty()) violation(violations,"P11",iri+"|domain");
                if (o.getDataPropertyRangeAxioms(p).isEmpty()) violation(violations,"P11",iri+"|range");
            }
            if (!e.getIRI().getRemainder().or("").matches(e.isOWLClass()?"[A-Z][A-Za-z0-9]*":"[a-z][A-Za-z0-9]*"))
                violation(violations,"P22",e.getEntityType()+"|"+iri);
        }
        for (OWLSubClassOfAxiom a : hierarchy) for (OWLSubClassOfAxiom b : hierarchy) {
            OWLClassExpression x = a.getSubClass(), y = b.getSubClass();
            if (a.getSuperClass().equals(b.getSuperClass()) && !x.equals(y)
                && o.getAxioms(AxiomType.DISJOINT_CLASSES).stream().noneMatch(d -> d.getClassExpressions().contains(x) && d.getClassExpressions().contains(y))) {
                List<String> pair = new ArrayList<>(Arrays.asList(x.asOWLClass().getIRI().toString(), y.asOWLClass().getIRI().toString()));
                Collections.sort(pair); violation(violations,"P10",String.join("|",pair));
            }
        }
        r.violations.addAll(violations.values()); r.counts.put("Q", (long)violations.size());
        r.manchester = manchester(o);
        r.axioms.addAll(o.getAxioms().stream().map(Object::toString).sorted().collect(Collectors.toList()));
        return r;
    }

    static String manchester(OWLOntology o) {
        ManchesterSyntaxDocumentFormat format = new ManchesterSyntaxDocumentFormat();
        format.setDefaultPrefix(NS);
        format.setPrefix("vc:", NS);
        format.setPrefix("owl:", "http://www.w3.org/2002/07/owl#");
        format.setPrefix("rdf:", "http://www.w3.org/1999/02/22-rdf-syntax-ns#");
        format.setPrefix("rdfs:", "http://www.w3.org/2000/01/rdf-schema#");
        format.setPrefix("xsd:", "http://www.w3.org/2001/XMLSchema#");
        // OWL API 4.5 renders decimal "40" as bare 40, which its parser reads
        // as integer. Render typed literals through temporary string tokens,
        // then restore their explicit lexical form and datatype in the document.
        // The actual ontology and the axiom/count interfaces are never changed.
        Set<OWLLiteral> literals = new TreeSet<>();
        List<OWLObject> objects = new ArrayList<>(o.getAxioms());
        objects.addAll(o.getAnnotations());
        new OWLObjectWalker<OWLObject>(objects).walkStructure(new OWLObjectVisitorAdapter() {
            @Override public void visit(OWLLiteral literal) {
                if (!literal.hasLang() && !literal.getDatatype().isString()) literals.add(literal);
            }
        });
        Map<OWLLiteral,OWLLiteral> replacements = new LinkedHashMap<>();
        String tokenPrefix = "__VC_TYPED_LITERAL_" + UUID.randomUUID().toString().replace("-", "") + "_";
        int index = 0;
        OWLOntologyManager manager = OWLManager.createOWLOntologyManager();
        for (OWLLiteral literal : literals) replacements.put(literal, manager.getOWLDataFactory().getOWLLiteral(tokenPrefix + index++));
        OWLObjectDuplicator duplicator = new OWLObjectDuplicator(manager.getOWLDataFactory(), Collections.<IRI,IRI>emptyMap(), replacements);
        try (ByteArrayOutputStream document = new ByteArrayOutputStream()) {
            OWLOntology copy = manager.createOntology(o.getOntologyID());
            for (OWLAxiom axiom : o.getAxioms()) manager.addAxiom(copy, duplicator.duplicateObject(axiom));
            for (OWLAnnotation annotation : o.getAnnotations()) manager.applyChange(new AddOntologyAnnotation(copy, duplicator.duplicateObject(annotation)));
            manager.saveOntology(copy, format, document);
            String result = document.toString(StandardCharsets.UTF_8);
            for (Map.Entry<OWLLiteral,OWLLiteral> entry : replacements.entrySet()) {
                String token = "\"" + entry.getValue().getLiteral() + "\"";
                result = result.replace(token + "^^xsd:string", entry.getKey().toString()).replace(token, entry.getKey().toString());
            }
            // The stock writer emits empty frames for referenced built-ins;
            // parsing those frames invents declaration axioms absent in the core.
            ManchesterOWLSyntaxPrefixNameShortFormProvider names = new ManchesterOWLSyntaxPrefixNameShortFormProvider(format);
            Set<OWLEntity> entities = new HashSet<>(copy.getSignature());
            entities.addAll(o.getSignature());
            for (OWLEntity entity : entities) {
                if (!entity.isBuiltIn() || o.containsAxiom(manager.getOWLDataFactory().getOWLDeclarationAxiom(entity))) continue;
                String kind = entity.isOWLDatatype() ? "Datatype" : entity.isOWLAnnotationProperty() ? "AnnotationProperty" : entity.isOWLClass() ? "Class" : null;
                if (kind != null) result = result.replaceAll("(?m)^" + kind + ": " + Pattern.quote(names.getShortForm(entity)) + "\\r?\\n(?:[ \\t]*\\r?\\n)*(?=\\S|\\z)", "");
            }
            return result;
        } catch (OWLOntologyStorageException | OWLOntologyCreationException | IOException error) {
            throw new IllegalStateException("Manchester serialization failed", error);
        }
    }
    static void violation(Map<String,Map<String,String>> target, String code, String key) {
        Map<String,String> value = new TreeMap<>(); value.put("code",code); value.put("key",key);
        target.put(code+"\u0000"+key,value);
    }
    public static void main(String[] args) throws Exception {
        try {
            JsonNode request = JSON.readTree(System.in);
            List<String> add = readList(request.get("add")), remove = readList(request.get("remove"));
            System.out.println(JSON.writeValueAsString(evaluate(request.get("base_path").textValue(),add,remove)));
        } catch (Exception e) {
            System.err.println("EVALUATION_ERROR: "+e.getClass().getSimpleName()+": "+e.getMessage());
            System.exit(2);
        }
    }
    static List<String> readList(JsonNode node) {
        if (node == null || !node.isArray()) throw new IllegalArgumentException("Expected axiom array");
        List<String> values = new ArrayList<>();
        for (JsonNode item : node) { if (!item.isTextual()) throw new IllegalArgumentException("Expected axiom text"); values.add(item.textValue()); }
        return values;
    }
}
