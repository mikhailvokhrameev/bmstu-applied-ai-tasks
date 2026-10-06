import java.io.PrintStream;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import java.util.TreeSet;
import java.util.stream.Collectors;
import org.semanticweb.owlapi.model.AxiomType;
import org.semanticweb.owlapi.model.OWLAnnotation;
import org.semanticweb.owlapi.model.OWLAnnotationAssertionAxiom;
import org.semanticweb.owlapi.model.OWLClass;
import org.semanticweb.owlapi.model.OWLClassExpression;
import org.semanticweb.owlapi.model.OWLDataFactory;
import org.semanticweb.owlapi.model.OWLDataProperty;
import org.semanticweb.owlapi.model.OWLDifferentIndividualsAxiom;
import org.semanticweb.owlapi.model.OWLDisjointClassesAxiom;
import org.semanticweb.owlapi.model.OWLEntity;
import org.semanticweb.owlapi.model.OWLEquivalentClassesAxiom;
import org.semanticweb.owlapi.model.OWLLiteral;
import org.semanticweb.owlapi.model.OWLNamedIndividual;
import org.semanticweb.owlapi.model.OWLObjectProperty;
import org.semanticweb.owlapi.model.OWLOntology;
import org.semanticweb.owlapi.model.OWLSubClassOfAxiom;
import org.semanticweb.owlapi.profiles.OWL2DLProfile;
import org.semanticweb.owlapi.profiles.OWLProfileReport;
import org.semanticweb.owlapi.profiles.OWLProfileViolation;
import org.semanticweb.owlapi.vocab.OWL2Datatype;
import org.semanticweb.owlapi.vocab.OWLFacet;
import org.semanticweb.owlapi.vocab.OWLRDFVocabulary;

/**
 * T02 (spec 4.2.1-4.2.4, 4.4.1): the file parses, is OWL 2 DL, has the required vocabulary with the right
 * domains/ranges/characteristics, Russian labels and comments, the required restrictions, disjointness,
 * defined-class definitions and a single DifferentIndividuals axiom. All expectations come from {@link Oracle}.
 */
public class T02OntologyStructure implements TestGroup {
    private static final OWLDataFactory DF = Support.DF;
    private String note = "";

    @Override
    public String id() {
        return "T02";
    }

    @Override
    public String name() {
        return "T02 ontology structure, OWL 2 DL profile, annotations";
    }

    @Override
    public String note() {
        return note;
    }

    @Override
    public boolean run(PrintStream out) throws Exception {
        Checks c = new Checks(out);
        OWLOntology ont = null;
        try {
            ont = Support.load(Support.ontologyFile().toFile());
            c.check("file ontology/videocard.owl parses", true);
        } catch (Exception e) {
            c.check("file ontology/videocard.owl parses", false, e.toString());
        }
        if (ont != null) verify(ont, c, out);
        note = c.summary() + (ont != null ? "; " + ont.getAxiomCount() + " axioms" : "");
        return c.ok();
    }

    /** Parses {@code file} (reported as a check) and, if that works, runs {@link #verify(OWLOntology, Checks, PrintStream)}. */
    static void verify(Path file, Checks c, PrintStream out) {
        OWLOntology ont;
        try {
            ont = Support.load(file.toFile());
            c.check("file parses", true);
        } catch (Exception e) {
            c.check("file parses", false, e.toString());
            return;
        }
        verify(ont, c, out);
    }

    /** All structural checks on an already parsed ontology; reusable on re-saved or mutated copies. */
    static void verify(OWLOntology ont, Checks c, PrintStream out) {
        out.println("axiom count: " + ont.getAxiomCount());
        checkProfile(ont, c, out);
        checkIdentity(ont, c);
        checkEntities(ont, c, out);
        checkHierarchy(ont, c);
        checkObjectProperties(ont, c);
        checkDataProperties(ont, c);
        checkAnnotations(ont, c);
        checkVideoCardRestrictions(ont, c);
        checkDisjointness(ont, c);
        checkDefinedClasses(ont, c);
        checkDifferentIndividuals(ont, c);
    }

