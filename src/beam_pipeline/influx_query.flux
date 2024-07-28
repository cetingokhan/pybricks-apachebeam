from(bucket: "pybricks")
    |>range(start: -5m)
    |>filter(fn:(r) => r._measurement == "pybricks")
    |>sort(columns: ["_time"], desc: false)