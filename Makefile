test:
	@flake8 natrix.py tests.py
	@coverage run tests.py
	@coverage report --show-missing -m natrix.py
	@coverage erase

init:
	@pip install flake8 coverage nose webtest
	@pip install appengine-sdk
