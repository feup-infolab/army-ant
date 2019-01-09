package armyant.lucene;

import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

import org.apache.lucene.analysis.TokenStream;
import org.apache.lucene.analysis.tokenattributes.CharTermAttribute;
import org.apache.lucene.document.Document;
import org.apache.lucene.document.StoredField;
import org.apache.lucene.index.DirectoryReader;
import org.apache.lucene.index.IndexReader;
import org.apache.lucene.index.MultiFields;
import org.apache.lucene.index.Term;
import org.apache.lucene.index.Terms;
import org.apache.lucene.index.TermsEnum;
import org.apache.lucene.queryparser.classic.ParseException;
import org.apache.lucene.queryparser.classic.QueryParser;
import org.apache.lucene.search.BooleanClause;
import org.apache.lucene.search.BooleanQuery;
import org.apache.lucene.search.IndexSearcher;
import org.apache.lucene.search.Query;
import org.apache.lucene.search.ScoreDoc;
import org.apache.lucene.search.TermQuery;
import org.apache.lucene.search.TopDocs;
import org.apache.lucene.search.similarities.BM25Similarity;
import org.apache.lucene.search.similarities.ClassicSimilarity;
import org.apache.lucene.util.Bits;
import org.apache.lucene.util.BytesRef;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class LuceneLearningToRankHelper extends LuceneEngine {
    private static final Logger logger = LoggerFactory.getLogger(LuceneLearningToRankHelper.class);

    public LuceneLearningToRankHelper(String path) throws Exception {
        super(path);
    }

    /**
     * Iterate over all documents and compute query-dependent features.
     * 
     * @throws ParseException
     */
    public void computeQueryDocumentFeatures(String query, List<String> filterByDocID) throws IOException, ParseException {
        Map<String, Map<String, Float>> docQueryFeatures = new HashMap<>();

        ArrayList<String> queryTerms = new ArrayList<>();
        TokenStream stream = this.analyzer.tokenStream("text", query);
        stream.reset();
        while (stream.incrementToken()) {
            queryTerms.add(stream.getAttribute(CharTermAttribute.class).toString());
        }
        stream.close();

        IndexReader reader = DirectoryReader.open(directory);
        IndexSearcher searcher = new IndexSearcher(reader);

        BooleanQuery.Builder baseQueryBuilder = new BooleanQuery.Builder();
        for (String docID : filterByDocID) {
            baseQueryBuilder.add(new TermQuery(new Term("doc_id", docID)), BooleanClause.Occur.SHOULD);
        }
        Query baseQuery = baseQueryBuilder.build();


        TopDocs hits = searcher.search(baseQuery, filterByDocID.size());
        
        for (ScoreDoc scoreDoc : hits.scoreDocs) {            
            Document doc = reader.document(scoreDoc.doc);
            String docID = doc.get("doc_id");
            if (!docQueryFeatures.containsKey(docID)) docQueryFeatures.put(docID, new HashMap<>());

            Terms terms = reader.getTermVector(scoreDoc.doc, "text");
            
            Set<String> termsText = new HashSet<>();
            TermsEnum termsEnum = terms.iterator();

            // TODO review this
            int numQueryTerms = 0;
            for (String queryTerm : queryTerms) {
                if (termsEnum.seekExact(new BytesRef(queryTerm.getBytes())) && termsEnum.docFreq() > 0) {
                    numQueryTerms += 1;
                }
            }
            double normNumQueryTerms = (double) numQueryTerms / queryTerms.size();

            System.out.println("docID=" + docID + ", numQueryTerms=" + numQueryTerms);
            System.out.println("docID=" + docID + ", normNumQueryTerms=" + normNumQueryTerms);
        }


        QueryParser queryParser = new QueryParser("text", this.analyzer);
        Query lQuery = new BooleanQuery.Builder()
            .add(baseQuery, BooleanClause.Occur.MUST)
            .add(queryParser.parse(query), BooleanClause.Occur.MUST)
            .build();

        // TF-IDF
        searcher.setSimilarity(new ClassicSimilarity());
        hits = searcher.search(lQuery, filterByDocID.size());

        for (ScoreDoc scoreDoc : hits.scoreDocs) {
            Document doc = reader.document(scoreDoc.doc);
            String docID = doc.get("doc_id");
            docQueryFeatures.get(docID).put("tfidf", scoreDoc.score);
            System.out.println("docID=" + docID + ", TF-IDF=" + scoreDoc.score);
        }

        // BM25
        searcher.setSimilarity(new BM25Similarity());
        hits = searcher.search(lQuery, filterByDocID.size());

        for (ScoreDoc scoreDoc : hits.scoreDocs) {
            Document doc = reader.document(scoreDoc.doc);
            String docID = doc.get("doc_id");
            docQueryFeatures.get(docID).put("tfidf", scoreDoc.score);
            System.out.println("docID=" + docID + ", BM25=" + scoreDoc.score);
        }

        reader.close();
    }

    /**
     * Iterate over all documents in the index, compute document-only features
     * and store them as new fields, updating the document.
     */
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

            doc.add(new StoredField("len", streamLength));
            doc.add(new StoredField("sum_norm_tf", sumNormTF));
            doc.add(new StoredField("min_norm_tf", minNormTF));
            doc.add(new StoredField("max_norm_tf", maxNormTF));
            doc.add(new StoredField("avg_norm_tf", avgNormTF));
            doc.add(new StoredField("var_norm_tf", varNormTF));

            writer.updateDocument(new Term("doc_id", doc.get("doc_id")), doc);
        }

        close();
        reader.close();
    }

    public void updateDocumentFeatures(Map<String, Map<String, Double>> docFeatures) throws IOException {
        IndexReader reader = DirectoryReader.open(directory);

        for (Map.Entry<String, Map<String, Double>> entry : docFeatures.entrySet()) {
            String docID = entry.getKey();
            // TODO load document, update fields, update document in index.
        }
    }
}