from aiohttp import web

from pulpcore.content import app
from pulp_docker.app.registry import Registry

registry = Registry()

app.add_routes([web.get('/v2/', Registry.serve_v2)])
app.add_routes([web.get(r'/v2/{path:.+}/blobs/sha256:{digest:.+}', registry.get_by_digest)])
app.add_routes([web.get(r'/v2/{path:.+}/manifests/sha256:{digest:.+}', registry.get_by_digest)])
app.add_routes([web.get(r'/v2/{path:.+}/manifests/{tag_name}', registry.get_tag)])
app.add_routes([web.get(r'/v2/{path:.+}/tags/list', registry.tags_list)])
