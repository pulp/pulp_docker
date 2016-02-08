Tags
====

v2
--

Manifest Tags are stored as Pulp Units. Each Tag has a name, a manifest_digest
(the digest of the Manifest that the Tag references), and a repo_id. A Tag's
name and repo_id must be unique together so that in any given repository a Tag
name only references a single Manifest. Here is an example tag from MongoDB::

    {
        "_id" : "4e50e89a-fbd9-454e-8f05-22a439698264",
        "pulp_user_metadata" : {

        },
        "_last_updated" : 1455043172,
        "name" : "1-glibc",
        "manifest_digest" : "sha256:d5ad6f092d781a71630261dc7ee6503bafb8c39e2c918e13c9e0765e10758a9b",
        "repo_id" : "synctest",
        "_ns" : "units_docker_tag",
        "_content_type_id" : "docker_tag"
    }


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


