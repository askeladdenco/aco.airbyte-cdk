#
# Copyright (c) 2023 Airbyte, Inc., all rights reserved.
#


from abc import ABC
from typing import Any, Iterable, List, Mapping, MutableMapping, Optional, Tuple

import requests
from airbyte_cdk.sources import AbstractSource
from airbyte_cdk.sources.streams import Stream
from airbyte_cdk.sources.streams.http import HttpStream
from airbyte_cdk.models import SyncMode
from airbyte_cdk.sources.streams.http.auth import TokenAuthenticator

from airbyte_cdk.sources.streams.http.requests_native_auth import Oauth2Authenticator


"""
TODO: Most comments in this class are instructive and should be deleted after the source is implemented.

This file provides a stubbed example of how to use the Airbyte CDK to develop both a source connector which supports full refresh or and an
incremental syncs from an HTTP API.

The various TODOs are both implementation hints and steps - fulfilling all the TODOs should be sufficient to implement one basic and one incremental
stream from a source. This pattern is the same one used by Airbyte internally to implement connectors.

The approach here is not authoritative, and devs are free to use their own judgement.

There are additional required TODOs in the files within the integration_tests folder and the spec.yaml file.
"""


# Basic full refresh stream
class FoodoraPartnerStream(HttpStream, ABC):
    """
    """

    # TODO: Fill in the url base. Required.
    url_base = "https://integration-middleware.eu.restaurant-partners.com/v2/chains/DiggPizza_NO/"

    def __init__(self, config: Mapping[str, Any]):
        super().__init__(authenticator=config.get("authenticator"))
        self.config = config

    def next_page_token(self, response: requests.Response) -> Optional[Mapping[str, Any]]:

        return None

    def parse_response(self, response: requests.Response, **kwargs) -> Iterable[Mapping]:
        """
        TODO: Override this method to define how a response is parsed.
        :return an iterable containing each record in the response
        """
        yield from response.json()


class Orders(FoodoraPartnerStream):
    """
    TODO: Change class name to match the table/data source this stream corresponds to.
    """

    # TODO: Fill in the primary key. Required. This is usually a unique field in the stream, like an ID or a timestamp.
    primary_key = "id"

    def parse_response(self, response: requests.Response, **kwargs) -> Iterable[Mapping]:
        """
        TODO: Override this method to define how a response is parsed.
        :return an iterable containing each record in the response
        """
        orders = response.json().get('orders', [])

        yield from [{"id": order} for order in orders]

    def path(
        self, stream_state: Mapping[str, Any] = None, stream_slice: Mapping[str, Any] = None, next_page_token: Mapping[str, Any] = None
    ) -> str:

        return "orders/ids?status=accepted"


class OrderDetails(FoodoraPartnerStream):
    """
    TODO: Change class name to match the table/data source this stream corresponds to.
    """

    primary_key = "token"

    def __init__(self, parent: Stream, config: Mapping[str, Any]):
        super().__init__(config)
        self.parent = parent

    def parse_response(self, response: requests.Response, **kwargs) -> Iterable[Mapping]:
        """
        TODO: Override this method to define how a response is parsed.
        :return an iterable containing each record in the response
        """
        orders = response.json().get('order', {})

        yield from [orders]

    def stream_slices(self, stream_state: Mapping[str, Any] = None, **kwargs) -> Iterable[Optional[Mapping[str, any]]]:

        orders_stream_data = self.parent.read_records(
            sync_mode=SyncMode.full_refresh)

        slices = []
        for order in orders_stream_data:

            slices.append({
                "id": order.get('id'),
            })
        return slices

    def path(
        self, stream_state: Mapping[str, Any] = None, stream_slice: Mapping[str, Any] = None, next_page_token: Mapping[str, Any] = None
    ) -> str:
        """
        TODO: Override this method to define the path this stream corresponds to. E.g. if the url is https://example-api.com/v1/customers then this
        should return "customers". Required.
        """
        order_id = stream_slice["id"]
        return f"orders/{order_id}"


# Source
class SourceFoodoraPartner(AbstractSource):

    def check_connection(self, logger, config) -> Tuple[bool, any]:

        config["authenticator"] = FoodoraAuthenticator(
            url="https://integration-middleware.eu.restaurant-partners.com/v2/login",
            username=config['username'],
            password=config['password'],
        )

        stream = Orders(config)
        stream.records_limit = 1
        try:
            next(stream.read_records(sync_mode=SyncMode.full_refresh), None)
            return True, None
        except Exception as e:
            return False, e

    def streams(self, config: Mapping[str, Any]) -> List[Stream]:

        config["authenticator"] = FoodoraAuthenticator(
            url="https://integration-middleware.eu.restaurant-partners.com/v2/login",
            username=config['username'],
            password=config['password'],
        )
        return [Orders(config), OrderDetails(parent=Orders(config), config=config)]


class FoodoraAuthenticator():

    def __init__(
        self,
        url: str,
        username: str,
        password: str,
    ):
        self.url = url
        self.username = username
        self.password = password

    def get_auth_header(self) -> Mapping[str, Any]:

        payload = f'username={self.username}&password={self.password}&grant_type=client_credentials'
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        response = requests.request(
            "POST", self.url, headers=headers, data=payload)

        if response.status_code != 200:
            raise Exception("Authentication failed")

        return {"Authorization": f"Bearer {response.json()['access_token']}"}
