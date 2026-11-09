import java.awt.Component;
import java.awt.Container;
import java.awt.Graphics2D;
import java.awt.Window;
import java.awt.image.BufferedImage;
import java.io.PrintWriter;
import java.io.StringWriter;
import java.lang.instrument.Instrumentation;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.lang.reflect.Proxy;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Properties;
import java.util.Set;
import java.util.TreeSet;
import java.util.concurrent.Callable;
import java.util.concurrent.FutureTask;
import java.util.concurrent.atomic.AtomicLong;
import javax.imageio.ImageIO;
import javax.swing.AbstractButton;
import javax.swing.JLabel;
import javax.swing.JList;
import javax.swing.JCheckBox;
import javax.swing.JTabbedPane;
import javax.swing.JTable;
import javax.swing.SwingUtilities;
import javax.swing.event.ListDataEvent;
import javax.swing.event.ListDataListener;
import javax.swing.text.JTextComponent;

/** Launch-only evidence collector for the actual installed Protégé application.
 * No attach, accessibility, private reflection, independent reasoner or desktop capture.
 */
public final class AcceptanceAgent {
    static Path out;
    static ClassLoader owlLoader;
    static Object pm;
    static Object factory;
    static final String NS = "https://example.org/ontologies/videocard#";
    static final List<Map<String,Object>> cases = new ArrayList<>();

    static Object invoke(Object target, String name, Object... args) throws Exception {
        Class<?> type = target instanceof Class ? (Class<?>)target : target.getClass();
        for (Method m : type.getMethods()) {
            if (!m.getName().equals(name) || m.getParameterCount() != args.length) continue;
            Class<?>[] types = m.getParameterTypes();
            boolean fits = true;
            for (int i = 0; i < args.length; i++) {
                Class<?> t = types[i];
                if (t == boolean.class) t = Boolean.class;
                if (t == int.class) t = Integer.class;
                if (args[i] != null && !t.isInstance(args[i])) fits = false;
            }
            if (!fits) continue;
            Method usable = m;
            if (!Modifier.isPublic(m.getDeclaringClass().getModifiers())) {
                usable = publicDeclaration(type, name, types);
                if (usable == null) continue;
            }
            try { return usable.invoke(target instanceof Class ? null : target, args); }
            catch (InvocationTargetException e) {
                Throwable cause = e.getCause();
                if (cause instanceof Exception) throw (Exception)cause;
                throw e;
            }
        }
        throw new NoSuchMethodException(type.getName() + "." + name + "/" + args.length);
    }

    static Method publicDeclaration(Class<?> type, String name, Class<?>[] parameters) {
        for (Class<?> face : type.getInterfaces()) {
            try {
                Method m = face.getMethod(name, parameters);
                if (Modifier.isPublic(m.getDeclaringClass().getModifiers())) return m;
            } catch (NoSuchMethodException ignored) { }
            Method nested = publicDeclaration(face, name, parameters);
            if (nested != null) return nested;
        }
        Class<?> parent = type.getSuperclass();
        if (parent != null) {
            try {
                Method m = parent.getMethod(name, parameters);
                if (Modifier.isPublic(m.getDeclaringClass().getModifiers())) return m;
            } catch (NoSuchMethodException ignored) { }
            return publicDeclaration(parent, name, parameters);
        }
        return null;
    }

    static <T> T edt(Callable<T> work) throws Exception {
        FutureTask<T> task = new FutureTask<>(work);
        SwingUtilities.invokeAndWait(task);
        return task.get();
    }

    static String json(Object value) {
        if (value == null) return "null";
        if (value instanceof Boolean || value instanceof Number) return value.toString();
        if (value instanceof Map) {
            List<String> items = new ArrayList<>();
            ((Map<?,?>)value).forEach((k,v) -> items.add(json(k.toString()) + ":" + json(v)));
            return "{" + String.join(",", items) + "}";
        }
        if (value instanceof Collection) {
            List<String> items = new ArrayList<>();
            for (Object item : (Collection<?>)value) items.add(json(item));
            return "[" + String.join(",", items) + "]";
        }
        return "\"" + value.toString().replace("\\", "\\\\").replace("\"", "\\\"")
                .replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t") + "\"";
    }

