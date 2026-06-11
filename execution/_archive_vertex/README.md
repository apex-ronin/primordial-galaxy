# Archived Vertex AI scripts (retired 2026-06-10)

These scripts targeted the Vertex AI / Discovery Engine datastore in GCP project
`govtech-control`, deleted in the 2026-06-06 teardown. They import
`google-cloud-discoveryengine`, which was dropped from requirements.txt.

Kept for reference only. To rebuild cloud discovery (FedRAMP / volume trigger),
restore these and re-add the google-cloud deps.
