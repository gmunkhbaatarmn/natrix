test:
	@flake8 natrix.py tests.py
	@coverage run tests.py
	@coverage report -m natrix.py
	@coverage erase
