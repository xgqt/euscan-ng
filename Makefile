# TODO: rename binary to euscan-ng
BIN = euscan


.PHONY:
	all
	clean
	install-user
	install-user-test
	install-user-web
	install
	uninstall distclean


all:
	@echo "Did nothing."
	@echo "To do user installation use target: install-user"


install-user:
	python setup.py -v install --user

install-user-test:
	pip install --user .'[test]'

install-user-web:
	pip install --user .'[web]'

install: install-user


clean:
	sh clean.sh

uninstall:
	pip uninstall -v -y $(BIN)

distclean:	clean	uninstall
