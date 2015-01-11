.PHONY: install

install:
	make clean
	python setup.py install
	make clean

develop:
	make clean
	python setup.py develop
	rm -rf build/ dist/

clean:
	rm -rf build/ dist/ *.egg-info
	find . -name '*.pyc' -delete