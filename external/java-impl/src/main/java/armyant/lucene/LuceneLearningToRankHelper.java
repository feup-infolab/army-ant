package armyant.lucene;

import java.util.ArrayList;
import java.util.Map;

import org.apache.lucene.document.Document;
import org.apache.lucene.document.StoredField;
import org.apache.lucene.index.DirectoryReader;
import org.apache.lucene.index.IndexReader;
import org.apache.lucene.index.MultiFields;
import org.apache.lucene.index.Term;
import org.apache.lucene.index.Terms;
import org.apache.lucene.index.TermsEnum;
import org.apache.lucene.util.Bits;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class LuceneLearningToRankHelper extends LuceneEngine {
    private static final Logger logger = LoggerFactory.getLogger(LuceneLearningToRankHelper.class);

    public LuceneLearningToRankHelper(String path) throws Exception {
        super(path);
    }

    public void computeDocumentFeatures() throws Exception {
        IndexReader reader = DirectoryReader.open(directory);

        open();

        Bits liveDocs = MultiFields.getLiveDocs(reader);
        for (int docID = 0; docID < reader.maxDoc(); docID++) {
            if (liveDocs != null && !liveDocs.get(docID)) continue;

            Terms terms = reader.getTermVector(docID, "text");
            
            ArrayList<Integer> termFrequencies = new ArrayList<>();
            TermsEnum termsEnum = terms.iterator();
            while (termsEnum.next() != null) {
                termFrequencies.add((int) termsEnum.totalTermFreq());
            }

            long streamLength = termFrequencies.stream().mapToInt(d -> d).sum();
            double sumNormTF = 0;
            double minNormTF = Double.MAX_VALUE;
            double maxNormTF = Double.MIN_VALUE;

            for (double tf : termFrequencies) {
                double normTF = tf / streamLength;
                sumNormTF += normTF;
                if (normTF < minNormTF) minNormTF = normTF;
                if (normTF > maxNormTF) maxNormTF = normTF;
            }

            double avgNormTF = sumNormTF / termFrequencies.size();
            double varNormTF = termFrequencies.stream()
                .mapToDouble(tf -> Math.pow(tf / streamLength - avgNormTF, 2))
                .sum() / termFrequencies.size();

            Document doc = reader.document(docID);

            System.out.println(doc);

            doc.add(new StoredField("len", streamLength));
            doc.add(new StoredField("sum_norm_tf", sumNormTF));
            doc.add(new StoredField("min_norm_tf", minNormTF));
            doc.add(new StoredField("max_norm_tf", maxNormTF));
            doc.add(new StoredField("avg_norm_tf", avgNormTF));
            doc.add(new StoredField("var_norm_tf", varNormTF));

            System.out.println(doc);

            writer.updateDocument(new Term("doc_id", doc.get("doc_id")), doc);
        }

        close();
    }

    public void updateDocumentFeatures(Map<String, Map<String, Double>> docFeatures) {

    }
}