# TODO: rename binary to euscan-ng
BIN = euscan


.PHONY:
	clean
	install-user
	install-user-test
	install-user-web
	install
	uninstall distclean


clean:
	sh clean.sh


install-user:
	python setup.py -v install --user

install-user-test:
	python setup.py -v install --user test

install-user-web:
	python setup.py -v install --user web

install: install-user


uninstall:
	pip uninstall -v -y $(BIN)


distclean: uninstall
distclean: clean
