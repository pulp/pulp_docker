Tags
====

v2
--

Manifest Tags are stored as Pulp Units. Each Tag has a name, a manifest_digest
(the digest of the Manifest that the Tag references), schema_version (the schema version
for the manifest the Tag references), manifest_type( image manifest or manifest list the
Tag references) and a repo_id. A Tag's name, schema_version, manifest_type and repo_id
must be unique together so that in any given repository a Tag only references
a single Manifest(image or list).
Here is an example of tag with name 'latest' within a repository::

    [
      {
        "updated": "2017-07-12T11:43:29Z", 
        "repo_id": "man-list", 
        "created": "2017-07-12T11:43:29Z", 
        "unit_id": "98a4ba20-f60e-4b9d-8aa3-9bbe23030b4c", 
        "unit_type_id": "docker_tag", 
        "_id": {
          "$oid": "59660b6152e81521aead11c3"
        }, 
        "metadata": {
          "repo_id": "man-list", 
          "manifest_digest": "sha256:69fd2d3fa813bcbb3a572f1af80fe31a1710409e15dde91af79be62b37ab4f70", 
          "manifest_type": "list", 
          "_ns": "units_docker_tag", 
          "_last_updated": 1499859809, 
          "schema_version": 2, 
          "pulp_user_metadata": {}, 
          "_content_type_id": "docker_tag", 
          "_id": "98a4ba20-f60e-4b9d-8aa3-9bbe23030b4c", 
          "name": "latest"
        }
      }, 
      {
        "updated": "2017-07-12T11:43:29Z", 
        "repo_id": "man-list", 
        "created": "2017-07-12T11:43:29Z", 
        "unit_id": "cf56285e-1acd-4834-9dbd-35721b8964e6", 
        "unit_type_id": "docker_tag", 
        "_id": {
          "$oid": "59660b6152e81521aead11c2"
        }, 
        "metadata": {
          "repo_id": "man-list", 
          "manifest_digest": "sha256:7864a5b2d5ba865d0b3183071a4fc0dcaa365a599e90d5b54903076ed4ec5155", 
          "manifest_type": "image", 
          "_ns": "units_docker_tag", 
          "_last_updated": 1499859809, 
          "schema_version": 1, 
          "pulp_user_metadata": {}, 
          "_content_type_id": "docker_tag", 
          "_id": "cf56285e-1acd-4834-9dbd-35721b8964e6", 
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


