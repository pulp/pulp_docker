import unittest

from pulp_docker.common import constants, tags


class TestGenerateUpdatedTags(unittest.TestCase):
    def test_generate_updated_tags(self):
        scratchpad = {'tags': [{constants.IMAGE_TAG_KEY: 'tag1',
                                constants.IMAGE_ID_KEY: 'image1'},
                               {constants.IMAGE_TAG_KEY: 'tag2',
                                constants.IMAGE_ID_KEY: 'image2'},
                               {constants.IMAGE_TAG_KEY: 'tag-existing',
                                constants.IMAGE_ID_KEY: 'image-existing'}]}
        new_tags = {'tag3': 'image3', 'tag-existing': 'image-new'}
        update_tags = tags.generate_updated_tags(scratchpad, new_tags)
        expected_update_tags = [{constants.IMAGE_TAG_KEY: 'tag1',
                                 constants.IMAGE_ID_KEY: 'image1'},
                                {constants.IMAGE_TAG_KEY: 'tag2',
                                 constants.IMAGE_ID_KEY: 'image2'},
                                {constants.IMAGE_TAG_KEY: 'tag-existing',
                                 constants.IMAGE_ID_KEY: 'image-new'},
                                {constants.IMAGE_TAG_KEY: 'tag3',
                                 constants.IMAGE_ID_KEY: 'image3'}]
        self.assertEqual(update_tags, expected_update_tags)

    def test_generate_updated_tags_empty_newtags(self):
        scratchpad = {'tags': [{constants.IMAGE_TAG_KEY: 'tag1',
                                constants.IMAGE_ID_KEY: 'image1'},
                               {constants.IMAGE_TAG_KEY: 'tag2',
                                constants.IMAGE_ID_KEY: 'image2'},
                               {constants.IMAGE_TAG_KEY: 'tag-existing',
                                constants.IMAGE_ID_KEY: 'image-existing'}]}
        new_tags = {}
        update_tags = tags.generate_updated_tags(scratchpad, new_tags)
        self.assertEqual(update_tags, scratchpad['tags'])
