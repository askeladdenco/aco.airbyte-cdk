#
# Copyright (c) 2022 Airbyte, Inc., all rights reserved.
#


from abc import ABC
from typing import Any, Iterable, List, Mapping, MutableMapping, Optional, Tuple

import requests
from airbyte_cdk.sources import AbstractSource
from airbyte_cdk.sources.streams import Stream
from airbyte_cdk.sources.streams.http import HttpStream
from airbyte_cdk.sources.streams.http.auth import TokenAuthenticator


class FoodoraStream(HttpStream, ABC):
    url_base = "https://vp-bff.api.eu.prd.portal.restaurant/vendors/v1/"

    def __init__(self, config: Mapping[str, Any], **kwargs):
        super().__init__()
        self.username = config.get("username")
        self.password = config.get("password")
        self.token_url = 'https://vp-bff.api.eu.prd.portal.restaurant/auth/v4/token'

    def next_page_token(self, response: requests.Response) -> Optional[Mapping[str, Any]]:
        return None
        

    def get_vendors(self) -> dict:
        response = requests.post(self.token_url, json={
            "username": self.username, "password": self.password}, verify=False)

        vendors = response.json().get("accessTokenContent", {}).get(
            "vendors", {}).get("FO_NO", {}).get("codes")

        vendors_list = [
            {
                'global_entity_id': 'FO_NO',
                'vendor_id': vendor_id,
            } for vendor_id in vendors
        ]

        return {'vendors': vendors_list}

    def request_kwargs(
            self,
            stream_state: Mapping[str, Any],
            stream_slice: Mapping[str, Any] = None,
            next_page_token: Mapping[str, Any] = None,
    ) -> Mapping[str, Any]:
        return {"verify": False}

    def request_headers(
            self, stream_state: Mapping[str, Any], stream_slice: Mapping[str, Any] = None, next_page_token: Mapping[str, Any] = None
    ) -> Mapping[str, Any]:
        token_url = f"https://vp-bff.api.eu.prd.portal.restaurant/auth/v4/token"

        response = requests.post(token_url, json={
                                 "username": self.username, "password": self.password}, verify=False)
        return {"authorization": f"Bearer {response.json().get('accessToken')}"}

    def request_body_json(
            self, stream_state: Mapping[str, Any], stream_slice: Mapping[str, Any] = None, next_page_token: Mapping[str, Any] = None
    ) -> Mapping[str, Any]:

        vendors = self.get_vendors()
        return vendors

    def request_params(
        self, stream_state: Mapping[str, Any], stream_slice: Mapping[str, any] = None, next_page_token: Mapping[str, Any] = None
    ) -> MutableMapping[str, Any]:
        return {}

    def parse_response(self, response: requests.Response, **kwargs) -> Iterable[Mapping]:
        yield from response.json().get("vendors", [])


class OpeningHours(FoodoraStream):
    primary_key = 'vendor_id'

    def path(
        self, stream_state: Mapping[str, Any] = None, stream_slice: Mapping[str, Any] = None, next_page_token: Mapping[str, Any] = None
    ) -> str:
        return "vendors"

    @property
    def http_method(self) -> str:
        return "POST"


class SourceFoodora(AbstractSource):

    def check_connection(self, logger, config) -> Tuple[bool, any]:
        """
        :param config:  the user-input config object conforming to the connector's spec.yaml
        :param logger:  logger object
        :return Tuple[bool, any]: (True, vendors) if vendors exist in the response, (False, error) otherwise.
        """

        token_url = "https://vp-bff.api.eu.prd.portal.restaurant/auth/v4/token"

        # Using the try-except block to catch potential issues with the request
        try:
            response = requests.post(token_url, json={
                "username": config.get('username'), "password": config.get('password')}, verify=False)

            vendors = response.json().get("accessTokenContent", {}).get(
                "vendors", {}).get("FO_NO", {}).get("codes")

            config['vendors'] = vendors

            if vendors:
                return True, None
            else:
                return False, "Vendors not found in the response."

        except Exception as e:
            logger.error(f"An error occurred: {e}")
            return False, f"Failed to check connection: {e}"

    def streams(self, config: Mapping[str, Any]) -> List[Stream]:
        """
        :param config: A Mapping of the user input configuration as defined in the connector spec.
        """

        return [OpeningHours(config)]
