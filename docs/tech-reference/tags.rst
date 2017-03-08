Tags
====

v2
--

Manifest Tags are stored as Pulp Units. Each Tag has a name, a manifest_digest
(the digest of the Manifest that the Tag references), schema_version (the schema version
for the manifest the Tag references) and a repo_id. A Tag's name, schema_version and repo_id
must be unique together so that in any given repository a Tag only references
a single Manifest that uses either schema version 1 or schema version 2.
Here is an example of tag with name 'latest' within a repository::

    [
      {
        "updated": "2017-02-09T15:52:46Z",
        "repo_id": "synctest",
        "created": "2017-02-09T15:52:46Z",
        "_ns": "repo_content_units",
        "unit_id": "19986269-4666-4dad-acbe-b0cce808bb21",
        "unit_type_id": "docker_tag",
        "_id": {
          "$oid": "589c904e45ef487707c641fa"
        },
        "id": "589c904e45ef487707c641fa",
        "metadata": {
          "repo_id": "synctest",
          "manifest_digest": "sha256:817a12c32a39bbe394944ba49de563e085f1d3c5266eb8e9723256bc4448680e",
          "_ns": "units_docker_tag",
          "_last_updated": 1486655449,
          "schema_version": 2,
          "pulp_user_metadata": {},
          "_content_type_id": "docker_tag",
          "_id": "19986269-4666-4dad-acbe-b0cce808bb21",
          "name": "latest"
        }
      },
      {
        "updated": "2017-02-09T16:02:54Z",
        "repo_id": "synctest",
        "created": "2017-02-09T16:02:54Z",
        "_ns": "repo_content_units",
        "unit_id": "7f92741b-5379-4f13-8b43-0d3ebd9c5c25",
        "unit_type_id": "docker_tag",
        "_id": {
          "$oid": "589c92ae45ef487707c641fd"
        },
        "id": "589c92ae45ef487707c641fd",
        "metadata": {
          "repo_id": "synctest",
          "manifest_digest": "sha256:c152ddeda2b828fbb610cb9e4cb121e1879dd5301d336f0a6c070b2844a0f56d",
          "_ns": "units_docker_tag",
          "_last_updated": 1486653137,
          "schema_version": 1,
          "pulp_user_metadata": {},
          "_content_type_id": "docker_tag",
          "_id": "7f92741b-5379-4f13-8b43-0d3ebd9c5c25",
          "name": "latest"
        }
      }
    ]


v1
--

Tags on Images are managed via the repository object.  In the ``tags`` sub object of the
``scratchpad`` object, a list of key value pairs for each tag & Image ID are stored as
shown below.

Example Repository object::

 {
 ...
  "scratchpad": {
    ...
    "tags": [
        { "tag": "latest",
          "image_id": "48e5f45168b97799ad0aafb7e2fef9fac57b5f16f6db7f67ba2000eb947637eb"}
    ]
 }


