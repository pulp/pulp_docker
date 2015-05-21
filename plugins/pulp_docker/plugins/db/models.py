from mongoengine import (IntField, StringField)

from pulp.server.db.model import ContentUnit


class DockerImage(ContentUnit):
    image_id = StringField(required=True)
    parent_id = StringField()
    size = IntField()

    # For backward compatibility
    _ns = StringField(default='units_docker_image')
    unit_type_id = StringField(db_field='_content_type_id', required=True, default='docker_image')

    unit_key_fields = ('image_id',)

    meta = {'collection': 'units_docker_image',
            'indexes': ['-image_id', ],
            'allow_inheritance': False}
