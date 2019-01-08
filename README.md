[![Build][build-img]][build-url]
[![Issue][issue-img]][issue-url]

# Natrix
Natrix is a simple lightweight Python Web framework designed for
Google App Engine.

# Installing
Copy and paste `natrix.py` on your Google App Engine project directory.

# Simple Example
Project structure and files:
```
.
├── app.py
├── app.yaml
└── natrix.py
```

```python
# app.py
from natrix import route, app


@route("/")
def home(x):
    x.response("Hello, Natrix!")
```

```yaml
# app.yaml
application: sample
version: debug

runtime: python27
api_version: 1
threadsafe: false

handlers:
- url: /.*
  script: app.app

libraries:
- { name: jinja2,     version: "2.6"   }
```

Running:
```
dev_appserver.py .

INFO     2019-01-23 04:56:07,089 devappserver2.py:278] Skipping SDK update check.
INFO     2019-01-23 04:56:07,348 api_server.py:275] Starting API server at: http://localhost:49668
INFO     2019-01-23 04:56:07,357 dispatcher.py:256] Starting module "default" running at: http://localhost:8080
INFO     2019-01-23 04:56:07,360 admin_server.py:150] Starting admin server at: http://localhost:8000
```

[build-img]: https://img.shields.io/travis/gmunkhbaatarmn/natrix.svg
[build-url]: https://travis-ci.org/gmunkhbaatarmn/natrix

[issue-img]: https://img.shields.io/github/issues/gmunkhbaatarmn/natrix.svg
[issue-url]: https://github.com/gmunkhbaatarmn/natrix/issues
