package armyant.structures;

/**
 * Created by jldevezas on 2017-10-23.
 */
public class Triple {
    public static class Instance {
        private boolean isBlank;
        private String uri;
        private String label;

        public Instance() {
            this.uri = null;
            this.label = null;
            this.isBlank = true;
        }

        public Instance(String uri, String label) {
            this.uri = uri;
            this.label = label;
            this.isBlank = false;
        }

        public String getURI() {
            return uri;
        }

        public void setURI(String uri) {
            this.uri = uri;
        }

        public String getLabel() {
            return label;
        }

        public void setLabel(String label) {
            this.label = label;
        }

        public boolean isBlank() {
            return isBlank;
        }
    }

    private Instance subject;
    private Instance predicate;
    private Instance object;

    public Triple(Instance subject, Instance predicate, Instance object) {
        this.subject = subject;
        this.predicate = predicate;
        this.object = object;
    }

    public Instance getSubject() {
        return subject;
    }

    public void setSubject(Instance subject) {
        this.subject = subject;
    }

    public Instance getPredicate() {
        return predicate;
    }

    public void setPredicate(Instance predicate) {
        this.predicate = predicate;
    }

    public Instance getObject() {
        return object;
    }

    public void setObject(Instance object) {
        this.object = object;
    }
}
