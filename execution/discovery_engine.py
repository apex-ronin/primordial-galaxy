"""
Discovery Engine — RETIRED 2026-06-10.

Vertex AI Search (Discovery Engine) was the cloud opportunity-discovery source.
Its datastore lived in GCP project `govtech-control`, which was deleted in the
2026-06-06 teardown. There is no local equivalent (it indexed live web/PDF
opportunities, not the legal corpus or principalities), so this source is
retired rather than rewired.

`search_vertex` is kept as a no-op stub so any lingering import stays valid and
returns an empty result set. The google-cloud-discoveryengine dependency has
been dropped from requirements.txt. If cloud discovery is ever rebuilt (FedRAMP
customer / volume trigger), restore from git history at the pre-retirement commit.
"""


def search_vertex(query, num_results=10):
    """Retired cloud discovery source. Always returns an empty list.

    Kept for import-compatibility only — see module docstring.
    """
    return []
