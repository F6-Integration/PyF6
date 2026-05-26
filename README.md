# PyF6


[![Python](https://img.shields.io/badge/python-v3.6.8+-blue?logo=python)](https://python.org/downloads/release/python-368/)
[![PyF6](https://img.shields.io/badge/pyf6-v0.7.11+-orange?)](https://github.com/F6-Integration/pyf6/releases/tag/0.7.11/)

**PyF6** - Python library to communicate with **Products** (TI, DRP, ASM) via  **API**.



## **Content**

* [Content](#content)
* [Installation](#installation)
* [Usage](#usage)
  * [Initialization](#initialization)
  * [Collection mapping](#collection-mapping)
  * [Portions generator](#portions-generator)
  * [Extra methods](#extra-methods)
    * [Available collections](#available-collections)
    * [Find feed by ID](#find-feed-by-id)
    * [Download file](#download-file)
    * [Get start seqUpdate number](#get-start-sequpdate-number)
  * [Close session](#close-session)
* [Parsing](#parsing)
  * [Parse portion method](#parse-portion-method)
  * [Get IoCs method](#get-iocs-method)
* [Examples](#examples)
  * [Full version of program](#full-version-of-the-program)
  * [Mapper](#mapper)
* [API logic](#api-logic) 
  * [Sequence update logic](#sequence-update-logic)
    * API response
    * Iteration steps
    * Stop the iteration
  * [Search logic](#search-logic)
    * API response
    * Iteration steps
    * Stop the iteration
* [Records limit](#records-limit)
* [Troubleshooting](#troubleshooting)
  * [301-302 Redirected](#301-302-redirected)
  * [400 Bad Request](#400-bad-request)
  * [401 Unauthorized](#401-unauthorized)
  * [403 Forbidden](#403-forbidden)
  * [404 Not Found](#404-not-found)
  * [429 Too Many Requests](#429-too-many-requests)
  * [500 Internal Server Error](#500-internal-server-error)
  * [504 response code or timeout](#504-gateway-timeout)
* [FAQ](#faq)



<br>



## **Installation**

Lib deps: **pyaml**, **requests**, **urllib3**, **dataclasses**.

PyF6 lib is available on [PyPI](https://pypi.org/project/pyf6/):

```
pip install pyf6
```

Or use a Portal WHL archive. Replace `X.X.X` with the current lib version:

```
pip install ./pyf6-X.X.X-py3-none-any.whl
```



<br>



## **Usage**


### Initialization

Initialize **poller** with your credentials and set proxy (proxy should be in request-like format) if required.

Change SSL Verification using `set_verify()` method. \
If verify is set to `False`, requests will accept any TLS certificate. \
If verify is set to `True`, requiring requests to verify the TLS certificate at the remote end. \
Put a path-like string to the custom TLS certificate if required.

```python
from pyf6 import TIPoller, DRPPoller

poller = TIPoller(username='example@gmail.com', api_key='API_KEY', api_url='API_URL')
poller.set_proxies(
  {"https": 'proxy_protocol' + "://" + 'proxy_user' + ":" + 'proxy_password' + "@" + 'proxy_ip' + ":" + 'proxy_port'})
poller.set_verify(True)
```

### Collection mapping

Method `set_keys()` sets **keys** to search in the selected **collection**. It should be python dict `mapping_keys = {key: value}` where \
**key** - result name \
**value** - dot-notation string with searchable keys

```python
mapping_keys = {"result_name": "searchable_key_1.searchable_key_2"}
```

Parser finds keys recursively in the API response, using dot-notation in **value**. 
If you want to add your own data to the results start the **value** with star `*`.

```python
mapping_keys = {
	"network": "indicators.params.ip", 
	"result_name": "*My_Value"
}
```

For `set_keys()` or `set_iocs_keys()` methods you can make a full template to get nested data in the way you want.

```python
mapping_keys = {
	'network': {
		'ips': 'indicators.params.ip'
	}, 
	'url': 'indicators.params.url', 
	'type': '*network'
}
poller.set_keys(collection_name="apt/threat", keys=mapping_keys)
poller.set_iocs_keys(collection_name="apt/threat", keys={"ips": "indicators.params.ip"})
```

### Portions generator

Use the next methods `create_update_generator()`, `create_search_generator()` to create a generator, which return portions of limited feeds. \
**Update generator** – goes through the feeds in ascending order. Feeds iteration based on `seqUpdate` field. \
**Search generator** – goes through the feeds in descending order. Feeds iteration based on `resultId` field.

**Note:** Update generator iterates over all collections excluding `compromised/breached` and `compromised/reaper`.
[Sequence update logic](#sequence-update-logic) is not applied to these collections.

```python
generator = poller.create_update_generator(
    collection_name='compromised/account_group', 
    date_from='2021-01-30', 
    date_to='2021-02-03', 
    query='8.8.8.8', 
    sequpdate=20000000, 
    limit=200
)
```

Each portion (iterable object) presented as `Parser` class object. 
You can get **raw data** (in JSON format) or **parsed portion** (Python dictionary format), 
using its methods and attributes. 

```python
for portion in generator:  
    parsed_json = portion.parse_portion(as_json=False)  
    iocs = portion.get_iocs(as_json=False) 
    sequpdate = portion.sequpdate  
    count = portion.count  
    raw_json = portion.raw_json  
    raw_dict = portion.raw_dict
    new_parsed_json = portion.bulk_parse_portion(keys_list=[{"ips": "indicators.params.ip"}, {"url": 'indicators.params.url'}], as_json=False)  
```

Attribute `sequpdate` of the generator-iterable object, gives you the last **sequence update number** (`seqUpdate`) 
of the feed, which you can save locally (refers to `create_update_generator()`). 

```python
sequpdate = portion.sequpdate
```

Attribute `result_id` of the generator-iterable object, gives you the **slice of data** that will exist for 5 minutes (`resultId`). 
The lifetime is extended with each subsequent request. You shouldn't save it as it will be destroyed after the 
iteration process is finished (refers to `create_search_generator()`). 

```python
result_id = portion.result_id
```

Attribute `count` of the generator-iterable object, shows you the number of feeds left. This amount still in the queue. 
For Search generator `count` will return total number of feeds in the queue. 

```python
count = portion.count
```

Methods `parse_portion()` and `get_iocs()` of generator-iterable objects, use your 
mapping keys (IoCs keys) to return parsed data.
You can override mapping keys using `keys` parameter in these functions. 

```python
parsed_json = portion.parse_portion(as_json=False)  
iocs = portion.get_iocs(as_json=False, keys=mapping_override_keys) 
```

Also, you can use `bulk_parse_portion()` method to get multiple parsed dicts from every feed.

```python
new_parsed_json = portion.bulk_parse_portion(keys_list=[{"ips": "indicators.params.ip"}, {"url": 'indicators.params.url'}], as_json=False)
```

### Extra methods

You can use some additional functions if required. 

#### Available collections

You should use `get_available_collections()` method before the normal API response if you want to avoid 
errors trying to access collections that you have no access to. \
(Endpoint: `https://<base URL>/api/v2/user/granted_collections`)

```python
collection_list = poller.get_available_collections()  
seq_update_dict = poller.get_seq_update_dict(date='2020-12-12')  
compromised_account_sequpdate = seq_update_dict.get('compromised/account')
```

#### Find feed by ID

You can find a specific feed by **id** with this command that also returns **Parser** object. \
(Endpoint: `https://<base URL>/api/v2/{collection_name}/{feed_id}`)

```python
feed = poller.search_feed_by_id(collection_name='compromised/account', feed_id='some_id')  
parsed_feed = feed.parse_portion()
```

#### Download file

You can get a binary file from threat reports. \
(Endpoint: `https://<base URL>/api/v2/{collection_name}/{feed_id}/file/{file_id}`)

```python
binary_file = poller.search_file_in_threats(collection_name='hi/threat', feed_id='some_id', file_id='some_file_id_inside_feed')
```

#### Get start seqUpdate number

You can get the seqUpdate number based on the date you choose to start the iteration process for the collection. \
(Endpoint: `https://<base URL>/api/v2/sequence_list`)

```python
binary_file = poller.get_seq_update_dict(date='2024-01-01', collection='hi/threat')
```

### Close session

Remember to close the session in **try…except…finally** block, or use poller with the context manager.

```python
from pyf6 import TIPoller
from pyf6.exception import InputException

...

try:
  poller = TIPoller('some@gmail.com', 'API_KEY', 'API_URL')
  ...
except InputException as e:
  logger.info("Wrong input: {0}".format(e))
finally:
  poller.close_session()

...

with TIPoller('some@gmail.com', 'API_KEY', 'API_URL') as poller:
  pass
```



<br>



## Parsing


Common example of API response from Collection (received feeds):

```python
api_response = [
    {
        'iocs': {
            'network': [
                {
                    'ip': [1, 2],
                    'url': 'url.com'
                },
                {
                    'ip': [3],
                    'url': ''
                }
            ]
        }
    },
    {
        'iocs': {
            'network': [
                {
                    'ip': [4, 5],
                    'url': 'new_url.com'
                }
            ]
        }
    }
]
```

### Parse portion method

Your mapping dict for `parse_portion()` or `bulk_parse_portion()` methods:

```python
mapping_keys = {
    'network': {'ips': 'iocs.network.ip'},
    'url': 'iocs.network.url',
    'type': '*custom_network'
}
```

Result of `parse_portion()` output:

```python
parsing_result = [
    {
        'network': {'ips': [[1, 2], [3]]},
        'url': ['url.com', ''],
        'type': 'custom_network'
    },
    {
        'network': {'ips': [[4, 5]]},
        'url': ['new_url.com'],
        'type': 'custom_network'
    }
]
```

Result of `bulk_parse_portion()` output:

```python
parsing_result = [
    [
        {
            'network': {'ips': [[1, 2], [3]]}, 
            'url': ['url.com', ''], 
            'type': 'custom_network'}
    ],
    [
        {
            'network': {'ips': [[4, 5]]},
            'url': ['new_url.com'], 
            'type': 'custom_network'}
    ]
]
```

### Get IoCs method

Your mapping dict for `get_iocs()` method:

```python
mapping_keys = {
    'ips': 'iocs.network.ip',
    'url': 'iocs.network.url'
}
```

Result of `get_iocs()` output:

```python
parsing_result = {
    'ips': [1, 2, 3, 4, 5], 
    'url': ['url.com', 'new_url.com']
}
```



<br>



## Examples

### Full version of the program

```python
import logging
from pyf6 import TIPoller
from pyf6.exception import InputException, ConnectionException, ParserException

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
...

# API
username="user@test.io"
api_key="ApIkey848"
api_url="https://<base URL>/api/v2"
# proxy
proxy_protocol="http"
proxy_user="proxy_user_1"
proxy_password="proxy_pass_1"
proxy_ip="192.168.5.5"
proxy_port="4322"
start_date="2024-01-01"

# mapping config
mapping_config = {
    "apt/threat": {
        "threat_report": {
            "__": "*Threat Report",
            "id": "id",
            "title": "title",
            "portal_link": {
                "__concatenate": {
                    "__": "TI Portal: Report - external reference",
                    "static": "https://<base URL>/ta/last-threats?threat=",
                    "dynamic": "id"
                }
            }
        },
        "file": {
            "__": "*IoC File",
            "file_list": {
                "__nested_dot_path_to_list": "indicators.params",
                "md5": "hashes.md5",
                "sha1": "hashes.sha1",
                "sha256": "hashes.sha256",
                "filename": "name",
                "size-in-bytes": "size"
            }
        }
    },
    "apt/threat_actor": {...}
}

# endpoints config
endpoints_config = {
    "collections": {
        "apt/threat": {
            "apply_hunting_rules": False,
            "default_date": "2024-01-01",
            "description": "",
            "enable": True,
            "limit": None,
            "seqUpdate": 17768741099878,
            "ttl": 90
        },
        "apt/threat_actor": {
            "apply_hunting_rules": False,
            "default_date": "2024-01-01",
            "description": "",
            "enable": True,
            "limit": None,
            "seqUpdate": None,
            "ttl": 365
        }
    }
}

try:
    # create poller instance
    poller = TIPoller(username=username, api_key=api_key, api_url=api_url)
    # set proxies
    poller.set_proxies({"https": proxy_protocol + "://" + proxy_user + ":" + proxy_password + "@" + proxy_ip + ":" + proxy_port})
    poller.set_verify(True)
    
    # set keys
    for collection, keys in mapping_config.items():
        poller.set_keys(collection, keys)
    
    for collection, state in endpoints_config.items():
        # create generator
        if state.get("sequpdate"):
            seqUpdate = state.get("sequpdate")
            generator = poller.create_update_generator(collection_name=collection, sequpdate=seqUpdate)
        else:
            _seqUpdate_dict = poller.get_seq_update_dict(date=start_date, collection=collection)
            seqUpdate = _seqUpdate_dict.get(collection, None)
            generator = poller.create_update_generator(collection_name=collection, sequpdate=seqUpdate)
        
        # iterate over collection data
        for portion in generator:
            # parse portion using mapping keys from mapping config
            parsed_portion = portion.parse_portion()
            # print result
            print(parsed_portion)
            # save seqUpdate to endpoint config
            endpoints_config[collection]["sequpdate"] = portion.sequpdate

except InputException as e:
    logging.exception("Wrong input: {0}".format(e))
except ConnectionException as e:
    logging.exception("Something wrong with connection: {0}".format(e))
except ParserException as e:
    logging.exception("Exception occured during parsing: {0}".format(e))
finally:
    poller.close_session()
```


### Mapper

In some cases we need extra manipulations with parser. So we could use extended features in mapper.
1. `__concatenate` key is used to concatenate your 'static' data string with 'dynamic' data string. 
'Dynamic' data will be extracted from the feed. Description in the '__concatenate' is using `"__"` key if needed. 
Applying `*` to the description string is not required.
2. `*` before the value is used to avoid parsing process and leave the string data as is.
3. `__nested_dot_path_to_list` key is used to parse a nested list of dicts. So after we extract the 'indicators.params' 
list, we apply parsing to each nested element using the values ('hashes.md5', 'hashes.sha1') below. So we extract
dict groups of data related to one object (file, report, matrix).

Here is a mapper example:

```json
{
    "apt/threat": {
        "threat_report": {
            "__": "*Threat Report",
            "id": "id",
            "title": "title",
            "portal_link": {
                "__concatenate": {
                    "__": "TI Portal: Report - external reference",
                    "static": "https://<base URL>/ta/last-threats?threat=",
                    "dynamic": "id"
                }
            }
        },
        "file": {
            "__": "*IoC File",
            "file_list": {
                "__nested_dot_path_to_list": "indicators.params",
                "md5": "hashes.md5",
                "sha1": "hashes.sha1",
                "sha256": "hashes.sha256",
                "filename": "name",
                "size-in-bytes": "size"
            }
        },
        ...
        "malware_report": {
            "__": "*Malware Report",
            "malware_report_list": {
                "__nested_dot_path_to_list": "malwareList",
                "name": "name",
                "category": "category",
                "platform": "platform",
                "aliases": "",
                "portal_link": {
                    "__concatenate": {
                        "__": "TI Portal: Malware - external reference",
                        "static": "https://<base URL>/malware/reports/",
                        "dynamic": "id"
                    }
                }
            }
        },
        ...
        "mitre_matrix": {
            "__": "*MITRE ATT&CK",
            "mitre_matrix_list": {
                "__nested_dot_path_to_list": "mitreMatrix",
                "attack_pattern": "mitreId",
                "kill_chain_phase": "attackTactic",
                "portal_link": {
                    "__concatenate": {
                        "__": "MITRE ATT&CK: Pattern - external reference",
                        "static": "https://attack.mitre.org/techniques/",
                        "dynamic": "mitreId"
                    }
                }
            }
        },
        ...
    }
}
```



<br>



## API logic

To iterate over received portions from the API response, you should follow one of the next iteration methods: 

- **Result ID iteration** method – based on `resultId` parameter, which was retrieved from previous response
with `df` and `dt` parameters. The `resultId` is a slice of data that will exist for 5 minutes. The lifetime
is extended with each subsequent request.
Uses common collection name endpoint (`apt/threat`) which is added to the base URL >>> `/api/v2/apt/threat`. 
- **Sequence update iteration** method – based on `seqUpdate` parameter, which was retrieved from previous response.
Uses updated endpoint (`/updated`) after collection name (`/apt/threat`) >>> `/api/v2/apt/threat/updated`.


To search IPs, domains, hashes, emails, etc., you should follow the next logic: 

- **Search logic** – 
first you should reach `/api/v2/search` endpoint with any `q` parameter >>> `/api/v2/search?q=8.8.8.8`.
In the output response you will receive collections, which contains the search result (`8.8.8.8`).
Use the _Sequence update iteration_ method or _Result ID iteration_ method as a next step to retrieve all events.


To get the latest updates on each collection event, you should follow the next logic: 

- **Sequence update logic** – 
first you should reach `/api/v2/sequnce_list` endpoint with `date` and `collection` parameters (optional) >>> 
`/api/v2/sequnce_list?date=2022-01-01&collection=apt/threat`.
In the output response you will receive `seqUpdate` number, which you should use in the next request to collection `/updated` endpoint.
Use the _Sequence update iteration_ method as a next step to retrieve all events.


To get a slice of data as is without updates, you should follow the next logic:

- **Slice logic** – 
first you should reach common collection name endpoint (`apt/threat`) which is added to the base URL >>> 
`/api/v2/apt/threat?df=2024-01-01&dt=2025-01-01`.
Or any other collection you need. Parameters `df` and `dt` should be set to determine data slice. In the JSON response
you should extract `resultId` and use it in the next requests.
Use _Result ID iteration_ method as a next step to retrieve all events.



<br>



### Sequence update logic

Most of the collections at the Threat Intelligence portal has `/updated` endpoint. 
And this endpoint uses updated logic based on `seqUpdate` key field, which comes from API JSON response.

The `seqUpdate` key – is a time from Epoch converted to a big number (microseconds), using the next formula:

```text
UTC timestamp * 1000 * 1000. 
```

_Note:_ Don't rely on this formula. Because of the rising amount of data, it could be changed. 
For that purpose `/api/v2/sequence_list` endpoint was created. 
Use this endpoint to get required `seqUpdate` number.

#### API response

Each row in our database has its own unique sequence update number. So, we can get all the events one by one. 
To check it, you can explore JSON output and then explore each item in the `"items"` field. 
So, each item contains a `seqUpdate` field. And the last element’s `seqUpdate` is put to the top level of JSON output. 
You can use it to get the next portion of feeds. 
Each collection has its own updated route like `/api/v2/apt/threat/updated`, so we can use the next output as an example.

```json
{
    "count": 1761,
    "items": [
        {"id": "fake286ca753feed3476649438e4e4488"...},
        {"id": "fake51d29357b22b80564a1d2f9fc8751"...},
        {
            "author": null,
            "companyId": [],
            "id": "fake4f16300296d20ef9b909dc0d354fb",
            ......,
            "indicators": [
                {
                    "dateFirstSeen": null,
                    "dateLastSeen": null,
                    "deleted": false,
                    "description": null,
                    "domain": "fake-fakesop.net",
                    "id": "fakebe483bb82759fbee7038235e0f52d0",
                    .....
                }
            ],
            "indicatorsIds": [
                "fakebe483bb82759fbee7038235e0f52d0"
            ],
            "isPublished": true,
            "isTailored": false,
            "labels": [],
            "langs": [
                "en"
            ],
            "malwareList": [],
            ......,
            "seqUpdate": 16172928022293
        },
    ],
    "seqUpdate": 16172928022293
}
```

#### Iteration steps

To iterate over `/api/v2/apt/threat/updated` endpoint data, you need to collect this 
field number (`"seqUpdate": 16172928022293`) right at the top level of the JSON response, 
received from previous request or from `/sequnce_list` endpoint.

```console
curl -X 'GET' 'https://<base URL>/api/v2/sequnce_list?date=2024-01-01&collection=apt/threat'
```

Add gathered `seqUpdate` in the next request, using endpoint params.

```console
curl -X 'GET' 'https://<base URL>/api/v2/apt/threat/updated?seqUpdate=16172928022293'
```

In the received JSON output check the `"count": 1751`. → \
Gather `seqUpdate` from last feed or at top level → \
Put it in next request → 

```console
curl -X 'GET' 'https://<base URL>/api/v2/apt/threat/updated?seqUpdate=16172928536227'
```

In the received JSON output, check the `"count": 1741` → \
Gather `seqUpdate` from last feed or at top level → \
Repeat till the end.

#### Stop the iteration

The "stop word" in that logic is items `"count"` or `"items"` list length. 
For the collection `apt/threat` in the above example, the `limit` is set to 10 by default; 
the other collections usually have 100 `limit`. The limit depends on the amount of data to not overload the JSON output.
For example, usually you receive a portion of 100 feeds (not 10) for the first iteration. → 
Then could be a portion of 23 feeds → Then a portion of 0 feeds → The end.



<br>



### Search logic

Search logic is used to find attribution to the search value in the Threat Intelligence database.

#### Global search

To find events related to IP, domain, hash, email, etc., you should send request to the `/api/v2/search` endpoint 
with any `q` parameter (`/api/v2/search?q=8.8.8.8`). 
It will return a list of collections, which contains this searchable parameter. 
As a next step, we need to use _Sequence update iteration_ over all items in each collection.
You can specify the searchable type keyword to avoid side results by setting `q` parameter like `/api/v2/search?q=ip:8.8.8.8`.
The same can be done for domain, email, hash, etc. (`/api/v2/search?q=domain:google.com`, `/api/v2/search?q=email:example@gmail.com`).


```json
[
    {
        "apiPath": "suspicious_ip/open_proxy",
        "label": "Suspicious IP :: Open Proxy",
        "link": "https://tap.group-ib.com/api/v2/suspicious_ip/open_proxy?q=ip:8.8.8.8",
        "count": 14,
        "time": 0.304644684,
        "detailedLinks": null
    },
    {
        "apiPath": "attacks/ddos",
        "label": "Attack :: DDoS",
        "link": "https://tap.group-ib.com/api/v2/attacks/ddos?q=ip:8.8.8.8",
        "count": 1490,
        "time": 0.389418291,
        "detailedLinks": null
    },
    {"apiPath": "attacks/deface"...},
    {"apiPath": "malware/config"...},
    {"apiPath": "suspicious_ip/scanner"...}
]

```

#### Iteration steps

On the first search step we receive information that collection `attacks/ddos` contains 1490 items (`"count": 1490`). 
Let's extract all of them. First we need to send request to this collection with the `q` parameter (`?q=ip:8.8.8.8`).
Then we retrieve `"seqUpdate"` field right at the top level of the JSON response and use it in the next request (`"seqUpdate": 1673373011294`).

```json
{
  "count": 1490,
  "items": [
    {
      "body": null,
      "cnc": {"cnc": "http://ex-ex.net/drv/"...},
      "company": null,
      "companyId": null,
      "dateBegin": null,
      "dateEnd": null,
      "dateReg": "2017-08-16T00:00:00+00:00",
      "evaluation": {},
      "favouriteForCompanies": [],
      "headers": [],
      "hideForCompanies": [],
      "id": "examplec58903baddc84b8c51eaef1f904374025d",
      "isFavourite": false,
      ...
    }
  ],
  ...,
  "seqUpdate": 1673373011294
}
```

So the next request should look like this `/api/v2/attacks/ddos/updated?q=ip:8.8.8.8&seqUpdate=1673373011294`.
We can also set the `limit` parameter in the requests, like `limit=500`.
Explore the example below.

```console
curl -X 'GET' 'https://<base URL>/api/v2/search?q=ip:8.8.8.8'
```

Add gathered `seqUpdate` in the next request, using endpoint params.

```console
curl -X 'GET' 'https://<base URL>/api/v2/apt/threat/updated?seqUpdate=1673373011294'
```

In the received JSON output check the `"count": 1390`. → \
Gather `seqUpdate` from last feed or at top level → \
Put it in next request → 

```console
curl -X 'GET' 'https://<base URL>/api/v2/apt/threat/updated?seqUpdate=1673375930599'
```

In the received JSON output, check the `"count": 1290` → \
Gather `seqUpdate` from last feed or at top level → \
Repeat till the end.

#### Stop the iteration

The "stop word" in that logic is items `"count"` or `"items"` list length. 
For the collection `attacks/ddos` in the above example, the `limit` is set to 100 by default, 
the other collections it may differ. The limit depends on the amount of data to not overload the JSON output.
For example, usually you receive a portion of 100 feeds for the first iteration. → 
Then could be a portion of 23 feeds → Then a portion of 0 feeds → The end.



<br>



### Slice logic

Description



<br>



## Records limit

The default limit is 100 records per request. Due to different sizes of feeds, there are different limits for getting data.

To change record limit in response, add param `limit=500` to the request. 
All limits for different collections can be found in the Portal documentation.

```console
curl -X 'GET' 'https://<base URL>/api/v2/apt/threat/updated?limit=500&seqUpdate=16172928022293'
```



<br>



### **Pack the package**

```
python setup.py sdist
python setup.py bdist_wheel
```

```
pip install wheel
python setup.py build
python setup.py install
python setup.py develop
```



<br>



## Troubleshooting

### 301-302 Redirected

Make sure your public IP address is added to the Portal trusted IP list. If the address is not on the list, 
this error may occur.

### 400 Bad Request

Invalid request format. Check the JSON response to find the error and correct the request.

### 401 Unauthorized

Authorization failed. This error occurs when the request is missing credentials, or they were entered incorrectly. 
Make sure you are using Basic Authentication and have entered the correct username and API key. 
Double-check that the credentials are correct and are sent in the request header.

### 403 Forbidden

There are several possible reasons for it:

- IP address restrictions: Make sure the request is coming from an allowed IP address. You can change 
the list of private IP addresses in your Personal Account settings.
- API key issue: Make sure your API key is active. If necessary, create a new API key according to the instructions.
- No access to feeds: Make sure you have access to the requested feeds. You can view the list of available feeds 
in your Portal Personal Account → Security and Access.

### 404 Not Found

The requested data is not available. Make sure the URL is entered correctly and the requested resource exists.

### 429 Too Many Requests

The number of requests has exceeded the limit. Reduce the request rate or decrease the number of requests per second 
in the request limit setting.

### 500 Internal Server Error

Server-side error. Please wait and try again in a few minutes.

### 504 Gateway Timeout

The response time limit has been exceeded. Try reducing the API request limit parameter to reduce the server load 
and avoid this error.


## FAQ

Have a question? Ask in the SD Ticket on our Portal
