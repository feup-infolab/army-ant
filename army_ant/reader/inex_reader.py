import glob
import itertools
import logging
import os
import re
import shelve
import shutil
import tarfile
import tempfile
import time

from lxml import etree

from army_ant.util import get_first, inex
from army_ant.util.dbpedia import fetch_dbpedia_triples
from army_ant.reader import Reader, Document, Entity

logger = logging.getLogger(__name__)


class INEXReader(Reader):
    def __init__(self, source_path, include_dbpedia=False, limit=None, title_index=None):
        super(INEXReader, self).__init__(source_path)
        self.include_dbpedia = include_dbpedia
        self.limit = limit

        self.counter = 0
        self.parser = etree.XMLParser(remove_blank_text=True, resolve_entities=False)
        self.doc_xpath = '//bdy/descendant-or-self::*[not(ancestor-or-self::template) and not(self::caption)]'
        self.tar = tarfile.open(source_path, 'r|bz2')

        self.href_to_page_id_re = re.compile(r".*/(\d+)\.xml.*")

        if title_index:
            if type(title_index) is str:
                logger.info("Using provided title index %s for %s" % (title_index, source_path))
                self.title_index = shelve.open(title_index, 'r')
            else:
                logger.info("Using provided title index dictionary for %s" % source_path)
                self.title_index = title_index
        else:
            with tarfile.open(source_path, 'r|bz2') as tar:
                logger.info("Indexing titles in %s by doc_id" % source_path)
                self.title_index = {}
                for member in tar:
                    if not member.name.endswith('.xml'):
                        continue
                    try:
                        article = etree.parse(tar.extractfile(member), self.parser)
                        page_id = inex.xlink_to_page_id(get_first(article.xpath('//header/id/text()')))
                        title = get_first(article.xpath('//header/title/text()'))
                        self.title_index[page_id] = title
                    except etree.XMLSyntaxError:
                        logger.warning("Error parsing XML, skipping title indexing for %s" % member.name)

    def to_plain_text(self, bdy):
        return re.sub(r'\s+', ' ', ''.join(bdy.xpath('%s/text()' % self.doc_xpath)))

    def to_wikipedia_entity(self, page_id, label):
        # return Entity(label, "https://en.wikipedia.org/wiki/%s" % label.replace(' ', '_'))
        # return Entity(label, "https://en.wikipedia.org/?curid=%s" % page_id)

        # This is the required option for the evaluation module to work
        return Entity(label, "WP%s" % page_id)

    def build_triples(self, page_id, title, bdy):
        links = set([])
        entities = set([])
        triples = set([])

        for link in bdy.xpath('//link'):
            href = get_first(link.xpath('@xlink:href', namespaces={'xlink': 'http://www.w3.org/1999/xlink'}))
            if href is None:
                continue

            link_match = self.href_to_page_id_re.match(href)
            if link_match:
                links.add(link_match.group(1))

            related_id = inex.xlink_to_page_id(href)

            link_text = get_first(link.xpath('text()'))
            if link_text and len(link_text) < 3:
                link_text = None

            related_title = self.title_index.get(related_id, link_text)
            if related_title is None:
                continue
            related_title = related_title.replace('\n', ' ').strip()

            subj = self.to_wikipedia_entity(page_id, title)
            pred = Entity('related_to')
            obj = self.to_wikipedia_entity(related_id, related_title)

            entities.add(subj)
            entities.add(obj)
            triples.add((subj, pred, obj))

        if self.include_dbpedia:
            logger.debug("Fetching DBpedia triples for %d entities in document %s" % (len(entities), page_id))

            max_retries = 10

            retries_left = max_retries
            retry_wait = 0

            while True:
                try:
                    dbpedia_triples = list(fetch_dbpedia_triples([entity.label for entity in entities]))
                    break
                except Exception:
                    if retries_left > 0:
                        retry_wait += 10 * (max_retries - retries_left + 1)
                        logger.exception(
                            "Error retrieving triples for %d entities in document %s, retrying in %d seconds"
                            " (%d retries left)" % (len(entities), page_id, retry_wait, retries_left))
                        retries_left -= 1
                        time.sleep(retry_wait)
                    else:
                        logger.exception(
                            "Could not retrieve triples for %d entities in document %s, giving up (returning "
                            "%d cached triples)" % (len(entities), page_id, len(triples)))
                        dbpedia_triples = []
                        break

            for (s, sl), (p, pl), (o, ol) in dbpedia_triples:
                triples.add((
                    Entity(sl, s),
                    Entity(pl, p),
                    Entity(ol, o)
                ))

        return list(links), list(entities), list(triples)

    def __next__(self):
        url = None

        # Note that this for is only required in case the first element cannot be parsed.
        # If that happens, it skips to the next parsable item.
        while True:
            member = self.tar.next()
            if member is None:
                break
            if not member.name.endswith('.xml'):
                continue

            # Avoids memory explosition by resetting visited files metadata
            self.tar.members = []

            logger.debug("Reading %s" % member.name)

            if self.limit is not None and self.counter >= self.limit:
                break
            self.counter += 1

            try:
                article = etree.parse(self.tar.extractfile(member), self.parser)
            except etree.XMLSyntaxError:
                logger.warning("Error parsing XML, skipping %s in %s" % (member.name, self.source_path))
                continue

            page_id = inex.xlink_to_page_id(get_first(article.xpath('//header/id/text()')))
            title = get_first(article.xpath('//header/title/text()'))
            categories = article.xpath('//header/categories/category/text()')

            bdy = get_first(article.xpath('//bdy'))
            if bdy is None:
                continue

            url = self.to_wikipedia_entity(page_id, title).uri

            links, entities, triples = self.build_triples(page_id, title, bdy)

            return Document(
                doc_id=page_id,
                title=title,
                text=self.to_plain_text(bdy),
                links=links,
                entities=entities,
                triples=triples,
                metadata={'url': url, 'name': title, 'categories': categories})

        self.tar.close()
        if type(self.title_index) is shelve.DbfilenameShelf:
            self.title_index.close()
        raise StopIteration


