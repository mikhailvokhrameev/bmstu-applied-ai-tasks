import java.awt.*;
import java.awt.image.BufferedImage;
import java.io.*;
import java.lang.instrument.Instrumentation;
import java.lang.reflect.*;
import java.nio.file.*;
import java.util.*;
import javax.imageio.ImageIO;
import javax.swing.*;
import javax.swing.text.JTextComponent;

public class InspectAgent {
    static Object call(Object x, String method) throws Exception {
        return x.getClass().getMethod(method).invoke(x);
    }
    static void dump(Component c, StringBuilder s, int depth) {
        if (depth > 30) return;
        String t = c instanceof JLabel ? ((JLabel)c).getText() : c instanceof AbstractButton ? ((AbstractButton)c).getText() : c instanceof JTextComponent ? ((JTextComponent)c).getText() : "";
        if(t != null && !t.isEmpty()) s.append(c.getClass().getName()).append(" : ").append(t).append("\n");
        if(c instanceof JTabbedPane) {
            JTabbedPane tabs=(JTabbedPane)c;
            for(int i=0;i<tabs.getTabCount();i++)s.append("TAB ").append(i).append(" : ").append(tabs.getTitleAt(i)).append("\n");
        }
        if(c instanceof Container)for(Component child:((Container)c).getComponents())dump(child,s,depth+1);
    }
    public static void premain(String directory, Instrumentation inst) {
        new Thread(() -> {
            try{Thread.sleep(30000);}catch(InterruptedException e){return;}
            agentmain(directory,inst);
        },"lab4-protege-startup").start();
    }
    public static void agentmain(String directory, Instrumentation inst) {
        new Thread(() -> {
            Path out=Paths.get(directory);
            try {
                Files.createDirectories(out);
                StringBuilder text=new StringBuilder();
                Class<?> manager=null;
                for(Class<?> c:inst.getAllLoadedClasses())if(c.getName().equals("org.protege.editor.core.ProtegeManager"))manager=c;
                if(manager==null)throw new IllegalStateException("No real ProtegeManager loaded");
                Object pm=manager.getMethod("getInstance").invoke(null);
                Object km=call(pm,"getEditorKitManager");
                for(Object kit:(Collection<?>)call(km,"getEditorKits")) {
                    text.append("EDITOR ").append(kit.getClass().getName()).append("\n");
                    Object model=call(kit,"getOWLModelManager");
                    Object ontology=call(model,"getActiveOntology");
                    text.append("ONTOLOGY ").append(call(ontology,"getOntologyID")).append("\n");
                    for(String method:new String[]{"getAxiomCount","getLogicalAxiomCount","getClassesInSignature","getObjectPropertiesInSignature","getDataPropertiesInSignature","getIndividualsInSignature"}) {
                        Object value=call(ontology,method);
                        text.append(method).append("=").append(value instanceof Collection ? ((Collection<?>)value).size() : value).append("\n");
                    }
                    Object rm=call(model,"getOWLReasonerManager");
                    text.append("REASONER_MANAGER ").append(rm.getClass().getName()).append("\n");
                    for(Method m:rm.getClass().getMethods())if(m.getDeclaringClass()!=Object.class)text.append("RM ").append(m.toString()).append("\n");
                }
                Files.writeString(out.resolve("model.txt"),text.toString());
                SwingUtilities.invokeAndWait(() -> {
                    StringBuilder ui=new StringBuilder();
                    int i=0;
                    for(Window w:Window.getWindows())if(w.isVisible()) {
                        ui.append("WINDOW ").append(w.getClass().getName()).append(" : ").append(w instanceof Frame ? ((Frame)w).getTitle() : "").append("\n");
                        dump(w,ui,0);
                        BufferedImage img=new BufferedImage(w.getWidth(),w.getHeight(),BufferedImage.TYPE_INT_RGB);
                        Graphics2D g=img.createGraphics();w.paintAll(g);g.dispose();
                        try{ImageIO.write(img,"png",out.resolve("window-"+(i++)+".png").toFile());}catch(IOException e){throw new RuntimeException(e);}
                    }
                    try{Files.writeString(out.resolve("ui.txt"),ui.toString());}catch(IOException e){throw new RuntimeException(e);}
                });
                Files.writeString(out.resolve("complete.txt"),"Actual running Protege Desktop model and Swing windows inspected. No other process or desktop captured.\n");
            }catch(Throwable e){try{StringWriter s=new StringWriter();e.printStackTrace(new PrintWriter(s));Files.writeString(out.resolve("error.txt"),s.toString());}catch(IOException ignored){}}
        },"lab4-protege-inspection").start();
    }
}
