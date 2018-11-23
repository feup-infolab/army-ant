/**
 * José Devezas <jld@fe.up.pt>
 * FEUP InfoLab and INESC TEC
 * 2018-06-26
 */

let dateRangePipeline = [
  {$match: {$and: [{published_date: {$ne: null}}, {published_date: {$gt: 0}}]}},
  {$group: {_id: {}, minDate: {$min: "$published_date"}, maxDate: {$max: "$published_date"}}},
  {
    $project: {
      _id: 0,
      minDate: {
        date: {$add: [new Date("1970-01-01"), "$minDate"]}
      },
      maxDate: {
        date: {$add: [new Date("1970-01-01"), "$maxDate"]}
      }
    }
  }
];

print("===> Article dates")
printjson(db.articles.aggregate(dateRangePipeline).toArray());
print("===> Blog dates")
printjson(db.blog_posts.aggregate(dateRangePipeline).toArray());