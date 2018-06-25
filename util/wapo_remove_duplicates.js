/**
 * José Devezas <jld@fe.up.pt>
 * FEUP InfoLab and INESC TEC
 * 2018-06-25
 */

print("===> Deleting duplicate articles");

db.articles.aggregate([
  {"$group": {"_id": "$id", "count": {"$sum": 1}, "most_recent_published_date": {"$max": "$published_date"}}},
  {"$match": {"_id": {"$ne": null}, "count": {"$gt": 1}}},
  {"$project": {"_id": 0, "id": "$_id", "most_recent_published_date": "$most_recent_published_date"}}
]).forEach(function(doc) {
  db.articles.remove({
    "id": doc.id,
    "published_date": { "$lt": doc.most_recent_published_date }
  });
});

print("===> Deleting duplicate blog posts");

db.blog_posts.aggregate([
  {"$group": {"_id": "$id", "count": {"$sum": 1}, "most_recent_published_date": {"$max": "$published_date"}}},
  {"$match": {"_id": {"$ne": null}, "count": {"$gt": 1}}},
  {"$project": {"_id": 0, "id": "$_id", "most_recent_published_date": "$most_recent_published_date"}}
]).forEach(function(doc) {
  db.blog_posts.remove({
    "id": doc.id,
    "published_date": { "$lt": doc.most_recent_published_date }
  });
});