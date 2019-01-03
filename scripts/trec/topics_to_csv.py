#!/usr/bin/env python
#
# topics_to_csv.py
# José Devezas <joseluisdevezas@gmail.com>
# 2019-01-03

import sys
from lxml import etree

if len(sys.argv) < 3:
    print("%s INPUT_XML OUTPUT_TXT" % sys.argv[0])
    sys.exit(1)

in_filename = sys.argv[1]
out_filename = sys.argv[2]

print("==> Reading from %s" % in_filename)
with open(in_filename, 'r') as in_file, open(out_filename, 'w') as out_file:
    xml = etree.parse(in_file)
    for topic in xml.xpath('//topic'):
        topic_id = topic.xpath('@id')[0]
        title = topic.xpath('title/text()')[0]
        out_file.write('%s\t%s\n' % (topic_id, title))
print("==> Written to %s" % out_filename)