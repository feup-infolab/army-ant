package armyant.hgoe;

/**
 * Created by jldevezas on 2017-11-21.
 */
public interface RankableAtom extends Atom {
    abstract public String getName();
    abstract public void setName(String name);
    abstract public void setID(String id);
    abstract public String getID();

    public default String getLabel() {
        return getClass().getSimpleName();
    }
}
