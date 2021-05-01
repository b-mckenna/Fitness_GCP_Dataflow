import datetime
import json
import requests

try:
    from urllib.parse import urlencode
except ImportError:
    # Python 2.x
    from urllib import urlencode

from requests.auth import HTTPBasicAuth
from requests_oauthlib import OAuth2Session

from . import exceptions
from .compliance import fitbit_compliance_fix
from .utils import curry


class FitbitOauth2Client(object):
    API_ENDPOINT = "https://api.fitbit.com"
    AUTHORIZE_ENDPOINT = "https://www.fitbit.com"
    API_VERSION = 1

    request_token_url = "%s/oauth2/token" % API_ENDPOINT
    authorization_url = "%s/oauth2/authorize" % AUTHORIZE_ENDPOINT
    access_token_url = request_token_url
    refresh_token_url = request_token_url

    def __init__(self, client_id, client_secret, access_token=None,
            refresh_token=None, expires_at=None, refresh_cb=None,
            redirect_uri=None, *args, **kwargs):
        """
        Create a FitbitOauth2Client object. Specify the first 7 parameters if
        you have them to access user data. Specify just the first 2 parameters
        to start the setup for user authorization (as an example see gather_key_oauth2.py)
            - client_id, client_secret are in the app configuration page
            https://dev.fitbit.com/apps
            - access_token, refresh_token are obtained after the user grants permission
        """

        self.client_id, self.client_secret = client_id, client_secret
        token = {}
        if access_token and refresh_token:
            token.update({
                'access_token': access_token,
                'refresh_token': refresh_token
            })
        if expires_at:
            token['expires_at'] = expires_at
        self.session = fitbit_compliance_fix(OAuth2Session(
            client_id,
            auto_refresh_url=self.refresh_token_url,
            token_updater=refresh_cb,
            token=token,
            redirect_uri=redirect_uri,
        ))
        self.timeout = kwargs.get("timeout", None)

    def _request(self, method, url, **kwargs):
        """
        A simple wrapper around requests.
        """
        if self.timeout is not None and 'timeout' not in kwargs:
            kwargs['timeout'] = self.timeout

        try:
            response = self.session.request(method, url, **kwargs)

            # If our current token has no expires_at, or something manages to slip
            # through that check
            if response.status_code == 401:
                d = json.loads(response.content.decode('utf8'))
                if d['errors'][0]['errorType'] == 'expired_token':
                    self.refresh_token()
                    response = self.session.request(method, url, **kwargs)

            return response
        except requests.Timeout as e:
            raise exceptions.Timeout(*e.args)

    def make_request(self, url, data=None, method=None, **kwargs):
        """
        Builds and makes the OAuth2 Request, catches errors
        https://dev.fitbit.com/docs/oauth2/#authorization-errors
        """
        data = data or {}
        method = method or ('POST' if data else 'GET')
        response = self._request(
            method,
            url,
            data=data,
            client_id=self.client_id,
            client_secret=self.client_secret,
            **kwargs
        )

        exceptions.detect_and_raise_error(response)

        return response

    def authorize_token_url(self, scope=None, redirect_uri=None, **kwargs):
        """Step 1: Return the URL the user needs to go to in order to grant us
        authorization to look at their data.  Then redirect the user to that
        URL, open their browser to it, or tell them to copy the URL into their
        browser.
            - scope: pemissions that that are being requested [default ask all]
            - redirect_uri: url to which the response will posted. required here
              unless you specify only one Callback URL on the fitbit app or
              you already passed it to the constructor
            for more info see https://dev.fitbit.com/docs/oauth2/
        """

        self.session.scope = scope or [
            "activity",
            "nutrition",
            "heartrate",
            "location",
            "nutrition",
            "profile",
            "settings",
            "sleep",
            "social",
            "weight",
        ]

        if redirect_uri:
            self.session.redirect_uri = redirect_uri

        return self.session.authorization_url(self.authorization_url, **kwargs)

    def fetch_access_token(self, code, redirect_uri=None):

        """Step 2: Given the code from fitbit from step 1, call
        fitbit again and returns an access token object. Extract the needed
        information from that and save it to use in future API calls.
        the token is internally saved
        """
        if redirect_uri:
            self.session.redirect_uri = redirect_uri
        return self.session.fetch_token(
            self.access_token_url,
            username=self.client_id,
            password=self.client_secret,
            code=code)

    def refresh_token(self):
        """Step 3: obtains a new access_token from the the refresh token
        obtained in step 2. Only do the refresh if there is `token_updater(),`
        which saves the token.
        """
        token = {}
        if self.session.token_updater:
            token = self.session.refresh_token(
                self.refresh_token_url,
                auth=HTTPBasicAuth(self.client_id, self.client_secret)
            )
            self.session.token_updater(token)

        return token


