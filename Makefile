DEV_CLAY_CONFIG=config/development.yaml
PROD_CLAY_CONFIG=config/production.yaml
PYMODULE=epubber

EGGS=$(PYMODULE).egg-info
ENVDIR=env

ACTIVATE=source $(ENVDIR)/bin/activate


all: $(ENVDIR) $(EGGS)


env:
	mkdir $(ENVDIR)
	virtualenv $(ENVDIR)
	bash -c "$(ACTIVATE) ; CFLAGS=-Qunused-arguments CPPFLAGS=-Qunused-arguments pip install -r requirements.txt"


$(EGGS):
	bash -c "$(ACTIVATE) ; python setup.py develop"


run-devel: $(ENVDIR) $(EGGS)
	bash -c "$(ACTIVATE) ; CLAY_CONFIG=$(DEV_CLAY_CONFIG) clay-devserver"


run-prod: $(ENVDIR) $(EGGS)
	bash -c "$(ACTIVATE) ; CLAY_CONFIG=$(PROD_CLAY_CONFIG) clay-devserver"


test:
	nosetests naps/tests


clean:
	find naps -name '*.pyc' -exec rm {} \;


distclean: clean
	rm -rf env *.egg-info


