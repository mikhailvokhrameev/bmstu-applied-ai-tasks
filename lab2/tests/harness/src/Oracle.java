import java.util.ArrayList;
import java.util.List;
import org.semanticweb.owlapi.model.OWLDataRange;
import org.semanticweb.owlapi.vocab.OWL2Datatype;
import org.semanticweb.owlapi.vocab.OWLFacet;

/**
 * The independent oracle for T01/T02/T04: literal tables transcribed from the project constraints
 * (spec Tables 1-3, clauses 4.4.1-4.4.7). Deliberately NOT derived from the ontology under test.
 */
final class Oracle {
    private Oracle() {}

    static final String ONTOLOGY_IRI = "https://example.org/ontologies/videocard";
    static final String VERSION_IRI = "https://example.org/ontologies/videocard/1.0.0";

    /** Table 1: the 13 base classes. */
    static final List<String> CLASSES = List.of(
            "VideoCardModel", "ModelComponent", "GPUModel", "MemoryConfiguration", "CoolingSystem",
            "ActiveCooling", "PassiveCooling", "Manufacturer", "ConnectionInterface", "VideoOutput",
            "MemoryType", "GPUArchitecture", "Purpose");

    /** 4.4.3: the two defined classes. */
    static final List<String> DEFINED_CLASSES = List.of("CardWith8GBMemory", "CardWithActiveCooling");

    /** Table 2: object property, domain, range. */
    static final String[][] OBJECT_PROPERTIES = {
        {"usesGPU", "VideoCardModel", "GPUModel"},
        {"hasMemory", "VideoCardModel", "MemoryConfiguration"},
        {"hasCooling", "VideoCardModel", "CoolingSystem"},
        {"hasInterface", "VideoCardModel", "ConnectionInterface"},
        {"hasVideoOutput", "VideoCardModel", "VideoOutput"},
        {"producedByManufacturer", "VideoCardModel", "Manufacturer"},
        {"gpuProducedBy", "GPUModel", "Manufacturer"},
        {"hasArchitecture", "GPUModel", "GPUArchitecture"},
        {"hasMemoryType", "MemoryConfiguration", "MemoryType"},
        {"hasPurpose", "VideoCardModel", "Purpose"},
    };

    /** Table 3: data properties (the first one, name, has a union domain, see {@link #NAME_DOMAIN}). */
    static final List<String> DATA_PROPERTIES = List.of(
            "name", "volumeGiB", "busWidthBit", "frequencyMHz", "powerW", "lengthMM", "fanCount");

    /** Single-domain data properties: property, domain class. */
    static final String[][] DATA_PROPERTY_DOMAINS = {
        {"volumeGiB", "MemoryConfiguration"},
        {"busWidthBit", "MemoryConfiguration"},
        {"frequencyMHz", "GPUModel"},
        {"powerW", "VideoCardModel"},
        {"lengthMM", "VideoCardModel"},
        {"fanCount", "CoolingSystem"},
    };

    /** 4.2.4: the domain of {@code name} is ONE ObjectUnionOf of these eight classes. */
    static final List<String> NAME_DOMAIN = List.of(
            "VideoCardModel", "GPUModel", "Manufacturer", "ConnectionInterface",
            "VideoOutput", "MemoryType", "GPUArchitecture", "Purpose");

    /** Exactly the numeric data properties are functional; name and all object properties are not. */
    static final List<String> FUNCTIONAL_DATA_PROPERTIES = List.of(
            "volumeGiB", "busWidthBit", "frequencyMHz", "powerW", "lengthMM", "fanCount");

    /** 4.4.2: the eight top-level classes, pairwise disjoint. */
    static final List<String> TOP_LEVEL = List.of(
            "VideoCardModel", "ModelComponent", "Manufacturer", "ConnectionInterface",
            "VideoOutput", "MemoryType", "GPUArchitecture", "Purpose");

    /** 4.4.2: the three component kinds, pairwise disjoint. */
    static final List<String> COMPONENT_KINDS = List.of("GPUModel", "MemoryConfiguration", "CoolingSystem");

    /** Asserted hierarchy: subclass, superclass. */
    static final String[][] SUBCLASS_OF = {
        {"GPUModel", "ModelComponent"},
        {"MemoryConfiguration", "ModelComponent"},
        {"CoolingSystem", "ModelComponent"},
        {"ActiveCooling", "CoolingSystem"},
        {"PassiveCooling", "CoolingSystem"},
    };

    /** The eight teaching models U01..U08. */
    static final List<String> MODELS = List.of("U01", "U02", "U03", "U04", "U05", "U06", "U07", "U08");

    /** All required disjoint pairs of 4.4.2 (28 + 3 + 1 = 32), as {a, b}. */
    static List<String[]> disjointPairs() {
        List<String[]> pairs = new ArrayList<>();
        addPairs(pairs, TOP_LEVEL);
        addPairs(pairs, COMPONENT_KINDS);
        pairs.add(new String[] {"ActiveCooling", "PassiveCooling"});
        return pairs;
    }

    private static void addPairs(List<String[]> pairs, List<String> names) {
        for (int i = 0; i < names.size(); i++) {
            for (int j = i + 1; j < names.size(); j++) {
                pairs.add(new String[] {names.get(i), names.get(j)});
            }
        }
    }

    /** Expected range of a data property of Table 3; "decimal > 0" is DatatypeRestriction(xsd:decimal minExclusive 0). */
    static OWLDataRange dataRange(String dataProperty) {
        var df = Support.DF;
        switch (dataProperty) {
            case "name":
                return df.getOWLDatatype(OWL2Datatype.XSD_STRING.getIRI());
            case "volumeGiB":
            case "busWidthBit":
                return df.getOWLDatatype(OWL2Datatype.XSD_POSITIVE_INTEGER.getIRI());
            case "fanCount":
                return df.getOWLDatatype(OWL2Datatype.XSD_NON_NEGATIVE_INTEGER.getIRI());
            case "frequencyMHz":
            case "powerW":
            case "lengthMM":
                return df.getOWLDatatypeRestriction(df.getOWLDatatype(OWL2Datatype.XSD_DECIMAL.getIRI()),
                        df.getOWLFacetRestriction(OWLFacet.MIN_EXCLUSIVE, df.getOWLLiteral("0", OWL2Datatype.XSD_DECIMAL)));
            default:
                throw new IllegalArgumentException(dataProperty);
        }
    }
}