    // ---- profile, imports, identity -------------------------------------------------------------------

    private static void checkProfile(OWLOntology ont, Checks c, PrintStream out) {
        OWLProfileReport report = new OWL2DLProfile().checkOntology(ont);
        for (OWLProfileViolation v : report.getViolations()) out.println("  violation: " + v);
        c.check("OWL2DLProfile reports no violations (" + report.getViolations().size() + " found)",
                report.isInProfile());
        c.check("no owl:imports declarations", ont.getImportsDeclarations().isEmpty()
                && ont.getDirectImports().isEmpty());
    }

    private static void checkIdentity(OWLOntology ont, Checks c) {
        var id = ont.getOntologyID();
        c.eq("ontology IRI", Oracle.ONTOLOGY_IRI,
                id.getOntologyIRI().isPresent() ? id.getOntologyIRI().get().toString() : "(none)");
        c.eq("version IRI", Oracle.VERSION_IRI,
                id.getVersionIRI().isPresent() ? id.getVersionIRI().get().toString() : "(none)");
    }

    // ---- entity inventory -----------------------------------------------------------------------------

    private static void checkEntities(OWLOntology ont, Checks c, PrintStream out) {
        Set<String> classes = names(ont.getClassesInSignature());
        Set<String> objectProps = names(ont.getObjectPropertiesInSignature());
        Set<String> dataProps = names(ont.getDataPropertiesInSignature());
        Set<String> individuals = names(ont.getIndividualsInSignature());
        out.println("entity counts: classes=" + classes.size() + ", object properties=" + objectProps.size()
                + ", data properties=" + dataProps.size() + ", individuals=" + individuals.size());
        printListing(out, "classes", classes);
        printListing(out, "object properties", objectProps);
        printListing(out, "data properties", dataProps);
        printListing(out, "individuals", individuals);

        Set<String> expectedClasses = new TreeSet<>(Oracle.CLASSES);
        expectedClasses.addAll(Oracle.DEFINED_CLASSES);
        Set<String> expectedObjectProps = new TreeSet<>();
        for (String[] p : Oracle.OBJECT_PROPERTIES) expectedObjectProps.add(p[0]);
        c.eq("classes in signature are exactly the 13 + 2 required", expectedClasses, classes);
        c.eq("object properties in signature are exactly the 10 required", expectedObjectProps, objectProps);
        c.eq("data properties in signature are exactly the 7 required", new TreeSet<>(Oracle.DATA_PROPERTIES), dataProps);
        c.check("individuals include U01..U08", individuals.containsAll(Oracle.MODELS),
                "missing " + Oracle.MODELS.stream().filter(m -> !individuals.contains(m)).collect(Collectors.toList()));

        List<String> foreign = new ArrayList<>();
        for (OWLEntity e : ont.getSignature()) {
            if (e.isBuiltIn()) continue;
            if (!e.getIRI().toString().startsWith(Support.NS)) foreign.add(e.getIRI().toString());
        }
        c.check("every user entity lives in the single namespace " + Support.NS, foreign.isEmpty(), foreign.toString());
    }

    /** Local names of the non-built-in entities (owl:Thing/owl:Nothing are built in). */
    private static Set<String> names(Set<? extends OWLEntity> entities) {
        Set<String> names = new TreeSet<>();
        for (OWLEntity e : entities) {
            if (e.isBuiltIn()) continue;
            names.add(Support.local(e.getIRI()));
        }
        return names;
    }

    private static void printListing(PrintStream out, String title, Set<String> names) {
        out.println("  " + title + " (" + names.size() + "): " + String.join(", ", names));
    }

    // ---- hierarchy, domains and ranges ----------------------------------------------------------------

    private static void checkHierarchy(OWLOntology ont, Checks c) {
        List<String> missing = new ArrayList<>();
        for (String[] sc : Oracle.SUBCLASS_OF) {
            if (!ont.containsAxiom(DF.getOWLSubClassOfAxiom(Support.cls(sc[0]), Support.cls(sc[1])))) {
                missing.add(sc[0] + " SubClassOf " + sc[1]);
            }
        }
        c.checkAll("asserted class hierarchy", Oracle.SUBCLASS_OF.length, missing);
    }

