.PHONY: install test inventory actions

install:
	python -m pip install -e '.[test]'

test:
	pytest -q

inventory:
	python -m homelab_ops.cli inventory

actions:
	python -m homelab_ops.cli actions
