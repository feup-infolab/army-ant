db.evaluation_tasks
	.find({}, {
		_id: 0,
		topics_path: 1,
		assessments_path: 1,
		valid_ids_path: 1,
		valid_categories_per_id_path: 1
	})
	.forEach(function(d) {
		for (var key in d) {
			if (d[key]) {
				print(d[key])
			}
		}
	})