    private static void checkObjectProperties(OWLOntology ont, Checks c) {
        List<String> bad = new ArrayList<>();
        for (String[] p : Oracle.OBJECT_PROPERTIES) {
            OWLObjectProperty prop = Support.op(p[0]);
            Set<OWLClassExpression> domains = ont.getObjectPropertyDomainAxioms(prop).stream()
                    .map(a -> a.getDomain()).collect(Collectors.toSet());
            Set<OWLClassExpression> ranges = ont.getObjectPropertyRangeAxioms(prop).stream()
                    .map(a -> a.getRange()).collect(Collectors.toSet());
            if (!domains.equals(Set.of(Support.cls(p[1])))) bad.add(p[0] + " domain " + domains);
            if (!ranges.equals(Set.of(Support.cls(p[2])))) bad.add(p[0] + " range " + ranges);
        }
        c.checkAll("domain and range of the 10 object properties exactly as in Table 2",
                Oracle.OBJECT_PROPERTIES.length * 2, bad);

        Set<String> functionalObject = ont.getAxioms(AxiomType.FUNCTIONAL_OBJECT_PROPERTY).stream()
                .map(a -> a.getProperty().toString()).collect(Collectors.toSet());
        c.check("no object property is functional", functionalObject.isEmpty(), functionalObject.toString());
    }

    private static void checkDataProperties(OWLOntology ont, Checks c) {
        List<String> bad = new ArrayList<>();
        int total = 0;

        OWLDataProperty name = Support.dp("name");
        Set<OWLClassExpression> nameDomains = ont.getDataPropertyDomainAxioms(name).stream()
                .map(a -> a.getDomain()).collect(Collectors.toSet());
        Set<OWLClassExpression> union = new TreeSet<>();
        Oracle.NAME_DOMAIN.forEach(n -> union.add(Support.cls(n)));
        c.eq("name has exactly one domain axiom: ObjectUnionOf of the 8 classes",
                Set.of(DF.getOWLObjectUnionOf(union)), nameDomains);

        for (String[] d : Oracle.DATA_PROPERTY_DOMAINS) {
            total++;
            Set<OWLClassExpression> domains = ont.getDataPropertyDomainAxioms(Support.dp(d[0])).stream()
                    .map(a -> a.getDomain()).collect(Collectors.toSet());
            if (!domains.equals(Set.of(Support.cls(d[1])))) bad.add(d[0] + " domain " + domains);
        }
        for (String p : Oracle.DATA_PROPERTIES) {
            total++;
            Set<Object> ranges = ont.getDataPropertyRangeAxioms(Support.dp(p)).stream()
                    .map(a -> (Object) a.getRange()).collect(Collectors.toSet());
            if (!ranges.equals(Set.of(Oracle.dataRange(p)))) bad.add(p + " range " + ranges);
        }
        c.checkAll("domain and range of the 7 data properties as in Table 3 (decimal > 0 = minExclusive 0)", total, bad);

        Set<String> functional = ont.getAxioms(AxiomType.FUNCTIONAL_DATA_PROPERTY).stream()
                .map(a -> Support.local(a.getProperty().asOWLDataProperty().getIRI()))
                .collect(Collectors.toCollection(TreeSet::new));
        c.eq("functional data properties are exactly the six numeric ones",
                new TreeSet<>(Oracle.FUNCTIONAL_DATA_PROPERTIES), functional);
    }

    // ---- annotations ----------------------------------------------------------------------------------

