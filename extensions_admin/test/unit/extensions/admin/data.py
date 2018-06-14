import os


busybox_tar_path = os.path.join(os.path.dirname(__file__), '../../../data/busyboxlight.tar')
skopeo_tar_path = os.path.join(os.path.dirname(__file__), '../../../data/skopeo.tar')

# these are in correct ancestry order
busybox_ids = (
    '769b9341d937a3dba9e460f664b4f183a6cecdd62b337220a28b3deb50ee0a02',
    '48e5f45168b97799ad0aafb7e2fef9fac57b5f16f6db7f67ba2000eb947637eb',
    'bf747efa0e2fa9f7c691588ce3938944c75607a7bb5e757f7369f86904d97c78',
    '511136ea3c5a64f264b78b5433614aec563103b4d4702f3ba7d4d2698e22c158',
)

repo_id = 'busybox'
manifest_digest = 'sha256:6ca13d52ca70c883e0f0bb101e425a89e8624de51db2d2392593af6a84118090'
tag_name = 'latest'