class INEXDirectoryReader(Reader):
    def __init__(self, source_path, include_dbpedia=False, use_memory=False, limit=None):
        super(INEXDirectoryReader, self).__init__(source_path)

        self.use_memory = use_memory
        self.limit = limit

        self.counter = 0

        file_paths = glob.glob(os.path.join(source_path, '*.tar.bz2'))

        parser = etree.XMLParser(remove_blank_text=True, resolve_entities=False)

        logger.info("Indexing titles by doc_id for all archives in %s" % source_path)

        if use_memory:
            title_index = {}
        else:
            self.tmp_dir = tempfile.mkdtemp()
            logger.info("Using temporary directory %s for %s" % (self.tmp_dir, source_path))

            title_index_path = os.path.join(self.tmp_dir, 'title_index')
            title_index = shelve.open(title_index_path)

        num_docs = 0
        for file_path in file_paths:
            with tarfile.open(file_path, 'r|bz2') as tar:
                for member in tar:
                    if not member.name.endswith('.xml'):
                        continue
                    num_docs += 1
                    try:
                        article = etree.parse(tar.extractfile(member), parser)
                        page_id = inex.xlink_to_page_id(get_first(article.xpath('//header/id/text()')))
                        title = get_first(article.xpath('//header/title/text()'))
                        title_index[page_id] = title
                    except etree.XMLSyntaxError:
                        logger.warning(
                            "Error parsing XML, skipping title indexing for %s in %s" % (member.name, source_path))

        if type(title_index) is shelve.DbfilenameShelf:
            title_index.close()

        logger.info(
            "Finished indexing titles by doc_id for %d documents in all archives in %s" % (num_docs, source_path))

        inex_iterators = [
            iter(INEXReader(
                file_path, include_dbpedia=include_dbpedia,
                title_index=title_index if use_memory else title_index_path))
            for file_path in file_paths
        ]
        self.it = itertools.chain(*inex_iterators)

    def __next__(self):
        try:
            if self.limit is not None and self.counter >= self.limit:
                raise StopIteration
            self.counter += 1
            return next(self.it)
        except StopIteration:
            if not self.use_memory:
                logger.info("Removing temporary directory %s for %s" % (self.tmp_dir, self.source_path))
                shutil.rmtree(self.tmp_dir)
            raise
