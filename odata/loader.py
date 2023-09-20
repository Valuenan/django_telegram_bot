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


class ProductImage(BaseModel):
    deletion_mark: bool = Field(alias='DeletionMark')
    ref_key: str = Field(alias='Ref_Key')
    description: str = Field(alias='Description')
    file_format: str = Field(alias='Расширение')


def _deserializer(model: object, value: dict) -> list:
    try:
        json_data = json.dumps(value)
        data = [model.model_validate_json(json_data)]
    except ValidationError as err:
        print("Exeption", err.json())
    else:
        return data


def create_request(login: str, password: str, model: object, server_url: str, base: str, top: int = 0,
                   **kwargs) -> dict or None:
    http.client.HTTPConnection.debuglevel = 0

    logging.basicConfig(filename='oadtalog')
    logging.getLogger().setLevel(logging.DEBUG)
    # requests_log = logging.getLogger("requests.packages.urllib3")
    # requests_log.setLevel(logging.DEBUG)
    # requests_log.propagate = True

    result_ = []
    odata = 'odata/standard.odata/'
    params = {}
    format_ = ''
    content = ''
    select = ''
    filter_ = ''
    order_by = ''
    if 'guid' in kwargs and kwargs['guid'] and model not in [ProductImage]:
        raise OdataError('С данной моделью нельзя передавать guid')
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
        elif model == ProductImage:
            if 'guid' in kwargs and kwargs['guid'] and type(kwargs['guid']) == str:
                guid = kwargs['guid']
            else:
                raise NameError('C этой моделью необходимо передать guid сущности CatalogProduct тип данных str')
            format_ = 'json'
            content = f"Catalog_Номенклатура(guid'{guid}')/ФайлКартинки"
            select = 'DeletionMark,Ref_Key,Description,Расширение'
            raw_filter = 'not DeletionMark'
            filter_ = quote(raw_filter)
            order_by = ''
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
            if value:
                url += f'{param}={value}&'
        else:
            url = url[:-1]
        resp = session.get(url, auth=HTTPBasicAuth(login, password))
        if resp.status_code == 404:
            return None
        else:
            if not model:
                return print(resp.text)
            else:
                resp_json = resp.json()
                if 'odata.error' in resp_json.keys():
                    raise OdataError(resp_json['odata.error']['message']['value'])
                if 'guid' in kwargs and kwargs['guid']:
                    result_ = _deserializer(model, resp_json)
                else:
                    for value in resp_json['value']:
                        result_ += _deserializer(model, value)

                return result_


if __name__ == '__main__':
    result = create_request(login=CREDENTIALS_1C['login'], password=CREDENTIALS_1C['password'], model=ProductImage,
                            server_url='clgl.1cbit.ru:10443/', base='470319099582-ut/',
                            guid='c8dd74aa-0b53-11ec-a0c6-005056b6fe75')
    print(result)
