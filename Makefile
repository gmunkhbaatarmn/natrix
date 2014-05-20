test:
	@coverage run tests.py
	@coverage report -m natrix.py
	@coverage erase
