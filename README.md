[![Build Status][build-status-img]][build-status-url]
[![Open issues][open-issues-img]][open-issues-url]
[![Coverage report][coverage-report-img]][coverage-report-url]
[![License][license-img]][license-url]

# Natrix
Natrix is a simple lightweight Python Web framework for Google App Engine. It is distributed as a single file module and has no dependencies.

### Example: Hello, natrix!

```python
# app.py
from natrix import route, app

@route("/")
def home(x):
    x.response("Hello, natrix!")
```

<details><summary>Complete details</summary>

<p>

Project structure and files:
```
.
├── app.py
├── app.yaml
└── natrix.py
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
- { name: jinja2, version: "2.6" }
```

Running:
```
dev_appserver.py .

INFO     2019-01-23 04:56:07,089 devappserver2.py:278] Skipping SDK update check.
INFO     2019-01-23 04:56:07,348 api_server.py:275] Starting API server at: http://localhost:49668
INFO     2019-01-23 04:56:07,357 dispatcher.py:256] Starting module "default" running at: http://localhost:8080
INFO     2019-01-23 04:56:07,360 admin_server.py:150] Starting admin server at: http://localhost:8000
```
</p></details>

### Install
Download [natrix.py](https://github.com/gmunkhbaatarmn/natrix/raw/v0.1.8/natrix.py) into your Google App Engine project directory.
There are no hard dependencies other than the Python standard library, Google App Engine included libraries.

[build-status-img]: https://img.shields.io/travis/gmunkhbaatarmn/natrix.svg
[build-status-url]: https://travis-ci.org/gmunkhbaatarmn/natrix

[open-issues-img]: https://img.shields.io/github/issues/gmunkhbaatarmn/natrix.svg
[open-issues-url]: https://github.com/gmunkhbaatarmn/natrix/issues

[coverage-report-img]: https://coveralls.io/repos/github/gmunkhbaatarmn/natrix/badge.svg?branch=master
[coverage-report-url]: https://coveralls.io/github/gmunkhbaatarmn/natrix?branch=master

[license-img]: https://img.shields.io/github/license/gmunkhbaatarmn/natrix.svg
[license-url]: https://github.com/gmunkhbaatarmn/natrix/blob/master/LICENSE
