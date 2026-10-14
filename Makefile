# Charterloom AI task runner. Every target is a plain command with no dashed flags.

.PHONY: install kb build evaluate examples test serve all

install:
	pip install .

kb:
	charterloom kb

build:
	charterloom build

evaluate:
	charterloom evaluate

examples:
	charterloom examples

test:
	pytest

serve:
	charterloom serve host=0.0.0.0 port=8000

all: kb build evaluate examples test
