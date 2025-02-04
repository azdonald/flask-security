.. _contributing:

===========================
Contributing
===========================


.. highlight:: console

Contributions are welcome.  If you would like add features or fix bugs,
please review the information below.

One source of history or ideas are the `bug reports`_.
There you can find ideas for requested features, or the remains of rejected
ideas.

If you have a 'big idea' - please file an issue first so it can be discussed
prior to you spending a lot of time developing. New features need to be generally
useful - if your feature has limited applicability, consider making a small
change that ENABLES your feature, rather than trying to get the entire feature
into Flask-Security.

.. _bug reports: https://github.com/jwag956/flask-security/issues


Checklist
---------

    * All new code and bug fixes need unit tests
    * If you change/add to the external API be sure to update docs/openapi.yaml
    * Additions to configuration variables and/or messages must be documented
    * Make sure any new public API methods have good docstrings, are picked up by
      the api.rst document, and are exposed in __init__.py if appropriate.
    * Add appropriate info to CHANGES.rst


Getting the code
----------------

The code is hosted on a GitHub repo at
https://github.com/jwag956/flask-security.  To get a working environment, follow
these steps:

  #. (Optional, but recommended) Create a Python 3.6 (or greater) virtualenv to work in,
     and activate it.

  #.  Fork the repo `Flask-Security <https://github.com/jwag956/flask-security>`_
      (look for the "Fork" button).

  #.  Clone your fork locally::

        $ git clone https://github.com/<your-username>/flask-security

  #. Create a branch for local development::

     $ git checkout -b name-of-your-bugfix-or-feature

  #.  Change directory to flask_security::

        $ cd flask_security

  #.  Install the requirements::

        $ pip install -e .[tests]

  #. Develop the Feature/Bug Fix and edit

  #. Write Tests for your code in::

        tests/

  #. When done, verify unit tests, syntax etc. all pass::

        $ python setup.py tests
        $ python setup.py build_sphinx

  #. When the tests are successful, commit your changes
     and push your branch to GitHub::

        $ git add .
        $ git commit -m "Your detailed description of your changes."
        $ git push origin name-of-your-bugfix-or-feature

  #. Submit a pull request through the GitHub website.

  #. Be sure that the CI tests and coverage checks pass.


Testing
-------
Unit tests are critical since Flask-Security is a piece of middleware. They also
help other contributors understand any subtleties in the code and edge conditions that
need to be handled.

Datastore
+++++++++
By default the unit tests use an in-memory sqlite DB to test datastores (except for
MongoDatastore which uses mongomock). While this is sufficient for most changes, changes
to the datastore layer require testing against a real DB (the CI tests test against
postgres). It is easy to run the unit tests against a real DB instance. First
of course install the DB locally then::

  # For postgres
  python setup.py test --realdburl postgres://<user>@localhost/
  # For mysql
  python setup.py test --realdburl "mysql+pymysql://root:<password>@localhost/"

Views
+++++
Much of Flask-Security is concerned with form-based views. These can be difficult to test
especially translations etc. In the tests directory is a stand-alone Flask application
``view_scaffold.py`` that can be run and you can point your browser to it and walk
through the various views.
