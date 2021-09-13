[![Actions Status](https://github.com/wayfair-incubator/bigquery-buildkite-plugin/workflows/Lint/badge.svg?branch=main)](https://github.com/wayfair-incubator/bigquery-buildkite-plugin/actions)
[![Actions Status](https://github.com/wayfair-incubator/bigquery-buildkite-plugin/workflows/Unit%20Tests/badge.svg?branch=main)](https://github.com/wayfair-incubator/bigquery-buildkite-plugin/actions)
![Version](https://img.shields.io/static/v1.svg?label=Version&message=0.1.1&color=lightgrey&?link=http://left&link=https://github.com/wayfair-incubator/bigquery-buildkite-plugin/tree/v0.1.1)
![Plugin Status](https://img.shields.io/static/v1.svg?label=&message=Buildkite%20Plugin&color=blue&logo=data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAGAAAABgCAMAAADVRocKAAAAk1BMVEX///+DrRik1Cb+/vyErhin1yeAqhfJ5n+dzCO50X2VwiC2zna020vg8LSo1i+q1zTN3qL7/fav2UDT4q33++yXuj3z+eLO6IqMuByJsSPM54XX5bWcvUbH5Xrg6sWiwVHB1ovk7cymxFnq8deOtC2xzG7c6L6/1YfU7JbI2pj2+e+jzzPd763K3J3j8ryRtDbY7aOqCe3pAAACTElEQVRoge3Z11KDQBSAYUpItSRqVGwxEVOwxPd/OndhCbA5BTaLM87sueb83+yMStHz3Lhx48bN/5iw+2VjImy0fDvzQiNCLKVrdjn0nq++QwNCLMy+9uOzc2Y59AZBwF4F55NefxxxyxK4aEvI/C7x/QxglrMTBNxVej6V+QNALh+AhkRY5isAsVwBxFWfM/rnLsu/qnwNQIkawBBy/abMawBCaEAQXGFElt/Evo8CIHEEIESWH9XyAAAQACCIH40A8yBwRICARiB5BNAIBKgQ8tLbCZBHgRqBAgWB5wmgQhCAIt7ekTwJ5AQHSGKC1TkgiM7WIs8A0bBvCETR8H7CA4EhIPP9fgPA7AR53u91BBR53+8EKPPdACLvq3wXQC1vH9DytoGjvF0gGo71vE0gCoC8PQDJ2wJEvgfmbQFo3g5A5HNA3K+eL0yBePdO5AtAEAOUoIB4c+ONiHwBZHddjMCB5DUV6yOqfzgBQWCAzMu9ZoAiHgACBpJdmj3SNAdQAgKSXfFQ1gZQz28PlxxQ5tsCIKED+6/qU2tbQBF3lxgwn9YfitsDR0QVmE9D7bHeBNCIEphf63lToEYUAJQ3BxSxlUQGPD3Cr5DmwIGQJ8DypwHqlXX7gec5oMcAXv5OT31OYU6weuM/9tDv/iSwWnJxfghA5s0+QzUCFi828iiwWNvJI4C9PAg8WcwDAPVLYwGwndeAufV8DZB/bm3nK0A3+RyI81tdF3l1gn1neQlM4qnpp+9ms0xP/P8AP/8778aNGzdu/mh+AQp1NCB/JInXAAAAAElFTkSuQmCC)


# BigQuery Buildkite Plugin

This Buildkite plugin can be used to deploy tables/views schemas to BigQuery

A [Buildkite plugin](https://buildkite.com/docs/agent/v3/plugins) for deploying tables/views schemas to BigQuery.

## Using the plugin

If the version number is not provided then the most recent version of the plugin will be used. Do not use version number as `master` or any branch names.

### Simple

```yaml
steps:
  - plugins:
      - wayfair-incubator/bigquery#v0.2.0:
          gcp_project: gcp-us-project
          dataset_schema_directory: schemas/gcp-us-project/dataset
```

## Configuration

### Required

### `gcp_project` (required, string)

The full name of the GCP project you want to deploy.

Example: `gcp-us-project`

### `dataset_schema_directory` (required, string)

The directory in your repository where are you storing the schemas for your tables and views.

Example: `gcp-us-project/dataset_name`

## Secret

This plugin expects `GCP_SERVICE_ACCOUNT` is placed as environment variable. Make sure to store it [securely](https://buildkite.com/docs/pipelines/secrets)!

```yaml
env:
  gcp_service_account: '{"email": ""}'
```

## Example

### Basic

The following pipeline will deploy all the schemas to the `gcp-us-project` living under `directory/project/`

## Schemas

This plugin uses [GBQ](https://github.com/wayfair-incubator/gbq) to deploy to Google BigQuery.
[GBQ](https://github.com/wayfair-incubator/gbq) now supports specifying partitions with the schema as well.

To leverage this you need to nest your JSON table schema in a dictionary. An example for the same is given below. Library supports Time and Range based partitioning along with Clustering.

All the configuration options can be found [here](https://github.csnzoo.com/shared/buyfair-bigquery-library/blob/master/buyfair_bigquery_library/dto.py).

```json
{
  "partition": {
    "type": "range",
    "definition": {
      "field": "ID",
      "range": {
        "start": 1,
        "end": 100000,
        "interval": 10
      }
    }
  },
  "clustering": [
    "ID"
  ],
  "schema": [
    {
      "name": "ID",
      "type": "INTEGER",
      "mode": "REQUIRED"
    }
  ]
}
```

## Contributing

See the [Contributing Guide](CONTRIBUTING.md) for additional information.

To execute tests locally (requires that `docker` and `docker-compose` are installed):

```bash
docker-compose run test
```

## Credits

This plugin was originally written by [Jash Parekh](https://github.com/jashparekh) for Wayfair.
