BEGIN { FS="/" }

/.*\.xml$/ {
    doc_id=$4
    gsub(".xml", "", doc_id)
    print doc_id
}
