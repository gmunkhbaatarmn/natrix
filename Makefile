test:
	@flake8 --quotes '"' natrix.py
	@flake8 --quotes '"' tests.py --ignore=N802
	@coverage run tests.py
	@coverage report --show-missing -m natrix.py
	@coverage erase

init:
	@pip install flake8
	@pip install flake8-print flake8-quotes==0.2.2 flake8-blind-except pep8-naming
	@pip install coverage nose webtest
	@pip install appengine-sdk
