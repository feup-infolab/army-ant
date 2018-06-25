/**
 * José Devezas <jld@fe.up.pt>
 * FEUP InfoLab and INESC TEC
 * 2018-06-25
 */

print("===> Deleting duplicate articles");

db.articles.aggregate([
  {"$unwind": "$contents"},
  {"$match": {"published_date": { $ne: null }, "contents.type": {"$eq": "date"}}},
  {"$group": {"_id": "$id", "count": {"$sum": 1}, "most_recent_date": {"$max": "$contents.content"}}},
  {"$match": {"_id": {"$ne": null}, "count": {"$gt": 1}}},
  {"$project": {"_id": 0, "id": "$_id", "most_recent_date": "$most_recent_date"}}
], allowDiskUse = true).forEach(function (doc) {
  if (doc.most_recent_date === null || doc.most_recent_date === undefined) return;
  db.articles.deleteMany({
    "id": doc.id,
    "contents.content": {"$lt": doc.most_recent_date}
  });
});

// FIXME "WriteError: cannot compare to undefined"
print("===> Deleting duplicate blog posts");

db.blog_posts.aggregate([
  {"$unwind": "$contents"},
  {"$match": {"published_date": { $ne: null }, "contents.type": {"$eq": "date"}}},
  {"$group": {"_id": "$id", "count": {"$sum": 1}, "most_published_date": {"$max": "contents.content"}}},
  {"$match": {"_id": {"$ne": null}, "count": {"$gt": 1}}},
  {"$project": {"_id": 0, "id": "$_id", "most_recent_date": "$most_recent_date"}}
], allowDiskUse = true).forEach(function (doc) {
  if (doc.most_recent_date === null || doc.most_recent_date === undefined) return;
  db.blog_posts.deleteMany({
    "id": doc.id,
    "contents.content": {"$lt": doc.most_recent_date}
  });
});