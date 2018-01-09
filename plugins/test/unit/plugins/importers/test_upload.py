"""
This module is here to import the upload module so that it shows 0 coverage. The tests for this
module will be written much later after some other work is completed.
"""
import hashlib
import json
import mock
import os
import shutil
import tarfile
import tempfile
import unittest
from pulp.server.exceptions import PulpCodedValidationException
from pulp_docker.common import constants
from pulp_docker.plugins import models
from pulp_docker.plugins.importers import upload


@mock.patch("pulp_docker.plugins.models.Blob.save_and_import_content")
@mock.patch("pulp_docker.plugins.models.Manifest.save_and_import_content")
@mock.patch("pulp_docker.plugins.importers.upload.repository")
class UploadTest(unittest.TestCase):
    def setUp(self):
        super(UploadTest, self).setUp()
        self.work_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.work_dir, ignore_errors=True)

    def test_AddUnits(self, _repo_controller, _Manifest_save, _Blob_save):
        # This is where we will untar the image
        step_work_dir = os.path.join(self.work_dir, "working_dir")
        os.makedirs(step_work_dir)

        img, layers = self._create_image()
        manifest_data = dict(layers=[dict(digest=x['digest'],
                                          mediaType="ignored")
                                     for x in layers],
                             config=dict(digest="abc"),
                             schemaVersion=2)
        units = [
            models.Manifest.from_json(json.dumps(manifest_data), digest="012"),
        ]
        units.extend(models.Blob(digest="sha256:%s" % x['digest'])
                     for x in layers)

        parent = mock.MagicMock(file_path=img, parent=None, uploaded_unit=None)
        parent.v2_step_get_local_units.units_to_download = units
        step = upload.AddUnits(step_type=constants.UPLOAD_STEP_SAVE,
                               working_dir=step_work_dir)
        step.parent = parent
        step.process_lifecycle()

        dst_blobs = []

        # Make sure the blobs were created, and not compressed
        for i, layer in enumerate(layers):
            dst = os.path.join(step_work_dir, "sha256:%s" % layer['digest'])
            self.assertEquals(layer['content'], open(dst).read())
            dst_blobs.append(dst)

        # Make sure we called save_and_import_content
        self.assertEquals(
            [mock.call(x) for x in dst_blobs],
            _Blob_save.call_args_list)
        _Manifest_save.assert_called_once_with(
            os.path.join(step_work_dir, "012"))

        # Make sure associate_single_unit got called
        repo_obj = parent.get_repo.return_value.repo_obj
        self.assertEquals(
            [mock.call(repo_obj, x) for x in units],
            _repo_controller.associate_single_unit.call_args_list)
        self.assertEquals(
            units[0],
            parent.uploaded_unit)

    @mock.patch("pulp_docker.plugins.models.Manifest.objects")
    def test_AddUnits__mf_exists(self, _Manifest_objects, _repo_controller,
                                 _Manifest_save, _Blob_save):
        # This is where we will untar the image
        step_work_dir = os.path.join(self.work_dir, "working_dir")
        os.makedirs(step_work_dir)

        img, layers = self._create_image()
        manifest_data = dict(layers=[dict(digest=x['digest'],
                                          mediaType="ignored")
                                     for x in layers],
                             config=dict(digest="abc"),
                             schemaVersion=2)
        units = [
            models.Manifest.from_json(json.dumps(manifest_data), digest="012"),
        ]
        units.extend(models.Blob(digest="sha256:%s" % x['digest'])
                     for x in layers)

        parent = mock.MagicMock(file_path=img, uploaded_unit=None)
        parent.v2_step_get_local_units.units_to_download = []
        parent.available_units = units
        step = upload.AddUnits(step_type=constants.UPLOAD_STEP_SAVE,
                               working_dir=step_work_dir)
        step.parent = parent
        step.process_lifecycle()

        # Make sure a manifest was looked up and added in the parent's
        # uploaded_unit
        self.assertEquals(
            _Manifest_objects.get.return_value,
            parent.uploaded_unit)

    def test_AddUnits_error_bad_checksum(self, _repo_controller, _Manifest_save, _Blob_save):
        # This is where we will untar the image
        step_work_dir = os.path.join(self.work_dir, "working_dir")
        os.makedirs(step_work_dir)

        img, layers = self._create_image(with_bad_checksum=True)
        manifest_data = dict(layers=[dict(digest=x['digest'],
                                          mediaType="ignored")
                                     for x in layers],
                             config=dict(digest="abc"),
                             schemaVersion=2)
        units = [
            models.Manifest.from_json(json.dumps(manifest_data), digest="012"),
        ]
        units.extend(models.Blob(digest="sha256:%s" % x['digest'])
                     for x in layers)

        parent = mock.MagicMock()
        parent.configure_mock(file_path=img, parent=None)
        parent.v2_step_get_local_units.units_to_download = units
        step = upload.AddUnits(step_type=constants.UPLOAD_STEP_SAVE,
                               working_dir=step_work_dir)
        step.parent = parent
        with self.assertRaises(upload.PulpCodedValidationException) as ctx:
            step.process_lifecycle()
        self.assertEquals("DKR1017", ctx.exception.error_code.code)
        self.assertEquals(
            "Checksum bad-digest (sha256) does not validate",
            str(ctx.exception))

    def test_AddUnits_error_missing_layer(self, _repo_controller, _Manifest_save, _Blob_save):
        # This is where we will untar the image
        step_work_dir = os.path.join(self.work_dir, "working_dir")
        os.makedirs(step_work_dir)

        img, layers = self._create_image()
        manifest_data = dict(layers=[dict(digest=x['digest'],
                                          mediaType="ignored")
                                     for x in layers],
                             config=dict(digest="abc"),
                             schemaVersion=2)
        units = [
            models.Manifest.from_json(json.dumps(manifest_data), digest="012"),
        ]
        units.extend(models.Blob(digest="sha256:%s" % x['digest'])
                     for x in layers)
        # This layer doesn't exist
        units.append(models.Blob(digest="sha256:this-is-missing"))

        parent = mock.MagicMock()
        parent.configure_mock(file_path=img, parent=None)
        parent.v2_step_get_local_units.units_to_download = units
        step = upload.AddUnits(step_type=constants.UPLOAD_STEP_SAVE,
                               working_dir=step_work_dir)
        step.parent = parent
        with self.assertRaises(upload.PulpCodedValidationException) as ctx:
            step.process_lifecycle()
        self.assertEquals("DKR1018", ctx.exception.error_code.code)
        self.assertEquals(
            "Layer this-is-missing.tar is not present in the image",
            str(ctx.exception))

    @mock.patch("pulp_docker.plugins.importers.upload.models.Manifest.objects")
    @mock.patch("pulp_docker.plugins.importers.upload.models.Tag.objects")
    def test_AddTags(self, _Tag_objects, _Manifest_objects, _repos,
                     _Manifest_save, _Blob_save):
        _Manifest_objects.filter.return_value.count.return_value = 1
        _Manifest_objects.filter.return_value.__getitem__.return_value.schema_version = 42

        step_work_dir = os.path.join(self.work_dir, "working_dir")

        parent = mock.MagicMock(
            metadata=dict(name="a",
                          manifest_digest="sha256:123"),
            parent=None)
        step = upload.AddTags(step_type=constants.UPLOAD_STEP_SAVE,
                              working_dir=step_work_dir)
        step.parent = parent
        step.process_main()

        _Tag_objects.tag_manifest.assert_called_once_with(
            tag_name="a", repo_id=parent.repo.id, manifest_type="image",
            schema_version=42, manifest_digest='sha256:123',
            pulp_user_metadata=None)

    def test_AddTags__error_no_name(self, _repo_controller, _Manifest_save, _Blob_save):
        # This is where we will untar the image
        step_work_dir = os.path.join(self.work_dir, "working_dir")
        os.makedirs(step_work_dir)

        parent = mock.MagicMock(metadata=dict(), parent=None)
        step = upload.AddTags(step_type=constants.UPLOAD_STEP_SAVE,
                              working_dir=step_work_dir)
        step.parent = parent
        with self.assertRaises(PulpCodedValidationException) as ctx:
            step.process_main()
        self.assertEquals(
            "Tag does not contain required field: name.",
            str(ctx.exception))

    def test_AddTags__error_no_manifest_digest(self, _repo_controller, _Manifest_save, _Blob_save):
        # This is where we will untar the image
        step_work_dir = os.path.join(self.work_dir, "working_dir")
        os.makedirs(step_work_dir)

        parent = mock.MagicMock(metadata=dict(name="aaa"), parent=None)
        step = upload.AddTags(step_type=constants.UPLOAD_STEP_SAVE,
                              working_dir=step_work_dir)
        step.parent = parent
        with self.assertRaises(PulpCodedValidationException) as ctx:
            step.process_main()
        self.assertEquals(
            "Tag does not contain required field: manifest_digest.",
            str(ctx.exception))

    def _create_layer(self, content):
        sha = hashlib.sha256()
        sha.update(content)
        fobj = tempfile.NamedTemporaryFile(dir=self.work_dir)
        fobj.write(content)
        fobj.seek(0)
        return fobj, sha.hexdigest()

    def _create_image(self, with_bad_checksum=False):
        fname = os.path.join(self.work_dir, "image.tar")
        tobj = tarfile.TarFile(fname, mode="w")
        layers = []
        for i in range(3):
            content = "Content for layer %d" % i
            fobj, digest = self._create_layer(content=content)
            if with_bad_checksum and i == 1:
                digest = "bad-digest"
            tinfo = tobj.gettarinfo(arcname="%s.tar" % digest, fileobj=fobj)
            tinfo.uid = tinfo.gid = 0
            tinfo.uname = tinfo.gname = "root"
            tobj.addfile(tinfo, fileobj=fobj)
            layers.append(dict(digest=digest, content=content))
        tobj.close()
        return fname, layers
