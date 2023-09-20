import json
import logging
import http.client
from urllib.parse import quote

from pydantic import BaseModel, Field, ValidationError
from requests.auth import HTTPBasicAuth

from shop.telegram.http_adapter import get_legacy_session
from shop.telegram.settings import CREDENTIALS_1C


class OdataError(Exception):
    pass


class CatalogFolder(BaseModel):
    deletion_mark: bool = Field(alias='DeletionMark')
    is_folder: bool = Field(alias='IsFolder')
    ref_key: str = Field(alias='Ref_Key')
    parent_key: str = Field(alias='Parent_Key')
    search: int = Field(alias='КодДляПоиска')
    description: str = Field(alias='Description')


class CatalogProduct(BaseModel):
    deletion_mark: bool = Field(alias='DeletionMark')
    parent_key: str = Field(alias='Parent_Key')
    ref_key: str = Field(alias='Ref_Key')
    name: str = Field(alias='НаименованиеПолное')
    search: int = Field(alias='КодДляПоиска')
    img_key: str = Field(alias='ФайлКартинки_Key')


def create_request(login: str, password: str, model: object, server_url: str, base: str, top: int = 0, *args,
                   **kwargs) -> dict:
    http.client.HTTPConnection.debuglevel = 0

    logging.basicConfig(filename='oadtalog')
    logging.getLogger().setLevel(logging.DEBUG)
    # requests_log = logging.getLogger("requests.packages.urllib3")
    # requests_log.setLevel(logging.DEBUG)
    # requests_log.propagate = True

    result = []
    odata = 'odata/standard.odata/'
    params = {}
    format_ = ''
    content = ''
    select = ''
    filter_ = ''
    order_by = ''

    if not model:
        params['$metadata'] = ''
    else:
        if model == CatalogProduct:
            format_ = 'json'
            content = 'Catalog_Номенклатура/'
            select = 'DeletionMark,Parent_Key,Ref_Key,НаименованиеПолное,КодДляПоиска,ФайлКартинки_Key'
            raw_filter = 'not IsFolder and not DeletionMark'
            filter_ = quote(raw_filter)
            order_by = ''
        elif model == CatalogFolder:
            format_ = 'json'
            content = 'Catalog_Номенклатура/'
            select = 'DeletionMark,IsFolder,Ref_Key,Parent_Key,КодДляПоиска,Description'
            raw_filter = 'IsFolder and not DeletionMark'
            filter_ = quote(raw_filter)
            order_by = 'Parent_Key'
        params['$format'] = format_
        params['$filter'] = filter_
        params['$select'] = select
        params['$orderby'] = order_by
        if top != 0:
            params['$top'] = top

    base_url = 'https://' + server_url + base + odata

    with get_legacy_session() as session:
        url = base_url + content + '?'
        for param, value in params.items():
            url += f'{param}={value}&'
        else:
            url = url[:-1]

        resp = session.get(url, auth=HTTPBasicAuth(login, password))

        if not model:
            return print(resp.text)
        else:
            resp_json = resp.json()
            if 'odata.error' in resp_json.keys():
                raise OdataError(resp_json['odata.error']['message']['value'])
            for value in resp_json['value']:
                try:
                    json_data = json.dumps(value)
                    result += [model.model_validate_json(json_data)]
                except ValidationError as err:
                    print("Exeption", err.json())
            return result


if __name__ == '__main__':
    create_request(login=CREDENTIALS_1C['login'], password=CREDENTIALS_1C['password'], model=CatalogProduct,
                   server_url='clgl.1cbit.ru:10443/', base='470319099582-ut/', top=50)
