API
===

The external (json/form) API is described `here`_

.. _here: _static/openapi_view.html


Core
----
.. autoclass:: flask_security.Security
    :members:

.. data:: flask_security.current_user

   A proxy for the current user.

.. function:: flask_security.Security.unauthorized_handler

    If an endpoint fails authentication or authorization from one of the decorators
    described below
    (except ``login_required``), a method annotated with this decorator will be called.
    For ``login_required`` (which is implemented in Flask-Login) use
    **flask_security.login_manager.unauthorized_handler**

    .. deprecated:: 3.3.0

Protecting Views
----------------
.. autofunction:: flask_security.anonymous_user_required

.. autofunction:: flask_security.http_auth_required

.. autofunction:: flask_security.auth_token_required

.. autofunction:: flask_security.auth_required

.. autofunction:: flask_security.login_required

.. autofunction:: flask_security.roles_required

.. autofunction:: flask_security.roles_accepted

.. autofunction:: flask_security.permissions_required

.. autofunction:: flask_security.permissions_accepted

.. autofunction:: flask_security.unauth_csrf

.. autofunction:: flask_security.handle_csrf

User Object Helpers
-------------------
.. autoclass:: flask_security.UserMixin
   :members:

.. autoclass:: flask_security.RoleMixin
   :members:

.. autoclass:: flask_security.AnonymousUser
   :members:


Datastores
----------
.. autoclass:: flask_security.UserDatastore
    :members:

.. autoclass:: flask_security.SQLAlchemyUserDatastore
    :members:
    :inherited-members:

.. autoclass:: flask_security.SQLAlchemySessionUserDatastore
    :members:
    :inherited-members:

.. autoclass:: flask_security.MongoEngineUserDatastore
    :members:
    :inherited-members:

.. autoclass:: flask_security.PeeweeUserDatastore
    :members:
    :inherited-members:

.. autoclass:: flask_security.PonyUserDatastore
    :members:
    :inherited-members:

Utils
-----
.. autofunction:: flask_security.login_user

.. autofunction:: flask_security.logout_user

.. autofunction:: flask_security.get_hmac

.. autofunction:: flask_security.verify_password

.. autofunction:: flask_security.verify_and_update_password

.. autofunction:: flask_security.hash_password

.. autofunction:: flask_security.url_for_security

.. autofunction:: flask_security.send_mail

.. autofunction:: flask_security.get_token_status

.. autofunction:: flask_security.get_url

.. autofunction:: flask_security.transform_url

.. autoclass:: flask_security.FsJsonEncoder

.. autoclass:: flask_security.SmsSenderBaseClass
  :members: send_sms

.. autoclass:: flask_security.SmsSenderFactory
  :members: createSender

Signals
-------
See the `Flask documentation on signals`_ for information on how to use these
signals in your code.

See the documentation for the signals provided by the Flask-Login and
Flask-Principal extensions. In addition to those signals, Flask-Security
sends the following signals.

.. data:: user_registered

   Sent when a user registers on the site. In addition to the app (which is the
   sender), it is passed `user` and `confirm_token` arguments.

.. data:: user_confirmed

   Sent when a user is confirmed. In addition to the app (which is the
   sender), it is passed a `user` argument.

.. data:: confirm_instructions_sent

   Sent when a user requests confirmation instructions. In addition to the app
   (which is the sender), it is passed a `user` argument.

.. data:: login_instructions_sent

   Sent when passwordless login is used and user logs in. In addition to the app
   (which is the sender), it is passed `user` and `login_token` arguments.

.. data:: password_reset

   Sent when a user completes a password reset. In addition to the app (which is
   the sender), it is passed a `user` argument.

.. data:: password_changed

   Sent when a user completes a password change. In addition to the app (which is
   the sender), it is passed a `user` argument.

.. data:: reset_password_instructions_sent

   Sent when a user requests a password reset. In addition to the app (which is
   the sender), it is passed `user` and `token` arguments.

.. data:: tf_code_confirmed

    Sent when a user performs two-factor authentication login on the site. In
    addition to the app (which is the sender), it is passed `user`
    and `method` arguments.

.. data:: tf_profile_changed

  Sent when two-factor is used and user logs in. In addition to the app
  (which is the sender), it is passed `user` and `method` arguments.

.. data:: tf_disabled

  Sent when two-factor is disabled. In addition to the app
  (which is the sender), it is passed `user` argument.

.. data:: tf_security_token_sent

  Sent when a two factor security/access code is sent. In addition to the app
  (which is the sender), it is passed `user`, `method`, and `token` arguments.

.. _Flask documentation on signals: http://flask.pocoo.org/docs/signals/
