package armyant.lucene;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

import org.apache.commons.collections4.ListUtils;
import org.apache.lucene.analysis.TokenStream;
import org.apache.lucene.analysis.tokenattributes.CharTermAttribute;
import org.apache.lucene.document.Document;
import org.apache.lucene.document.StoredField;
import org.apache.lucene.index.DirectoryReader;
import org.apache.lucene.index.IndexReader;
import org.apache.lucene.index.IndexableField;
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
import org.apache.lucene.search.similarities.LMDirichletSimilarity;
import org.apache.lucene.search.similarities.LMJelinekMercerSimilarity;
import org.apache.lucene.util.Bits;
import org.apache.lucene.util.BytesRef;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class LuceneLearningToRankHelper extends LuceneEngine {
    private static final Logger logger = LoggerFactory.getLogger(LuceneLearningToRankHelper.class);
    private static final Set<String> NON_FEATURE_FIELDS = new HashSet<>(Arrays.asList("doc_id", "title", "text"));

    public LuceneLearningToRankHelper(String path) throws Exception {
        super(path);
    }

    public Map<String, Map<String, Float>> computeQueryDocumentFeaturesBatch(
            IndexReader reader, IndexSearcher searcher, String query, List<String> queryTerms, List<String> batch)
            throws IOException, ParseException {

        Map<String, Map<String, Float>> docQueryFeatures = new HashMap<>();
        Query baseQuery;
        int maxResults;

        if (batch == null || batch.isEmpty()) {
            logger.warn("Considering all documents");
            baseQuery = new QueryParser("text", this.analyzer).parse("*");
            maxResults = reader.numDocs();
        } else {
            BooleanQuery.Builder baseQueryBuilder = new BooleanQuery.Builder();
            for (String docID : batch) {
                baseQueryBuilder.add(new TermQuery(new Term("doc_id", docID)), BooleanClause.Occur.SHOULD);
            }
            baseQuery = baseQueryBuilder.build();
            maxResults = batch.size();

            TopDocs hits = searcher.search(baseQuery, maxResults);

            for (ScoreDoc scoreDoc : hits.scoreDocs) {
                Document doc = reader.document(scoreDoc.doc);
                String docID = doc.get("doc_id");
                if (!docQueryFeatures.containsKey(docID)) docQueryFeatures.put(docID, new LinkedHashMap<>());

                Terms terms = reader.getTermVector(scoreDoc.doc, "text");

                TermsEnum termsEnum = terms.iterator();

                float idf = 0;
                float numQueryTerms = 0;
                float numDocsWithQueryTerms = 0;
                float sumQueryTF = 0;
                float minQueryTF = Integer.MAX_VALUE;
                float maxQueryTF = Integer.MIN_VALUE;
                ArrayList<Long> queryTermFrequencies = new ArrayList<>();

                for (String queryTerm : queryTerms) {
                    if (termsEnum.seekExact(new BytesRef(queryTerm.getBytes())) && termsEnum.docFreq() > 0) {
                        numQueryTerms += 1;
                        numDocsWithQueryTerms += termsEnum.docFreq();

                        long tf = termsEnum.totalTermFreq();
                        sumQueryTF += tf;
                        if (tf < minQueryTF) minQueryTF = tf;
                        if (tf > maxQueryTF) maxQueryTF = tf;
                        queryTermFrequencies.add(tf);
                    }

                    if (numDocsWithQueryTerms > 0) idf = 1f / numDocsWithQueryTerms;
                }

                float normNumQueryTerms = (float) numQueryTerms / queryTerms.size();
                float avgQueryTF = (float) sumQueryTF / queryTerms.size();
                float varQueryTF = (float) queryTermFrequencies.stream()
                    .mapToDouble(tf -> Math.pow(tf - avgQueryTF, 2))
                    .sum() / queryTermFrequencies.size();

                docQueryFeatures.get(docID).put("num_query_terms", numQueryTerms);
                docQueryFeatures.get(docID).put("norm_num_query_terms", normNumQueryTerms);
                docQueryFeatures.get(docID).put("idf", idf);
                docQueryFeatures.get(docID).put("sum_query_tf", sumQueryTF);
                docQueryFeatures.get(docID).put("min_query_tf", minQueryTF);
                docQueryFeatures.get(docID).put("max_query_tf", maxQueryTF);
                docQueryFeatures.get(docID).put("avg_query_tf", avgQueryTF);
                docQueryFeatures.get(docID).put("var_query_tf", Float.isNaN(varQueryTF) ? 0 : varQueryTF);

                // Query-independent features (document and web)
                for (IndexableField field : doc.getFields()) {
                    if (NON_FEATURE_FIELDS.contains(field.name())) continue;
                    docQueryFeatures.get(docID).put(field.name(), field.numericValue().floatValue());
                }
            }

            QueryParser queryParser = new QueryParser("text", this.analyzer);
            Query lQuery = new BooleanQuery.Builder()
                .add(baseQuery, BooleanClause.Occur.MUST)
                .add(queryParser.parse(query), BooleanClause.Occur.SHOULD)
                .build();

            // TF-IDF
            searcher.setSimilarity(new ClassicSimilarity());
            hits = searcher.search(lQuery, maxResults);

            for (ScoreDoc scoreDoc : hits.scoreDocs) {
                Document doc = reader.document(scoreDoc.doc);
                String docID = doc.get("doc_id");
                docQueryFeatures.get(docID).put("tf_idf", scoreDoc.score);
            }

            // BM25
            searcher.setSimilarity(new BM25Similarity());
            hits = searcher.search(lQuery, maxResults);

            for (ScoreDoc scoreDoc : hits.scoreDocs) {
                Document doc = reader.document(scoreDoc.doc);
                String docID = doc.get("doc_id");
                docQueryFeatures.get(docID).put("bm25", scoreDoc.score);
            }

            // LM-JelinekMercer(lambda=0.7)
            // Lambda was set according to an intuition from Figure 1 in
            // Zhai, Chengxiang, and John Lafferty. "A study of smoothing methods for language models
            // applied to ad hoc information retrieval." ACM SIGIR Forum. Vol. 51. No. 2. ACM, 2017.
            // http://www.iro.umontreal.ca/~nie/IFT6255/zhai-lafferty.pdf
            searcher.setSimilarity(new LMJelinekMercerSimilarity(0.7f));
            hits = searcher.search(lQuery, maxResults);

            for (ScoreDoc scoreDoc : hits.scoreDocs) {
                Document doc = reader.document(scoreDoc.doc);
                String docID = doc.get("doc_id");
                docQueryFeatures.get(docID).put("lm_jelinek_mercer", scoreDoc.score);
            }

            // LM-Dirichlet
            searcher.setSimilarity(new LMDirichletSimilarity());
            hits = searcher.search(lQuery, maxResults);

            for (ScoreDoc scoreDoc : hits.scoreDocs) {
                Document doc = reader.document(scoreDoc.doc);
                String docID = doc.get("doc_id");
                docQueryFeatures.get(docID).put("lm_dirichlet", scoreDoc.score);
            }

            /*for (Map.Entry<String, Map<String,Float>> entry : docQueryFeatures.entrySet()) {
                System.out.println("docID: " + entry.getKey());
                for (Map.Entry<String, Float> featuresEntry : entry.getValue().entrySet()) {
                    System.out.println(featuresEntry.getKey() + ": " + featuresEntry.getValue());
                }
                System.out.println();
            }*/
        }

        return docQueryFeatures;
    }

    public Map<String, Map<String, Float>> computeQueryDocumentFeatures(String query)
            throws IOException, ParseException {
        return computeQueryDocumentFeatures(query, null);
    }

    /**
     * Iterate over the filtered documents and compute query-dependent features.
     *
     * @throws ParseException
     */
    public Map<String, Map<String, Float>> computeQueryDocumentFeatures(String query, List<String> filterByDocID)
            throws IOException, ParseException {

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

        if (filterByDocID == null) {
            computeQueryDocumentFeaturesBatch(reader, searcher, query, queryTerms, null);
        } else {
            List<List<String>> batches = ListUtils.partition(filterByDocID, 1000);
            logger.info("Split into {} batches of 1000 documents", batches.size());

            // Notice that batches cannot overlap (i.e., a docID must only be listed once).
            for (List<String> batch : batches) {
                docQueryFeatures.putAll(computeQueryDocumentFeaturesBatch(reader, searcher, query, queryTerms, batch));
            }
        }

        reader.close();

        return docQueryFeatures;
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

            doc.removeFields("stream_length");
            doc.removeFields("sum_norm_tf");
            doc.removeFields("min_norm_tf");
            doc.removeFields("max_norm_tf");
            doc.removeFields("avg_norm_tf");
            doc.removeFields("var_norm_tf");

            doc.add(new StoredField("stream_length", streamLength));
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

    /**
     * Updates/creates fields, but only for existing documents.
     *
     * @param docFeatures
     * @throws Exception
     */
    public void updateDocumentFeatures(Map<String, Map<String, Double>> docFeatures) throws Exception {
        IndexReader reader = DirectoryReader.open(directory);
        IndexSearcher searcher = new IndexSearcher(reader);
        open();

        List<List<String>> batches = ListUtils.partition(new ArrayList<String>(docFeatures.keySet()), 1000);
        logger.info("Split into {} batches of 1000 documents", batches.size());

        for (List<String> batch : batches) {
            BooleanQuery.Builder queryBuilder = new BooleanQuery.Builder();
            for (String docID : batch) {
                queryBuilder.add(new TermQuery(new Term("doc_id", docID)), BooleanClause.Occur.SHOULD);
            }
            Query query = queryBuilder.build();

            TopDocs hits = searcher.search(query, batch.size());
            for (ScoreDoc scoreDoc : hits.scoreDocs) {
                Document doc = reader.document(scoreDoc.doc);
                String docID = doc.get("doc_id");

                if (!docFeatures.containsKey(docID)) {
                    logger.warn("Document {} not found in index, ignoring", docID);
                    continue;
                }

                for (Map.Entry<String, Double> entry : docFeatures.get(docID).entrySet()) {
                    String featureName = entry.getKey();
                    doc.removeFields(featureName);
                    doc.add(new StoredField(featureName, entry.getValue()));
                }

                writer.updateDocument(new Term("doc_id", docID), doc);
            }
        }

        close();
        reader.close();
    }
}