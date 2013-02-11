import json
import locale
import functools

import requests

from .constants import *

class ApiException(Exception): pass
class ApiBadResponseException(ApiException): pass
class ApiError(ApiException): pass

class ApiInterface(object):
    """This will be the basis for the shared API interfaces once the Ajax and
    Web APIs have been implemented
    """
    pass

class AjaxApi(ApiInterface):
    """AJAX call API
    """
    pass

class WebApi(ApiInterface):
    """Screen scraping API
    """
    pass

def make_api_method(req_method, secure=True, version=0):
    def outer_func(func):
        def inner_func(self, **kwargs):
            req_url = self._build_request_url(secure, func.__name__, version)
            req_func = self._build_request(req_method, req_url, params=kwargs)
            response = req_func()
            func(self, response)
            return response
        return inner_func
    return outer_func

class AndroidApi(ApiInterface):
    """
    """

    METHOD_GET      = 'GET'
    METHOD_POST     = 'POST'

    def __init__(self, session_id=None, auth=None):
        self._connector = requests.Session()
        self._request_headers = {
            'X-Android-Device-Manufacturer':
                ANDROID_DEVICE_MANUFACTURER,
            'X-Android-Device-Model':
                ANDROID_DEVICE_MODEL,
            'X-Android-Device-Product':
                ANDROID_DEVICE_PRODUCT,
            'X-Android-Device-Is-GoogleTV': '0',
            'X-Android-SDK': ANDROID_SDK_VERSION,
            'X-Android-Release': ANDROID_RELEASE_VERSION,
            'X-Android-Application-Version-Code': ANDROID_APP_CODE,
            'X-Android-Application-Version-Name': ANDROID_APP_PACKAGE,
            'User-Agent': ANDROID_USER_AGENT,
        }
        self._state_params = {
            'session_id': session_id,
            'auth': auth,
            'user': None,
        }
        self._session_ops = []

    def _get_locale(self):
        return locale.getdefaultlocale()[0].replace('_', '').replace('-', '')

    def _get_base_params(self):
        base_params = {
            'locale':       self._get_locale(),
            'device_id':    ANDROID_DEVICE_ID,
            'device_type':  ANDROID_APP_PACKAGE,
            'access_token': CR_ACCESS_TOKEN,
            'version':      ANDROID_APP_CODE,
        }
        for key, value in self._state_params.iteritems():
            if value is not None:
                base_params[key] = value
        return base_params

    def _do_post_request_tasks(self, response_data):
        if 'ops' in response_data:
            try:
                self._session_ops.extend(response_data.get('ops', []))
            except AttributeError:
                # oops, wasn't a dict
                pass

    def _build_request(self, method, url, params=None):
        full_params = self._get_base_params()
        if params is not None:
            full_params.update(params)
        if method == self.METHOD_GET:
            request_func = lambda u, d: self._connector.get(u, params=d,
                headers=self._request_headers)
        elif method == self.METHOD_POST:
            request_func = lambda u, d: self._connector.post(u, data=d,
                headers=self._request_headers)
        else:
            raise Exception('Invalid request method')
        def do_request():
            resp = request_func(url, full_params)
            try:
                is_error = resp.json['error']
            except TypeError:
                raise ApiBadResponseException(resp.content)
            if is_error:
                raise ApiError('%s: %s' % (resp.json['code'], resp.json['message']))
            else:
                data = resp.json['data']
                self._do_post_request_tasks(data)
                return data
        return do_request

    def _build_request_url(self, secure, api_method, version):
        if secure:
            proto = CR_API_SECURE_PROTO
        else:
            proto = CR_API_INSECURE_PROTO
        req_url = CR_API_URL.format(
            protocol=proto,
            api_method=api_method,
            version=version
        )
        return req_url

    @make_api_method(METHOD_POST, False)
    def start_session(self, response):
        """
        This is the only method that doesn't go over HTTPS (for some reason). Must
        be called before anything else or you get an "unauthorized request" error.

        @param int duration
        """
        self._state_params['session_id'] = response['session_id']
        self._state_params['country_code'] = response['country_code']

    @make_api_method(METHOD_POST)
    def end_session(self, response):
        """
        Should probably be called after ``logout``
        """
        self._state_params['session_id'] = None

    @make_api_method(METHOD_POST)
    def login(self, response):
        """
        Login using email/username and password, used to get the auth token

        @param str account
        @param str password
        @param int duration
        """
        self._state_params['auth'] = response['auth']

    @make_api_method(METHOD_POST)
    def logout(self, response):
        """
        Auth param is not actually required, will be included with requests
        automatically after logging in

        @param str auth
        """
        self._state_params['auth'] = None

    @make_api_method(METHOD_POST)
    def authenticate(self, response):
        """
        This does not appear to be used, might refresh auth token though.

        @param str auth
        @param int duration
        """
        pass

    @make_api_method(METHOD_GET)
    def list_series(self, response):
        """
        Get the list of series, default limit seems to be 20.

        @param str media_type   one of CR_MEDIA_TYPE_*
        @param str filter       one of CR_SORT_*
        @param int offset       pick the index to start at, is not multiplied
                                    by limit or anything
        @param int limit        does not seem to have an upper bound
        """
        pass

    @make_api_method(METHOD_GET)
    def list_media(self, response):
        """
        Get the list of videos for a series

        @param int collection_id
        @param int series_id
        @param str sort
        @param int offset
        @param int limit
        """
        pass

    @make_api_method(METHOD_GET)
    def info(self, response):
        """
        Get info about a specific video

        @param int media_id
        @param int collection_id
        @param int series_id
        """
        pass

    @make_api_method(METHOD_POST)
    def add_to_queue(self, response):
        """
        @param int series_id
        """
        pass

    @make_api_method(METHOD_GET)
    def categories(self, response):
        """
        @param str media_type
        """
        pass

    @make_api_method(METHOD_GET)
    def queue(self, response):
        """
        @param str media_types
        """
        pass

    @make_api_method(METHOD_GET)
    def recently_watched(self, response):
        """
        @param str media_types
        @param int offset
        @param int limit
        """
        pass

    @make_api_method(METHOD_POST)
    def remove_from_queue(self, response):
        """
        @param int series_id
        """
        pass

    @make_api_method(METHOD_POST)
    def signup(self, response):
        """
        @param str email
        @param str password
        @param str username
        @param str first_name
        @param str last_name
        @param int duration
        """
        pass

    @make_api_method(METHOD_POST)
    def free_trial_start(self, response):
        """
        @param str sku
        @param str currency_code
        @param str first_name
        @param str last_name
        @param str cc
        @param str exp_month
        @param str exp_year
        @param str zip
        @param str address_1
        @param str address_2
        @param str city
        @param str state
        @param str country_code
        """
        pass

    @make_api_method(METHOD_POST)
    def forgot_password(self, response):
        """
        @param str email
        """
        pass

    @make_api_method(METHOD_GET)
    def free_trial_info(self, response):
        """
        """
        pass

    @make_api_method(METHOD_GET)
    def list_ads(self, response):
        """
        @param int media_id
        """
        pass

    @make_api_method(METHOD_POST)
    def log_ad_requested(self, response):
        """
        @param str ad_network
        """
        pass

    @make_api_method(METHOD_POST)
    def log_ad_served(self, response):
        """
        @param str ad_network
        """
        pass

    @make_api_method(METHOD_POST)
    def log_first_launch(self, response):
        """
        """
        pass

    @make_api_method(METHOD_POST)
    def log_impression(self, response):
        """
        @param str view
        """
        pass

    @make_api_method(METHOD_POST)
    def log_install_referrer(self, response):
        """
        @param str referrer
        """
        pass

    @make_api_method(METHOD_POST)
    def log(self, response):
        """
        @param str event
        @param int media_id
        @param int playhead
        @param int elapsed
        @param int elapsed_delta
        @param int video_id
        @param int video_encode_id
        """
        pass
