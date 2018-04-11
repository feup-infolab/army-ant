package armyant;

import armyant.structures.Document;
import armyant.structures.ResultSet;
import com.optimaize.langdetect.LanguageDetector;
import com.optimaize.langdetect.LanguageDetectorBuilder;
import com.optimaize.langdetect.i18n.LdLocale;
import com.optimaize.langdetect.ngram.NgramExtractors;
import com.optimaize.langdetect.profiles.LanguageProfile;
import com.optimaize.langdetect.profiles.LanguageProfileReader;
import it.unimi.dsi.util.XoRoShiRo128PlusRandom;
import org.apache.commons.io.IOUtils;
import org.apache.commons.lang.ArrayUtils;
import org.apache.commons.lang3.NotImplementedException;
import org.apache.lucene.analysis.CharArraySet;
import org.apache.lucene.analysis.LowerCaseFilter;
import org.apache.lucene.analysis.StopFilter;
import org.apache.lucene.analysis.TokenStream;
import org.apache.lucene.analysis.miscellaneous.LengthFilter;
import org.apache.lucene.analysis.standard.StandardFilter;
import org.apache.lucene.analysis.standard.StandardTokenizer;
import org.apache.lucene.analysis.tokenattributes.CharTermAttribute;
import org.apache.lucene.util.AttributeFactory;
import org.joda.time.Duration;
import org.joda.time.format.PeriodFormatter;
import org.joda.time.format.PeriodFormatterBuilder;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.io.InputStream;
import java.io.StringReader;
import java.io.StringWriter;
import java.util.*;

/**
 * Created by jldevezas on 2017-11-10.
 */
public abstract class Engine {
    private static final Logger logger = LoggerFactory.getLogger(Engine.class);

    private static final int MIN_TOKEN_LENGTH = 3;
    private static final XoRoShiRo128PlusRandom RNG = new XoRoShiRo128PlusRandom();

    private LanguageDetector languageDetector;

    public Engine() {
        try {
            List<LanguageProfile> languageProfiles = new LanguageProfileReader().readAllBuiltIn();
            languageDetector = LanguageDetectorBuilder.create(NgramExtractors.standard())
                    .withProfiles(languageProfiles)
                    .build();
        } catch (IOException e) {
            logger.error(e.getMessage(), e);
        }
    }

    public static Integer sampleUniformlyAtRandom(int[] elementIDs) {
        return elementIDs[(int) (elementIDs.length * RNG.nextDoubleFast())];
    }

    public static Integer sampleNonUniformlyAtRandom(int[] elementIDs, float[] weights) {
        float weightsSum = 0;
        for (float weight : weights) {
            weightsSum += weight;
        }

        float cumulativeProbability = 0;
        TreeMap<Float, Integer> elements = new TreeMap<>();
        for (int i=0; i < weights.length; i++) {
            cumulativeProbability += weights[i] / weightsSum;
            elements.put(cumulativeProbability, elementIDs[i]);
        }

        Map.Entry<Float, Integer> randomElement = elements.higherEntry(RNG.nextFloat());
        if (randomElement == null) return sampleUniformlyAtRandom(elementIDs);
        return randomElement.getValue();
    }

    public abstract void index(Document document) throws Exception;

    public void indexCorpus(Collection<Document> corpus) {
        throw new NotImplementedException("Not implemented");
    }

    public void postProcessing() throws Exception {
    }

    public void inspect(String feature, String workdir) {
        throw new NotImplementedException("Not implemented");
    }

    public abstract ResultSet search(String query, int offset, int limit) throws Exception;

    public void close() throws Exception {
    }

    protected String formatMillis(float millis) {
        if (millis >= 1000) return formatMillis((long) millis);
        return String.format("%.2fms", millis);
    }

    protected String formatMillis(long millis) {
        Duration duration = new Duration(millis); // in milliseconds
        PeriodFormatter formatter = new PeriodFormatterBuilder()
                .appendDays()
                .appendSuffix("d")
                .appendHours()
                .appendSuffix("h")
                .appendMinutes()
                .appendSuffix("m")
                .appendSeconds()
                .appendSuffix("s")
                .appendMillis()
                .appendSuffix("ms")
                .toFormatter();
        return formatter.print(duration.toPeriod());
    }

    private CharArraySet getStopwords(String language) {
        StringWriter writer = new StringWriter();

        logger.debug("Fetching stopwords for {} language", language);

        String defaultFilename = "/stopwords/en.stopwords";
        String filename = String.format("/stopwords/%s.stopwords", language);

        try {
            InputStream inputStream = getClass().getResourceAsStream(filename);
            if (inputStream == null) {
                logger.warn("Could not load '{}' stopwords, using 'en' as default", language);
                inputStream = getClass().getResourceAsStream(defaultFilename);
            }
            IOUtils.copy(inputStream, writer, "UTF-8");
            return new CharArraySet(Arrays.asList(writer.toString().split("\n")), true);
        } catch (IOException e) {
            logger.warn("Could not load 'en' stopwords, ignoring stopwords");
            return CharArraySet.EMPTY_SET;
        }
    }

    protected List<String> analyze(String text) throws IOException {
        AttributeFactory factory = AttributeFactory.DEFAULT_ATTRIBUTE_FACTORY;

        StandardTokenizer tokenizer = new StandardTokenizer(factory);
        tokenizer.setReader(new StringReader(text));

        String language = languageDetector.detect(text).or(LdLocale.fromString("en")).getLanguage();

        TokenStream filter = new StandardFilter(tokenizer);
        filter = new LowerCaseFilter(filter);
        filter = new StopFilter(filter, getStopwords(language));
        filter = new LengthFilter(filter, MIN_TOKEN_LENGTH, Integer.MAX_VALUE);
        filter.reset();

        List<String> tokens = new ArrayList<>();
        CharTermAttribute attr = tokenizer.addAttribute(CharTermAttribute.class);
        while (filter.incrementToken()) {
            tokens.add(attr.toString());
        }

        return tokens;
    }
}