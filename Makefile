PACKAGE_NAME := pyscroll

.PHONY: build clean publish install lint test

build:
    python3 -m build

clean:
    rm -rf dist/ *.egg-info

publish: build
    python3 -m twine upload --repository pypi dist/*

install:
    pip install -e .

lint:
    black $(PACKAGE_NAME)/
    isort $(PACKAGE_NAME)/

test:
    pytest tests/
