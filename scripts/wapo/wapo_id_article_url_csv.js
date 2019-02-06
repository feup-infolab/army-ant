print("id,article_url")
db.articles.find({}, { _id: 0, id: 1, article_url: 1 }).toCSV()
db.blog_posts.find({}, { _id: 0, id: 1, article_url: 1 }).toCSV()