class Fitbit(object):
    """
    Before using this class, create a Fitbit app
    `here <https://dev.fitbit.com/apps/new>`_. There you will get the client id
    and secret needed to instantiate this class. When first authorizing a user,
    make sure to pass the `redirect_uri` keyword arg so fitbit will know where
    to return to when the authorization is complete. See
    `gather_keys_oauth2.py <https://github.com/orcasgit/python-fitbit/blob/master/gather_keys_oauth2.py>`_
    for a reference implementation of the authorization process. You should
    save ``access_token``, ``refresh_token``, and ``expires_at`` from the
    returned token for each user you authorize.
    When instantiating this class for use with an already authorized user, pass
    in the ``access_token``, ``refresh_token``, and ``expires_at`` keyword
    arguments. We also strongly recommend passing in a ``refresh_cb`` keyword
    argument, which should be a function taking one argument: a token dict.
    When that argument is present, we will automatically refresh the access
    token when needed and call this function so that you can save the updated
    token data. If you don't save the updated information, then you could end
    up with invalid access and refresh tokens, and the only way to recover from
    that is to reauthorize the user.
    """
    US = 'en_US'
    METRIC = 'en_UK'

    API_ENDPOINT = "https://api.fitbit.com"
    API_VERSION = 1
    WEEK_DAYS = ['SUNDAY', 'MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY']
    PERIODS = ['1d', '7d', '30d', '1w', '1m', '3m', '6m', '1y', 'max']

    RESOURCE_LIST = [
        'body',
        'activities',
        'foods/log',
        'foods/log/water',
        'sleep',
        'heart',
        'bp',
        'glucose',
    ]

    QUALIFIERS = [
        'recent',
        'favorite',
        'frequent',
    ]

    def __init__(self, client_id, client_secret, access_token=None,
            refresh_token=None, expires_at=None, refresh_cb=None,
            redirect_uri=None, system=US, **kwargs):
        """
        Fitbit(<id>, <secret>, access_token=<token>, refresh_token=<token>)
        """
        self.system = system
        self.client = FitbitOauth2Client(
            client_id,
            client_secret,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            refresh_cb=refresh_cb,
            redirect_uri=redirect_uri,
            **kwargs
        )

        # All of these use the same patterns, define the method for accessing
        # creating and deleting records once, and use curry to make individual
        # Methods for each
        for resource in Fitbit.RESOURCE_LIST:
            underscore_resource = resource.replace('/', '_')
            setattr(self, underscore_resource,
                    curry(self._COLLECTION_RESOURCE, resource))

            if resource not in ['body', 'glucose']:
                # Body and Glucose entries are not currently able to be deleted
                setattr(self, 'delete_%s' % underscore_resource, curry(
                    self._DELETE_COLLECTION_RESOURCE, resource))

        for qualifier in Fitbit.QUALIFIERS:
            setattr(self, '%s_activities' % qualifier, curry(self.activity_stats, qualifier=qualifier))
            setattr(self, '%s_foods' % qualifier, curry(self._food_stats,
                                                        qualifier=qualifier))

    def make_request(self, *args, **kwargs):
        # This should handle data level errors, improper requests, and bad
        # serialization
        headers = kwargs.get('headers', {})
        headers.update({'Accept-Language': self.system})
        kwargs['headers'] = headers

        method = kwargs.get('method', 'POST' if 'data' in kwargs else 'GET')
        response = self.client.make_request(*args, **kwargs)

        if response.status_code == 202:
            return True
        if method == 'DELETE':
            if response.status_code == 204:
                return True
            else:
                raise exceptions.DeleteError(response)
        try:
            rep = json.loads(response.content.decode('utf8'))
        except ValueError:
            raise exceptions.BadResponse

        return rep

    def user_profile_get(self, user_id=None):
        """
        Get a user profile. You can get other user's profile information
        by passing user_id, or you can get the current user's by not passing
        a user_id
        .. note:
            This is not the same format that the GET comes back in, GET requests
            are wrapped in {'user': <dict of user data>}
        https://dev.fitbit.com/docs/user/
        """
        url = "{0}/{1}/user/{2}/profile.json".format(*self._get_common_args(user_id))
        return self.make_request(url)