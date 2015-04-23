test:
	@flake8 natrix.py tests.py
	@coverage run tests.py
	@coverage report -m natrix.py
	@coverage erase

init:
	@pip install flake8 coverage nose
	@pip install appengine-sdk
