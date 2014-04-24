FimFiction.net Reader
---------------------
Makes valid ePubs from FimFiction.net stories, including summary text and images.


To Set Up:
----------
```
mkdir env
virtualenv env
source env/bin/activate

# Config compiler flags so ldap module can compile.
export CFLAGS=-Qunused-arguments
export CPPFLAGS=-Qunused-arguments

pip install -r requirements.txt
python setup.py develop
```


Run KillSwitch Development Webserver.
-------------------------------------
```
CLAY_CONFIG=config/development.yaml clay-devserver
```


Tests:
------
```
nosetests epubber/tests
```

