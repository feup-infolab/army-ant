package armyant.structures;

/**
 * Created by jldevezas on 2017-10-23.
 */
public class Triple {
    private Entity subject;
    private Entity predicate;
    private Entity object;

    public Triple(Entity subject, Entity predicate, Entity object) {
        this.subject = subject;
        this.predicate = predicate;
        this.object = object;
    }

    public Entity getSubject() {
        return subject;
    }

    public void setSubject(Entity subject) {
        this.subject = subject;
    }

    public Entity getPredicate() {
        return predicate;
    }

    public void setPredicate(Entity predicate) {
        this.predicate = predicate;
    }

    public Entity getObject() {
        return object;
    }

    public void setObject(Entity object) {
        this.object = object;
    }
}
