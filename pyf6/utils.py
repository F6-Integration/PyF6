# -*- encoding: utf-8 -*-
"""
Copyright (c) 2025 - present by F6
"""
from datetime import datetime
from typing import Union
from urllib.parse import urljoin

try:
    import pyaml
except Exception:
    pass

from .exception import InputException, EmptyCredsError, BadProtocolError, EncryptionError
from .const import CollectionConsts


class Validator(object):
    @classmethod
    def validate_collection_name(cls, collection_name, method=None):
        """Validate a collection name is exist in API and if update feed generator may be created"""
        if method == "update" and collection_name in CollectionConsts.ONLY_SEARCH_COLLECTIONS:
            raise InputException(f"{collection_name} collection must be used only with a search generator.")

        collection_names = CollectionConsts.TI_COLLECTIONS_INFO.keys()
        drp_collection_names = CollectionConsts.DRP_COLLECTIONS_INFO.keys()
        if (collection_name not in collection_names) and (collection_name not in drp_collection_names):
            raise InputException(f"Invalid collection name {collection_name}, "
                                 f"should be one of this {', '.join(collection_names)} "
                                 f"or one of this {', '.join(drp_collection_names)}")

    @classmethod
    def validate_date_format(cls, date, formats):
        """Validate a date format is allowed"""
        for i in formats:
            try:
                datetime.strptime(date, i)
                return
            except (TypeError, ValueError):
                pass
        raise InputException(f"Invalid date {date}, please use one of this formats: {', '.join(formats)}.")

    @classmethod
    def validate_set_iocs_keys_input(cls, keys):
        """Validate mapper keys"""
        if isinstance(keys, dict):
            for i in keys.values():
                cls.validate_set_keys_input(i)
        elif not isinstance(keys, str):
            raise InputException('Keys should be stored in nested dicts and on the lower level it should be a string.')

    @classmethod
    def validate_set_keys_input(cls, keys):
        """Validate mapper keys"""
        if isinstance(keys, dict):
            for i in keys.values():
                cls.validate_set_keys_input(i)
        elif not isinstance(keys, str):
            raise InputException('Keys should be stored in nested dicts and on the lower level it should be a string.')

    @classmethod
    def validate_group_collections(cls, collections):
        """Validate group collections are in allowed list"""
        if collections in CollectionConsts.GROUP_COLLECTIONS:
            return True


class ParserHelper(object):
    """
    Class with recursive methods
    """

    @classmethod
    def find_by_template(cls, feed, keys, **kwargs):
        # type: (dict, dict, dict) -> dict
        """Recursively check feed elements using template (mapper) and return parsed dict."""
        parsed_dict = {}
        for key, value in keys.items():
            # if value dot-string {"pl": "malwareList.platform"} or a dict ("pls": {"pl1": "malwareList.platform"})
            if isinstance(value, str):
                # avoid adding __nested_dot_path_to_list key in the parsed_dict
                if key != "__nested_dot_path_to_list":
                    if value.startswith("*"):
                        # if we have * ("__description": "*Description string")
                        # replace will be next ("*Description string" -> "Description string")
                        # instead of searching it
                        parsed_dict.update({key: value[1:]})
                    elif value.startswith("#"):
                        # API send some hashes in list like "hash": ["1Df213", "1Df213dds", "1Df213dds3lkm"] and to
                        # extract them like "md5": "1Df213", "sha1": "1Df213dds", "sha256": "1Df213dds3lkm" we use #
                        # in mapper: "md5": "#hash[0] . So we extract from key 'hash' with values in list above
                        # first element as md5. "sha1": "#hash[1]" -> second elements as sha1
                        #
                        # retrieve "hash" and "0" from "#hash[0]"
                        v, num = value[1:-1].split("[")
                        # we expect list of items
                        # if we found list and list has items
                        # we take list[0] or list[1] ...
                        new_val = cls.find_element_by_key(obj=feed, key=v)
                        if isinstance(new_val, list) and len(new_val) > int(num):
                            parsed_dict.update({key: new_val[int(num)]})
                        else:
                            # else we put None
                            parsed_dict.update({key: None})
                    else:
                        # no "*", "#" -> find element
                        element = cls.find_element_by_key(obj=feed, key=value)
                        # custom: -convert list to string with elements sep=,
                        if kwargs.get("use_join_to_end_list") and isinstance(element, list) and all(isinstance(_, str) for _ in element):
                            if kwargs.get("except_keys") and key in kwargs.get("except_keys"):
                                parsed_dict.update({key: element})
                            else:
                                parsed_dict.update({key: ",".join(element)})
                        else:
                            parsed_dict.update({key: element})
            elif isinstance(value, dict):
                # __nested_dot_path_to_list is used to process lists in the feed.
                # The value in this key is the path to the list in the feed to be expanded.
                # The same pattern (value) is applied to each list item, which allows you
                # to automatically handle arrays of nested objects.
                #
                # if dict -> we go deeper
                # CUSTOM FEATURES:
                # -- create list of dicts
                if value.get("__nested_dot_path_to_list"):
                    # warning! if [[],[],[]] like indicators[].params[] we rely on JSON?
                    # list_obj -> found object by __nested_dot_path_to_list in feed (should be list)
                    list_obj = cls.find_element_by_key(obj=feed, key=value.get("__nested_dot_path_to_list"))
                    if isinstance(list_obj, list):
                        # apply mapping to each element in list_obj
                        parsed_dict.update({
                            key: [cls.find_by_template(nested_feed, value, **kwargs) for nested_feed in list_obj]
                        })
                    elif isinstance(list_obj, dict):
                        # act in normal way but return list
                        parsed_dict.update({
                            key: [cls.find_by_template(list_obj, value, **kwargs)]
                        })
                # -- concatenate static string and found dynamic element
                # key = portal_link, value = {_concatenate}
                elif value.get("__concatenate"):
                    _concat_values = value.get("__concatenate", {})
                    _description = _concat_values.get("__", "")
                    static = _concat_values.get("static")
                    _flag = _concat_values.get("flag", False)
                    _format = _concat_values.get("format", False)
                    dynamic = cls.find_element_by_key(obj=feed, key=_concat_values.get("dynamic"))
                    if dynamic:
                        # if mitre result -> T010.202 -> T010/202
                        _slashed = "/".join(dynamic.split("."))
                        if _format:
                            concatenate_result = static.format(_slashed)
                        else:
                            concatenate_result = str(static) + str(_slashed)
                        if _flag:
                            parsed_dict.update({
                                key: concatenate_result
                            })
                        else:
                            parsed_dict.update({
                                key: {
                                    "__": _description,
                                    "static": static,
                                    "dynamic": dynamic,
                                    "result": concatenate_result
                                }
                            })
                    else:
                        parsed_dict.update({
                            key: {}
                        })

                # -- act in normal way
                else:
                    parsed_dict.update({key: cls.find_by_template(feed, value, **kwargs)})

        return parsed_dict

    @classmethod
    def find_element_by_key(cls, obj, key):
        """
        Recursively finds element or elements in dict.
        """
        # "malwareList.platform.win" -> ["malwareList", "platform.win"]; "platform.win" -> ["platform", "win"]; "win" ->
        path = key.split(".", 1)
        # if it is a last word in dot-notation string -> act normal
        if len(path) == 1:
            if isinstance(obj, list):
                # extract value in each element of list obj
                return [i.get(path[0]) for i in obj]
            elif isinstance(obj, dict):
                # extract value in dict obj
                return obj.get(path[0])
            else:
                return obj
        # else go deeper in dot-notation string
        else:
            if isinstance(obj, list):
                # extract (data by key, take next key from dot-string) for each element in list
                return [cls.find_element_by_key(i.get(path[0]), path[1]) for i in obj]
            elif isinstance(obj, dict):
                # extract (data by key, take next key from dot-string)
                return cls.find_element_by_key(obj.get(path[0]), path[1])
            else:
                # finnish extraction
                return obj

    @classmethod
    def unpack_iocs(cls, ioc):
        # type: (Union[list, str]) -> list
        """
        Recursively unpacks all IOCs in one list.
        """
        unpacked = []
        if isinstance(ioc, list):
            for i in ioc:
                unpacked.extend(cls.unpack_iocs(i))
        else:
            if ioc not in ['255.255.255.255', '0.0.0.0', '', None]:
                unpacked.append(ioc)

        return list(set(unpacked))


