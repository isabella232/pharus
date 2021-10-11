from textwrap import indent
from pathlib import Path
import os
import yaml


def populate_api():
    header_template = """
# Auto-generated rest api
from .server import app, protected_route
from .interface import _DJConnector, dj
import json
import numpy as np


class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)
"""
    route_template = """

@app.route('{route}', methods=['GET'])
@protected_route
def {method_name}(jwt_payload: dict) -> dict:

{query}
    djconn = _DJConnector._set_datajoint_config(jwt_payload)
    vm_dict = {{s: dj.VirtualModule(s, s, connection=djconn) for s in dj.list_schemas()}}
    query, fetch_args = dj_query(vm_dict)
    return json.dumps(query.fetch(**fetch_args), cls=NumpyEncoder)


@app.route('{route}/attributes', methods=['GET'])
@protected_route
def {method_name}_attributes(jwt_payload: dict) -> dict:

{query}
    djconn = _DJConnector._set_datajoint_config(jwt_payload)
    vm_dict = {{s: dj.VirtualModule(s, s, connection=djconn) for s in dj.list_schemas()}}
    query, fetch_args = dj_query(vm_dict)

    query_attributes = dict(primary=[], secondary=[])
    for attribute_name, attribute_info in query.heading.attributes.items():
        if attribute_info.in_key:
            query_attributes['primary'].append((
                attribute_name,
                attribute_info.type,
                attribute_info.nullable,
                attribute_info.default,
                attribute_info.autoincrement
                ))
        else:
            query_attributes['secondary'].append((
                attribute_name,
                attribute_info.type,
                attribute_info.nullable,
                attribute_info.default,
                attribute_info.autoincrement
                ))
    attributes_meta = dict(attribute_headers=['name', 'type', 'nullable', 'default',
                           'autoincrement'], attributes=query_attributes)

    return dict(attributeHeaders=attributes_meta['attribute_headers'],
                attributes=attributes_meta['attributes'])
"""

    spec_path = os.environ.get('API_SPEC_PATH')
    api_path = 'pharus/dynamic_api.py'
    with open(Path(api_path), 'w') as f, open(Path(spec_path), 'r') as y:
        f.write(header_template)
        values_yaml = yaml.load(y, Loader=yaml.FullLoader)
        pages = values_yaml['SciViz']['pages']

        # Crawl through the yaml file for the routes in the components
        for page in pages.values():
            for grid in page['grids'].values():
                for comp in grid['components'].values():
                    f.write(route_template.format(route=comp['route'],
                            method_name=comp['route'].replace('/', ''),
                            query=indent(comp['dj_query'], '    ')))
