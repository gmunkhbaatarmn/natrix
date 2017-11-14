test:
	@flake8 --max-line-length=100 --inline-quotes '"' natrix.py
	@flake8 --max-line-length=100 --inline-quotes '"' tests.py --ignore=N802
	@coverage run tests.py
	@coverage report --show-missing natrix.py
	@coverage erase

init:
	@pip install flake8
	@pip install flake8-print flake8-quotes flake8-blind-except pep8-naming
	@pip install flake8-builtins flake8-commas flake8-comprehensions
	@pip install coverage nose webtest
	@pip install appengine-sdk jinja2 pyyaml