class ProxyConfigurator:

    @staticmethod
    def check_proxy_connection():
        pass

    @staticmethod
    def get_proxies(
            proxy_protocol=None,
            proxy_ip=None,
            proxy_port=None,
            proxy_username=None,
            proxy_password=None,
            encrypted_data_handler=None
    ):
        # type: (str, str, str, str, str, Any) -> Union[Dict[str, str], None]
        """
        Method that returns proxies from given arguments. Only HTTP and HTTPS allowed.

            Return format:

            >>> {
            >>>     "http": "{protocol}://{username}:{password}@{ip}:{port}",
            >>>     "https": "{protocol}://{username}:{password}@{ip}:{port}"
            >>> }

        :param proxy_protocol: HTTP or HTTPS
        :param proxy_ip: 255.255.255.255 format
        :param proxy_port: 3128, 3129, ...
        :param proxy_username: Username
        :param proxy_password: Password parametr ignored for secure purpose
        :param encrypted_data_handler: Encryption object engine which is used to decrypt password
        :return: proxies
        """

        if not proxy_protocol or not proxy_ip or not proxy_port:
            return None

        protocol_allowed_list = ["http", "https"]
        proxy_protocol = proxy_protocol.lower()

        if proxy_protocol not in protocol_allowed_list:
            raise BadProtocolError("Bad protocol used for proxy: {protocol}! Expected: {allowed}".format(
                protocol=proxy_protocol,
                allowed=protocol_allowed_list
            ))

        if encrypted_data_handler:
            try:
                __proxy_password = encrypted_data_handler(label='proxy_password').decrypt()
            except EncryptionError:
                __proxy_password = None
        else:
            __proxy_password = proxy_password

        if proxy_username and __proxy_password:
            __proxy_dict = {
                "http": "{protocol}://{username}:{password}@{ip}:{port}".format(
                    protocol=proxy_protocol,
                    username=proxy_username,
                    password=__proxy_password,
                    ip=proxy_ip,
                    port=proxy_port
                ),
                "https": "{protocol}://{username}:{password}@{ip}:{port}".format(
                    protocol=proxy_protocol,
                    username=proxy_username,
                    password=__proxy_password,
                    ip=proxy_ip,
                    port=proxy_port
                )
            }
            return __proxy_dict

        __proxy_dict = {
            "http": "{protocol}://{ip}:{port}".format(
                protocol=proxy_protocol,
                ip=proxy_ip,
                port=proxy_port
            ),
            "https": "{protocol}://{ip}:{port}".format(
                protocol=proxy_protocol,
                ip=proxy_ip,
                port=proxy_port
            )
        }
        return __proxy_dict

