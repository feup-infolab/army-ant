/**
 * José Devezas <jld@fe.up.pt>
 * FEUP InfoLab and INESC TEC
 * 2018-06-25
 */

print("===> Deleting duplicate articles (keeping last version according to _id order)");

db.articles.aggregate([
  {"$sort": {"_id": 1}},
  {"$group": {"_id": "$id", "count": {"$sum": 1}, "keep_id": {"$last": "$_id"}}},
  {"$match": {"_id": {"$ne": null}, "count": {"$gt": 1}}},
  {"$project": {"_id": 0, "id": "$_id", "keep_id": "$keep_id"}}
], allowDiskUse = true).forEach(function (doc) {
  db.articles.deleteMany({
    "id": doc.id,
    "_id": {"$ne": doc.keep_id}
  });
});

print("===> Deleting duplicate blog posts(keeping last version according to _id order)");

db.blog_posts.aggregate([
  {"$sort": {"_id": 1}},
  {"$group": {"_id": "$id", "count": {"$sum": 1}, "keep_id": {"$last": "$_id"}}},
  {"$match": {"_id": {"$ne": null}, "count": {"$gt": 1}}},
  {"$project": {"_id": 0, "id": "$_id", "keep_id": "$keep_id"}}
], allowDiskUse = true).forEach(function (doc) {
  db.blog_posts.deleteMany({
    "id": doc.id,
    "_id": {"$ne": doc.keep_id}
  });
});