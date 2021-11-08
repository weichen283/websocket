## server
------

To run the server, simple execute:
```bash
python server.py
```

## cache
-----

To run the cache, execute:
```bash
python cache.py
```

## client
------

To run the client, execute:
```bash
python client.py http://host:port/file
```
where host is where the server is running (e.g. localhost), port is the port 
number reported by the server where it is running and file is the name of the 
file you want to retrieve.

-----

To connect with cache instead of server:
```bash
python client.py -proxy cachehost:cacheport http://host:port/file
```

where cachehost is where the cache is running (e.g., localhost), cacheport is 
the port number reported by the cache.
