Tags
====

Tags on images are managed via the repository object.  In the ``tags`` sub object of the
``scratchpad`` object, a list of key value pairs for each tag & Image ID are stored as
shown below.

Example Repository Object::

 {
 ...
  "scratchpad": {
    ...
    "tags": [
        { "tag": "latest",
          "image_id": "48e5f45168b97799ad0aafb7e2fef9fac57b5f16f6db7f67ba2000eb947637eb"}
    ]
 }