    private static void checkAnnotations(OWLOntology ont, Checks c) {
        List<String> missing = new ArrayList<>();
        int total = 0;
        for (OWLEntity e : userEntities(ont)) {
            total++;
            boolean label = hasRussian(ont, e, OWLRDFVocabulary.RDFS_LABEL);
            boolean comment = hasRussian(ont, e, OWLRDFVocabulary.RDFS_COMMENT);
            if (!label || !comment) {
                missing.add(Support.local(e.getIRI()) + (label ? "" : " [no @ru label]")
                        + (comment ? "" : " [no @ru comment]"));
            }
        }
        c.checkAll("every class, property and individual has an rdfs:label@ru and an rdfs:comment@ru", total, missing);
    }

    private static Set<OWLEntity> userEntities(OWLOntology ont) {
        Set<OWLEntity> all = new java.util.LinkedHashSet<>();
        for (OWLClass e : ont.getClassesInSignature()) if (!e.isBuiltIn()) all.add(e);
        for (OWLObjectProperty e : ont.getObjectPropertiesInSignature()) if (!e.isBuiltIn()) all.add(e);
        for (OWLDataProperty e : ont.getDataPropertiesInSignature()) if (!e.isBuiltIn()) all.add(e);
        for (OWLNamedIndividual e : ont.getIndividualsInSignature()) all.add(e);
        return all;
    }

    private static boolean hasRussian(OWLOntology ont, OWLEntity e, OWLRDFVocabulary property) {
        for (OWLAnnotationAssertionAxiom ax : ont.getAnnotationAssertionAxioms(e.getIRI())) {
            OWLAnnotation a = ax.getAnnotation();
            if (!a.getProperty().getIRI().equals(property.getIRI())) continue;
            if (a.getValue() instanceof OWLLiteral) {
                OWLLiteral lit = (OWLLiteral) a.getValue();
                if ("ru".equals(lit.getLang()) && !lit.getLiteral().trim().isEmpty()) return true;
            }
        }
        return false;
    }

    // ---- VideoCardModel restrictions, disjointness, definitions, DifferentIndividuals -----------------

    private static void checkVideoCardRestrictions(OWLOntology ont, Checks c) {
        OWLClass vcm = Support.cls("VideoCardModel");
        Set<OWLClassExpression> supers = ont.getSubClassAxiomsForSubClass(vcm).stream()
                .map(OWLSubClassOfAxiom::getSuperClass).collect(Collectors.toSet());

        List<String> missing = new ArrayList<>();
        int exact = 0;
        int only = 0;
        for (String[] p : Oracle.OBJECT_PROPERTIES) {
            if (!p[1].equals("VideoCardModel") || p[0].equals("hasVideoOutput") || p[0].equals("hasPurpose")) continue;
            OWLObjectProperty prop = Support.op(p[0]);
            exact++;
            only++;
            if (!supers.contains(DF.getOWLObjectExactCardinality(1, prop))) missing.add("exactly 1 " + p[0]);
            if (!supers.contains(DF.getOWLObjectAllValuesFrom(prop, Support.cls(p[2])))) {
                missing.add(p[0] + " only " + p[2]);
            }
        }
        c.checkAll("VideoCardModel: 5 ExactCardinality(1) and 5 AllValuesFrom restrictions", exact + only, missing);
        c.check("VideoCardModel: MinCardinality(1) hasVideoOutput",
                supers.contains(DF.getOWLObjectMinCardinality(1, Support.op("hasVideoOutput"))));

        long exactCount = supers.stream().filter(s -> s.getClassExpressionType()
                == org.semanticweb.owlapi.model.ClassExpressionType.OBJECT_EXACT_CARDINALITY).count();
        long onlyCount = supers.stream().filter(s -> s.getClassExpressionType()
                == org.semanticweb.owlapi.model.ClassExpressionType.OBJECT_ALL_VALUES_FROM).count();
        long minCount = supers.stream().filter(s -> s.getClassExpressionType()
                == org.semanticweb.owlapi.model.ClassExpressionType.OBJECT_MIN_CARDINALITY).count();
        c.check("VideoCardModel carries exactly 5 exact / 5 only / 1 min restrictions (found " + exactCount + "/"
                + onlyCount + "/" + minCount + ")", exactCount == 5 && onlyCount == 5 && minCount == 1);
    }

