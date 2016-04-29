#!/usr/bin/env python
#
# Copyright 2007-2013 The Python-Twitter Developers
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import webbrowser, request
from requests_oauthlib import OAuth1Session

#SIGNIN_URL = 'https://api.twitter.com/oauth/authenticate'


def get_access_token(consumer_key, consumer_secret):
    oauth_client = OAuth1Session(consumer_key, client_secret=consumer_secret, callback_uri='http://python.marcelin-da-cruz.fr/twitter/callback/')

    print('Requesting temp token from Twitter')

    try:
        resp = oauth_client.fetch_request_token('https://api.twitter.com/oauth/request_token')
    except ValueError as e:
        print('Invalid respond from Twitter requesting temp token: %s' % e)
        return False
    url = oauth_client.authorization_url('https://api.twitter.com/oauth/authorize')+'&oauth_callback=http://python.marcelin-da-cruz.fr/twitter/callback/'
    
    print(url)
    pincode = input('Pincode? ')

    print('')
    print('Generating and signing request for an access token')
    print('')

    oauth_client = OAuth1Session(consumer_key, client_secret=consumer_secret,
                                 resource_owner_key=resp.get('oauth_token'),
                                 resource_owner_secret=resp.get('oauth_token_secret'),
                                 verifier=pincode
    )
    try:
        resp = oauth_client.fetch_access_token('https://api.twitter.com/oauth/access_token')
    except ValueError as e:
        print('Invalid respond from Twitter requesting access token: %s' % e)
        return

    print('Your Twitter Access Token key: %s' % resp.get('oauth_token'))
    print('          Access Token secret: %s' % resp.get('oauth_token_secret'))
    print('')


def main():
    consumer_key = "JCJtzJaeIJ7Jl57TYni1Its2j"	#input('Enter your consumer key: ')
    consumer_secret = "ZBlc4iyzXxZwImy4GvUAfzEabwpgFPb7PzxYJegiJsnX5eci7m"	#input("Enter your consumer secret: ")
    get_access_token(consumer_key, consumer_secret)


if __name__ == "__main__":
    main()