    static String sha(Path path) throws Exception {
        StringBuilder s = new StringBuilder();
        for (byte b : MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(path)))
            s.append(String.format("%02x", b & 255));
        return s.toString();
    }

    static Map<String,Object> counts(Object ontology) throws Exception {
        Map<String,Object> m = new LinkedHashMap<>();
        m.put("ontology_id", invoke(ontology, "getOntologyID").toString());
        for (String method : new String[]{"getAxiomCount", "getLogicalAxiomCount", "getClassesInSignature",
                "getObjectPropertiesInSignature", "getDataPropertiesInSignature", "getIndividualsInSignature"}) {
            Object v = invoke(ontology, method);
            m.put(method, v instanceof Collection ? ((Collection<?>)v).size() : v);
        }
        m.put("class_count_includes_owl_Thing_if_in_signature", true);
        return m;
    }

    static void dump(Component c, StringBuilder s, int depth) {
        if (depth > 35) return;
        String t = c instanceof JLabel ? ((JLabel)c).getText()
                : c instanceof AbstractButton ? ((AbstractButton)c).getText()
                : c instanceof JTextComponent ? ((JTextComponent)c).getText() : "";
        if (t != null && !t.isEmpty()) s.append(c.getClass().getName()).append(" : ").append(t).append('\n');
        if (c instanceof JTabbedPane) {
            JTabbedPane tabs = (JTabbedPane)c;
            for (int i = 0; i < tabs.getTabCount(); i++) s.append("TAB ").append(i).append(" : ").append(tabs.getTitleAt(i)).append('\n');
        }
        if (c instanceof JTable) {
            JTable table = (JTable)c;
            s.append("TABLE ").append(table.getRowCount()).append("x").append(table.getColumnCount()).append('\n');
            for (int row = 0; row < table.getRowCount(); row++) {
                for (int col = 0; col < table.getColumnCount(); col++) s.append(table.getValueAt(row,col)).append('\t');
                s.append('\n');
            }
        }
        if (c instanceof JList) {
            JList<?> list = (JList<?>)c;
            s.append("LIST ").append(list.getClass().getName()).append(" size=").append(list.getModel().getSize()).append('\n');
            for (int i = 0; i < list.getModel().getSize(); i++) s.append("  ").append(list.getModel().getElementAt(i)).append('\n');
        }
        if (c instanceof Container) for (Component child : ((Container)c).getComponents()) dump(child,s,depth+1);
    }

    static void capture(Object kit, Path directory) throws Exception {
        Files.createDirectories(directory);
        edt(() -> {
            Object workspace = invoke(kit,"getWorkspace");
            Window window = (Window)invoke(pm,"getFrame",workspace);
            StringBuilder ui = new StringBuilder();
            ui.append("Actual Protégé WorkspaceFrame; Swing component rendering only.\n");
            dump(window,ui,0);
            Files.writeString(directory.resolve("ui.txt"),ui.toString());
            if (!window.isVisible() || window.getWidth() == 0 || window.getHeight() == 0)
                throw new IllegalStateException("Actual WorkspaceFrame is not visible");
            BufferedImage image = new BufferedImage(window.getWidth(),window.getHeight(),BufferedImage.TYPE_INT_RGB);
            Graphics2D graphics = image.createGraphics();
            window.paintAll(graphics);
            graphics.dispose();
            ImageIO.write(image,"png",directory.resolve("window.png").toFile());
            return null;
        });
    }

    static void captureStartup() throws Exception {
        edt(() -> {
            StringBuilder text = new StringBuilder();
            int index = 0;
            for (Window window : Window.getWindows()) {
                if (!window.isVisible() || window.getWidth() == 0 || window.getHeight() == 0) continue;
                text.append("OWN STARTUP WINDOW ").append(window.getClass().getName()).append('\n');
                dump(window,text,0);
                BufferedImage image = new BufferedImage(window.getWidth(),window.getHeight(),BufferedImage.TYPE_INT_RGB);
                Graphics2D graphics = image.createGraphics();
                window.paintAll(graphics); graphics.dispose();
                ImageIO.write(image,"png",out.resolve("startup-window-"+(index++)+".png").toFile());
            }
            Files.writeString(out.resolve("startup-ui.txt"),text.toString());
            return null;
        });
    }

    static boolean queryResultsPass(List<Object> results) {
        for (Object item : results) if (!Boolean.TRUE.equals(((Map<?,?>)item).get("passed"))) return false;
        return !results.isEmpty();
    }

    static Component find(Component root, java.util.function.Predicate<Component> predicate) {
        if (predicate.test(root)) return root;
        if (root instanceof Container) for (Component child : ((Container)root).getComponents()) {
            Component found = find(child,predicate);
            if (found != null) return found;
        }
        return null;
    }

    static boolean selectTab(Component root, String title) {
        if (root instanceof JTabbedPane) {
            JTabbedPane tabs = (JTabbedPane)root;
            for (int i = 0; i < tabs.getTabCount(); i++) if (tabs.getTitleAt(i).equals(title)) {
                tabs.setSelectedIndex(i); return true;
            }
        }
        if (root instanceof Container) for (Component child : ((Container)root).getComponents())
            if (selectTab(child,title)) return true;
        return false;
    }

    static List<Object> uiQueries(Object kit, Path plan, Path directory) throws Exception {
        Component workspace = (Component)invoke(kit,"getWorkspace");
        edt(() -> {
            if (!selectTab(workspace,"DL Query")) throw new IllegalStateException("No installed DL Query tab");
            return null;
        });
        Thread.sleep(500);
        Component view = edt(() -> find(workspace,c -> c.getClass().getName().equals("org.coode.dlquery.OWLClassExpressionEditorViewComponent")));
        if (view == null) throw new IllegalStateException("Actual DL Query view missing");
        JTextComponent editor = (JTextComponent)edt(() -> find(view,c -> c.getClass().getName().equals("org.protege.editor.owl.ui.clsdescriptioneditor.ExpressionEditor")));
        AbstractButton execute = (AbstractButton)edt(() -> find(view,c -> c instanceof AbstractButton && "Execute".equals(((AbstractButton)c).getText())));
        JList<?> results = (JList<?>)edt(() -> find(view,c -> c.getClass().getName().equals("org.coode.dlquery.ResultsList")));
        if (editor == null || execute == null || results == null) throw new IllegalStateException("Actual DL Query public Swing components missing");
        edt(() -> {
            find(view,c -> {
                if (c instanceof JCheckBox) {
                    JCheckBox checkbox = (JCheckBox)c;
                    boolean desired = "Instances".equals(checkbox.getText());
                    if (checkbox.isSelected() != desired) checkbox.doClick();
                }
                return false;
            });
            return null;
        });
        AtomicLong revisions = new AtomicLong();
        java.beans.PropertyChangeListener modelListener = event -> revisions.incrementAndGet();
        ListDataListener listener = new ListDataListener() {
            public void contentsChanged(ListDataEvent event) { revisions.incrementAndGet(); }
            public void intervalAdded(ListDataEvent event) { revisions.incrementAndGet(); }
            public void intervalRemoved(ListDataEvent event) { revisions.incrementAndGet(); }
        };
        edt(() -> {
            results.getModel().addListDataListener(listener);
            results.addPropertyChangeListener("model",modelListener);
            return null;
        });
        List<Object> reports = new ArrayList<>();
        int index = 0;
        for (String line : Files.readAllLines(plan)) {
            if (line.isEmpty()) continue;
            String[] fields = line.split("\t",-1);
            Set<String> expected = new TreeSet<>();
            if (!fields[2].isEmpty()) Collections.addAll(expected,fields[2].split(","));
            edt(() -> { editor.setText(fields[1]); return null; });
            long deadline = System.currentTimeMillis()+15000;
            while (!edt(() -> execute.isEnabled() && (Boolean)invoke(editor,"isWellFormed"))) {
                if (System.currentTimeMillis()>deadline) throw new IllegalStateException("DL Query editor did not accept " + fields[0]);
                Thread.sleep(100);
            }
            long before = revisions.get();
            edt(() -> { execute.doClick(); return null; });
            // Execute restarts the plugin's public-control-driven 400 ms Swing timer.
            Thread.sleep(650);
            while (revisions.get() <= before) {
                if (System.currentTimeMillis()>deadline) throw new IllegalStateException("DL Query results did not refresh for " + fields[0]);
                Thread.sleep(100);
            }
            Set<String> actual = edt(() -> {
                Set<String> names = new TreeSet<>();
                for (int i = 0; i < results.getModel().getSize(); i++) {
                    Object item = results.getModel().getElementAt(i);
                    if (!item.getClass().getName().equals("org.coode.dlquery.DLQueryResultsSectionItem")) continue;
                    Object object = invoke(item,"getOWLObject");
                    String value = invoke(object,"getIRI").toString();
                    names.add(value.startsWith(NS) ? value.substring(NS.length()) : value);
                }
                return names;
            });
            Map<String,Object> row = new LinkedHashMap<>();
            row.put("label",fields[0]); row.put("manchester",fields[1]);
            row.put("expected",expected); row.put("actual",actual);
            row.put("result_model_revision_before_execute",before); row.put("result_model_revision_after_execute",revisions.get());
            row.put("route","Actual DL Query Swing tab: ExpressionEditor.setText; Execute.doClick; public JList model and DLQueryResultsSectionItem.getOWLObject");
            row.put("passed",expected.equals(actual));
            String name = String.format("%02d",++index) + "-" + fields[0].replaceAll("[^A-Za-z0-9_-]","_");
            capture(kit,directory.resolve(name));
            row.put("screenshot",out.relativize(directory.resolve(name).resolve("window.png")).toString());
            reports.add(row);
            Files.createDirectories(directory);
            Files.writeString(directory.resolve("results.json"),json(reports)+"\n");
        }
        edt(() -> {
            results.getModel().removeListDataListener(listener);
            results.removePropertyChangeListener("model",modelListener);
            return null;
        });
        return reports;
    }

    static Object classify(Object model, Map<String,Object> report) throws Exception {
        edt(() -> {
            Object preferences = invoke(owlLoader.loadClass("org.protege.editor.owl.ui.renderer.OWLRendererPreferences"),"getInstance");
            Object renderer = invoke(preferences,"getRendererPluginByClassName","org.protege.editor.owl.ui.renderer.OWLEntityRendererImpl");
            if (renderer == null) throw new IllegalStateException("Installed local-name renderer plugin missing");
            invoke(preferences,"setRendererPlugin",renderer);
            invoke(model,"refreshRenderer");
            report.put("entity_renderer",invoke(renderer,"getRendererClassName"));
            report.put("renderer_note","Render by entity IRI local name, in isolated application profile; allows the fixed Manchester queries to use local names.");
            return null;
        });
        Object manager = invoke(model,"getOWLReasonerManager");
        List<Object> installed = new ArrayList<>();
        String selected = null;
        for (Object info : (Set<?>)invoke(manager,"getInstalledReasonerFactories")) {
            String name = invoke(info,"getReasonerName").toString();
            String id = invoke(info,"getReasonerId").toString();
            installed.add(Map.of("name",name,"id",id));
            if (name.toLowerCase().contains("hermit")) selected = id;
        }
        report.put("installed_reasoners",installed);
        if (selected == null) throw new IllegalStateException("No installed HermiT factory");
        Class<?> handler = owlLoader.loadClass("org.protege.editor.owl.model.inference.OWLReasonerExceptionHandler");
        List<String> exceptions = Collections.synchronizedList(new ArrayList<>());
        Object proxy = Proxy.newProxyInstance(owlLoader,new Class<?>[]{handler},(p,m,args) -> {
            if (m.getName().equals("handle")) exceptions.add(String.valueOf(args[0]));
            return null;
        });
        invoke(manager,"setReasonerExceptionHandler",proxy);
        String id = selected;
        edt(() -> { invoke(manager,"setCurrentReasonerFactoryId",id); return null; });
        report.put("selected_reasoner_id",invoke(manager,"getCurrentReasonerFactoryId"));
        report.put("manager_name_before_initialization",invoke(manager,"getCurrentReasonerName"));
        Class<?> inferenceType = owlLoader.loadClass("org.semanticweb.owlapi.reasoner.InferenceType");
        Object hierarchy = inferenceType.getField("CLASS_HIERARCHY").get(null);
        Object assertions = inferenceType.getField("CLASS_ASSERTIONS").get(null);
        boolean started = edt(() -> (Boolean)invoke(manager,"classifyAsynchronously",Set.of(hierarchy,assertions)));
        report.put("classification_started",started);
        long deadline = System.currentTimeMillis() + 180000;
        String status;
        do {
            Thread.sleep(300);
            status = invoke(manager,"getReasonerStatus").toString();
            if (!(Boolean)invoke(manager,"isClassificationInProgress") &&
                    (status.equals("INITIALIZED") || status.equals("INCONSISTENT"))) break;
            if (System.currentTimeMillis() > deadline) throw new IllegalStateException("Classification timeout; " + status + "; " + exceptions);
        } while (true);
        report.put("reasoner_status",status);
        report.put("selected_reasoner_name",invoke(manager,"getCurrentReasonerName"));
        report.put("classification_in_progress",invoke(manager,"isClassificationInProgress"));
        report.put("is_classified",invoke(manager,"isClassified"));
        report.put("reasoner_exceptions",exceptions);
        Object reasoner = invoke(manager,"getCurrentReasoner");
        report.put("actual_reasoner_class",reasoner.getClass().getName());
        report.put("actual_reasoner_name",invoke(reasoner,"getReasonerName"));
        report.put("actual_reasoner_version",invoke(reasoner,"getReasonerVersion").toString());
        report.put("consistent",invoke(reasoner,"isConsistent"));
        return reasoner;
    }

    static List<Object> queries(Object model, Object reasoner, Path plan) throws Exception {
        Object checker = invoke(invoke(model,"getOWLExpressionCheckerFactory"),"getOWLClassExpressionChecker");
        List<Object> results = new ArrayList<>();
        for (String line : Files.readAllLines(plan)) {
            if (line.isEmpty()) continue;
            String[] fields = line.split("\t",-1);
            Set<String> expected = new TreeSet<>();
            if (!fields[2].isEmpty()) Collections.addAll(expected,fields[2].split(","));
            Set<String> actual = new TreeSet<>();
            String error = null;
            try {
                Object expression = edt(() -> invoke(checker,"createObject",fields[1]));
                Object nodes = invoke(reasoner,"getInstances",expression,false);
                for (Object individual : (Set<?>)invoke(nodes,"getFlattened")) {
                    String iri = invoke(individual,"getIRI").toString();
                    actual.add(iri.startsWith(NS) ? iri.substring(NS.length()) : iri);
                }
            } catch (Exception e) { error = e.toString(); }
            Map<String,Object> row = new LinkedHashMap<>();
            row.put("label",fields[0]); row.put("manchester",fields[1]);
            row.put("expected",expected); row.put("actual",actual); row.put("error",error);
            row.put("passed",error == null && expected.equals(actual));
            results.add(row);
        }
        return results;
    }

    static Object iri(String name) throws Exception {
        return invoke(owlLoader.loadClass("org.semanticweb.owlapi.model.IRI"),"create",NS+name);
    }
    static Object entity(Object df, String kind, String name) throws Exception {
        return invoke(df,"getOWL"+kind,iri(name));
    }
    static void save(Object ontology, Path path) throws Exception {
        Object format = owlLoader.loadClass("org.semanticweb.owlapi.formats.RDFXMLDocumentFormat").getConstructor().newInstance();
        Object manager = invoke(ontology,"getOWLOntologyManager");
        try (java.io.OutputStream stream = Files.newOutputStream(path)) {
            invoke(manager,"saveOntology",ontology,format,stream);
        }
    }
    static Object open(Path path) throws Exception {
        return edt(() -> invoke(pm,"createAndSetupNewEditorKit",factory,path.toUri()));
    }

    static void mutate(Object model, String id, Map<String,Object> row) throws Exception {
        Object ontology = invoke(model,"getActiveOntology");
        Object manager = invoke(model,"getOWLOntologyManager");
        Object df = invoke(model,"getOWLDataFactory");
        Object add = null;
        Set<Object> remove = new java.util.HashSet<>();
        if (id.equals("T06")) {
            add = invoke(df,"getOWLClassAssertionAxiom",entity(df,"Class","PassiveCooling"),entity(df,"NamedIndividual","Cooling_Active_2fan"));
        } else if (id.equals("T07")) {
            add = invoke(df,"getOWLObjectPropertyAssertionAxiom",entity(df,"ObjectProperty","usesGPU"),entity(df,"NamedIndividual","U01"),entity(df,"NamedIndividual","GPU_G2"));
        } else if (id.equals("T08")) {
            Object subject = entity(df,"NamedIndividual","Mem_4GiB_GDDR5");
            Object property = entity(df,"DataProperty","volumeGiB");
            for (Object ax : (Set<?>)invoke(ontology,"getDataPropertyAssertionAxioms",subject))
                if (invoke(ax,"getProperty").equals(property)) remove.add(ax);
            Object datatypeIri = invoke(owlLoader.loadClass("org.semanticweb.owlapi.model.IRI"),"create","http://www.w3.org/2001/XMLSchema#integer");
            Object datatype = invoke(df,"getOWLDatatype",datatypeIri);
            Object literal = invoke(df,"getOWLLiteral","-8",datatype);
            add = invoke(df,"getOWLDataPropertyAssertionAxiom",property,subject,literal);
            row.put("replaced_volume_assertion_count",remove.size());
        } else if (id.equals("T09")) {
            Object subject = entity(df,"NamedIndividual","U05");
            Object property = entity(df,"ObjectProperty","hasMemory");
            for (Object ax : (Set<?>)invoke(ontology,"getObjectPropertyAssertionAxioms",subject))
                if (invoke(ax,"getProperty").equals(property)) remove.add(ax);
            row.put("removed_asserted_hasMemory_count",remove.size());
            row.put("open_world_note","Consistency remains true; missing asserted value is a completeness-card problem, not a contradiction.");
        }
        final Object addition = add;
        edt(() -> {
            if (!remove.isEmpty()) invoke(manager,"removeAxioms",ontology,remove);
            if (addition != null) invoke(manager,"addAxiom",ontology,addition);
            return null;
        });
        String subjectName = id.equals("T06") ? "Cooling_Active_2fan" : id.equals("T08") ? "Mem_4GiB_GDDR5" : id.equals("T09") ? "U05" : "U01";
        Object selected = entity(df,"NamedIndividual",subjectName);
        edt(() -> { invoke(invoke(modelForKit(model),"getOWLWorkspace"),"displayOWLEntity",selected); return null; });
        row.put("selected_individual",subjectName);
    }

    static Object modelForKit(Object model) throws Exception {
        for (Object kit : (Collection<?>)invoke(invoke(pm,"getEditorKitManager"),"getEditorKits"))
            if (invoke(kit,"getOWLModelManager") == model) return kit;
        throw new IllegalStateException("No EditorKit for model");
    }

    static void run(Properties properties, Instrumentation inst) throws Exception {
        Path source = Path.of(properties.getProperty("ontology")).toRealPath();
        Path plan = Path.of(properties.getProperty("queries"));
        String sourceHash = sha(source);
        Class<?> pmClass = null;
        long deadline = System.currentTimeMillis()+180000;
        Object baseline = null;
        while (baseline == null) {
            for (Class<?> c : inst.getAllLoadedClasses()) if (c.getName().equals("org.protege.editor.core.ProtegeManager")) pmClass = c;
            if (pmClass != null) {
                pm = invoke(pmClass,"getInstance");
                for (Object kit : (Collection<?>)invoke(invoke(pm,"getEditorKitManager"),"getEditorKits")) {
                    if (!kit.getClass().getName().equals("org.protege.editor.owl.OWLEditorKit")) continue;
                    Object model = invoke(kit,"getOWLModelManager");
                    if (model == null) continue;
                    Object ontology = invoke(model,"getActiveOntology");
                    if (ontology != null && source.toUri().equals(invoke(model,"getOntologyPhysicalURI",ontology))) baseline = kit;
                }
            }
            if (baseline == null) {
                captureStartup();
                if (System.currentTimeMillis()>deadline) throw new IllegalStateException("Requested ontology not loaded in actual EditorKit");
                Thread.sleep(1000);
            }
        }
        owlLoader = baseline.getClass().getClassLoader();
        Thread.currentThread().setContextClassLoader(owlLoader);
        factory = invoke(baseline,"getEditorKitFactory");
        Object model = invoke(baseline,"getOWLModelManager");
        Object ontology = invoke(model,"getActiveOntology");
        Map<String,Object> original = new LinkedHashMap<>();
        original.put("case","source"); original.put("source",source.toString()); original.put("source_sha256",sourceHash);
        original.put("counts",counts(ontology));
        Object reasoner = classify(model,original);
        List<Object> sourceQueries = queries(model,reasoner,plan);
        original.put("queries",sourceQueries);
        Object unsatisfiable = invoke(invoke(reasoner,"getUnsatisfiableClasses"),"getEntitiesMinusBottom");
        List<String> unsatisfiableNames = new ArrayList<>();
        for (Object item : (Set<?>)unsatisfiable) unsatisfiableNames.add(item.toString());
        original.put("unsatisfiable_named_classes_excluding_bottom",unsatisfiableNames);
        original.put("passed",Boolean.TRUE.equals(original.get("consistent")) && unsatisfiableNames.isEmpty() && queryResultsPass(sourceQueries));
        original.put("query_route","actual Protégé expression checker and actual current HermiT via public APIs; DL Query UI button not invoked");
        cases.add(original);
        capture(baseline,out.resolve("source"));
        List<Object> sourceUi = uiQueries(baseline,plan,out.resolve("source-dl-query"));
        original.put("dl_query_ui",sourceUi);
        original.put("passed",Boolean.TRUE.equals(original.get("passed")) && queryResultsPass(sourceUi));
        Files.writeString(out.resolve("progress.json"),json(cases)+"\n");

        for (String id : new String[]{"T06","T07","T08","T09"}) {
            Path copy = out.resolve(id+".owl");
            save(ontology,copy);
            Object kit = open(copy);
            Object copyModel = invoke(kit,"getOWLModelManager");
            Map<String,Object> row = new LinkedHashMap<>();
            row.put("case",id); row.put("generated_from_source_sha256",sourceHash);
            mutate(copyModel,id,row);
            Object copyOntology = invoke(copyModel,"getActiveOntology");
            save(copyOntology,copy);
            invoke(copyModel,"setClean",copyOntology);
            row.put("copy_sha256",sha(copy)); row.put("counts",counts(copyOntology));
            classify(copyModel,row);
            row.put("expected_consistent",id.equals("T09"));
            row.put("passed",Boolean.valueOf(id.equals("T09")).equals(row.get("consistent")));
            cases.add(row);
            edt(() -> { selectTab((Component)invoke(kit,"getWorkspace"),"Active ontology"); return null; });
            capture(kit,out.resolve(id).resolve("metrics"));
            Object copyDf = invoke(copyModel,"getOWLDataFactory");
            Object selectedIndividual = entity(copyDf,"NamedIndividual",row.get("selected_individual").toString());
            edt(() -> {
                Object workspace = invoke(kit,"getOWLWorkspace");
                invoke(workspace,"displayOWLEntity",selectedIndividual);
                invoke(invoke(workspace,"getOWLSelectionModel"),"setSelectedEntity",selectedIndividual);
                return null;
            });
            Thread.sleep(400);
            List<String> asserted = new ArrayList<>();
            for (Object axiom : (Set<?>)invoke(copyOntology,"getObjectPropertyAssertionAxioms",selectedIndividual)) asserted.add(axiom.toString());
            for (Object axiom : (Set<?>)invoke(copyOntology,"getDataPropertyAssertionAxioms",selectedIndividual)) asserted.add(axiom.toString());
            for (Object axiom : (Set<?>)invoke(copyOntology,"getClassAssertionAxioms",selectedIndividual)) asserted.add(axiom.toString());
            row.put("selected_individual_asserted_axioms",asserted);
            capture(kit,out.resolve(id));
            Files.writeString(out.resolve("progress.json"),json(cases)+"\n");
        }

        Path roundtrip = out.resolve("T10_resaved.owl");
        save(ontology,roundtrip);
        Object reloadedKit = open(roundtrip);
        Object reloadedModel = invoke(reloadedKit,"getOWLModelManager");
        Object reloaded = invoke(reloadedModel,"getActiveOntology");
        Map<String,Object> row = new LinkedHashMap<>();
        row.put("case","T10"); row.put("saved_via","actual source EditorKit ontology manager RDF/XML writer; loaded in fresh real EditorKit");
        row.put("axiom_sets_equal",invoke(ontology,"getAxioms").equals(invoke(reloaded,"getAxioms")));
        row.put("ontology_ids_equal",invoke(ontology,"getOntologyID").equals(invoke(reloaded,"getOntologyID")));
        row.put("ontology_annotations_equal",invoke(ontology,"getAnnotations").equals(invoke(reloaded,"getAnnotations")));
        row.put("counts_before",counts(ontology)); row.put("counts_after",counts(reloaded));
        row.put("resaved_sha256",sha(roundtrip));
        Object reloadedReasoner = classify(reloadedModel,row);
        List<Object> reloadedQueries = queries(reloadedModel,reloadedReasoner,plan);
        row.put("queries",reloadedQueries);
        row.put("passed",Boolean.TRUE.equals(row.get("axiom_sets_equal")) && Boolean.TRUE.equals(row.get("ontology_ids_equal"))
                && Boolean.TRUE.equals(row.get("ontology_annotations_equal")) && Boolean.TRUE.equals(row.get("consistent"))
                && queryResultsPass(reloadedQueries));
        cases.add(row);
        capture(reloadedKit,out.resolve("T10"));
        List<Object> reloadedUi = uiQueries(reloadedKit,plan,out.resolve("T10-dl-query"));
        row.put("dl_query_ui",reloadedUi);
        row.put("passed",Boolean.TRUE.equals(row.get("passed")) && queryResultsPass(reloadedUi));
        Map<String,Object> evidence = new LinkedHashMap<>();
        evidence.put("pid",ProcessHandle.current().pid());
        evidence.put("java",System.getProperty("java.version"));
        evidence.put("collector","premain launch-only public API reflection; actual installed GUI model; own Swing frames only");
        evidence.put("source_sha256_before",sourceHash); evidence.put("source_sha256_after",sha(source));
        evidence.put("source_unchanged",sourceHash.equals(sha(source)));
        evidence.put("cases",cases);
        evidence.put("all_collector_checks_passed",cases.stream().allMatch(item -> Boolean.TRUE.equals(item.get("passed")))
                && sourceHash.equals(sha(source)));
        Files.writeString(out.resolve("evidence.json"),json(evidence)+"\n");
        Files.writeString(out.resolve("complete.txt"),"Collector completed. Inspect individual passed fields and exact query sets before acceptance. This file alone is not acceptance.\n");
    }

    public static void premain(String config, Instrumentation inst) {
        new Thread(() -> {
            try {
                Properties properties = new Properties();
                try (java.io.Reader reader = Files.newBufferedReader(Path.of(config))) { properties.load(reader); }
                out = Path.of(properties.getProperty("output"));
                Files.createDirectories(out);
                Files.writeString(out.resolve("pid.txt"),ProcessHandle.current().pid()+"\n");
                Thread stop = new Thread(() -> {
                    try {
                        while (!Files.exists(out.resolve("stop-request.txt"))) Thread.sleep(1000);
                        System.exit(0);
                    } catch (InterruptedException ignored) { }
                },"lab4-own-process-stop-signal");
                stop.setDaemon(true); stop.start();
                run(properties,inst);
            } catch (Throwable failure) {
                try {
                    StringWriter text = new StringWriter(); failure.printStackTrace(new PrintWriter(text));
                    Files.writeString(out.resolve("error.txt"),text.toString());
                } catch (Exception ignored) { failure.printStackTrace(); }
            }
        },"lab4-protege-acceptance").start();
    }
}