    private static void checkDisjointness(OWLOntology ont, Checks c) {
        List<String> missing = new ArrayList<>();
        List<String[]> pairs = Oracle.disjointPairs();
        for (String[] pair : pairs) {
            OWLClass b = Support.cls(pair[1]);
            boolean found = false;
            for (OWLDisjointClassesAxiom ax : ont.getDisjointClassesAxioms(Support.cls(pair[0]))) {
                if (ax.getClassExpressions().contains(b)) {
                    found = true;
                    break;
                }
            }
            if (!found) missing.add(pair[0] + " / " + pair[1]);
        }
        c.checkAll("asserted DisjointClasses for the required 4.4.2 pairs (8 top-level, 3 component kinds, "
                + "Active/Passive)", pairs.size(), missing);
    }

    private static void checkDefinedClasses(OWLOntology ont, Checks c) {
        OWLClass eightGb = Support.cls("CardWith8GBMemory");
        OWLClassExpression eightGbDefinition = DF.getOWLObjectIntersectionOf(Support.cls("VideoCardModel"),
                DF.getOWLObjectSomeValuesFrom(Support.op("hasMemory"),
                        DF.getOWLDataSomeValuesFrom(Support.dp("volumeGiB"),
                                DF.getOWLDatatypeRestriction(DF.getOWLDatatype(OWL2Datatype.XSD_INTEGER.getIRI()),
                                        DF.getOWLFacetRestriction(OWLFacet.MIN_INCLUSIVE,
                                                DF.getOWLLiteral(8))))));
        c.check("CardWith8GBMemory == VideoCardModel and hasMemory some (volumeGiB some xsd:integer[>= 8])",
                isDefinedAs(ont, eightGb, eightGbDefinition));

        OWLClass active = Support.cls("CardWithActiveCooling");
        OWLClassExpression activeDefinition = DF.getOWLObjectIntersectionOf(Support.cls("VideoCardModel"),
                DF.getOWLObjectSomeValuesFrom(Support.op("hasCooling"), Support.cls("ActiveCooling")));
        c.check("CardWithActiveCooling == VideoCardModel and hasCooling some ActiveCooling",
                isDefinedAs(ont, active, activeDefinition));
    }

    private static boolean isDefinedAs(OWLOntology ont, OWLClass defined, OWLClassExpression definition) {
        for (OWLEquivalentClassesAxiom ax : ont.getEquivalentClassesAxioms(defined)) {
            if (ax.getClassExpressions().equals(Set.of(defined, definition))) return true;
        }
        return false;
    }

    private static void checkDifferentIndividuals(OWLOntology ont, Checks c) {
        Set<OWLDifferentIndividualsAxiom> axioms = ont.getAxioms(AxiomType.DIFFERENT_INDIVIDUALS);
        c.eq("exactly one DifferentIndividuals/AllDifferent axiom", 1, axioms.size());
        if (axioms.size() == 1) {
            Set<OWLNamedIndividual> inAxiom = axioms.iterator().next().getIndividuals().stream()
                    .filter(i -> i.isNamed()).map(i -> i.asOWLNamedIndividual()).collect(Collectors.toSet());
            Set<OWLNamedIndividual> all = ont.getIndividualsInSignature();
            c.check("the DifferentIndividuals axiom covers all " + all.size() + " named individuals",
                    inAxiom.equals(all), "differs by " + symmetricDifference(inAxiom, all));
        }
        c.eq("no SameIndividual axioms", 0, ont.getAxioms(AxiomType.SAME_INDIVIDUAL).size());
    }

    private static Set<String> symmetricDifference(Set<OWLNamedIndividual> a, Set<OWLNamedIndividual> b) {
        Set<String> diff = new TreeSet<>();
        for (OWLNamedIndividual i : a) if (!b.contains(i)) diff.add(Support.local(i.getIRI()));
        for (OWLNamedIndividual i : b) if (!a.contains(i)) diff.add(Support.local(i.getIRI()));
        return diff;
    }
}
