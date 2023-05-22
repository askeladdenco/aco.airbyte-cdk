#
# Copyright (c) 2022 Airbyte, Inc., all rights reserved.
#


from abc import ABC
from typing import Any, Iterable, List, Mapping, MutableMapping, Optional, Tuple

import requests
import pendulum
from airbyte_cdk.sources import AbstractSource
from airbyte_cdk.sources.streams import Stream
from airbyte_cdk.sources.streams.http import HttpStream
from airbyte_cdk.sources.streams.http.auth import TokenAuthenticator


def get_vendors() -> dict:
    vendors = {
        'vendors': [
            {
                'global_entity_id': 'FO_NO',
                'vendor_id': 'n7iy',
            },
            {
                'global_entity_id': 'FO_NO',
                'vendor_id': 'u5iq',
            },
            {
                'global_entity_id': 'FO_NO',
                'vendor_id': 'zp04',
            },
            {
                'global_entity_id': 'FO_NO',
                'vendor_id': 'pv2d',
            },
        ],
    }

    return vendors


class FoodoraStream(HttpStream, ABC):
    url_base = "https://vp-bff.api.eu.prd.portal.restaurant/vendors/v1/"

    def __init__(self, config: Mapping[str, Any], **kwargs):
        super().__init__()
        self.username = config.get("username")
        self.password = config.get("password")
        self.access_token = None
        self.update_access_token()

    def next_page_token(self, response: requests.Response) -> Optional[Mapping[str, Any]]:
        return None

    def request_kwargs(
            self,
            stream_state: Mapping[str, Any],
            stream_slice: Mapping[str, Any] = None,
            next_page_token: Mapping[str, Any] = None,
    ) -> Mapping[str, Any]:
        return {"verify": False}

    def update_access_token(self):
        response = requests.post(
            url=f"https://vp-bff.api.eu.prd.portal.restaurant/auth/v4/token",
            json={"username": self.username, "password": self.password},
        )
        self.access_token = response.json().get('accessToken')

    def request_headers(
            self, stream_state: Mapping[str, Any],
            stream_slice: Mapping[str, Any] = None,
            next_page_token: Mapping[str, Any] = None
    ) -> Mapping[str, Any]:
        return {"authorization": f"Bearer {self.access_token}"}

    def request_body_json(
            self, stream_state: Mapping[str, Any], stream_slice: Mapping[str, Any] = None, next_page_token: Mapping[str, Any] = None
    ) -> Mapping[str, Any]:
        return get_vendors()

    def request_params(
            self, stream_state: Mapping[str, Any], stream_slice: Mapping[str, any] = None, next_page_token: Mapping[str, Any] = None
    ) -> MutableMapping[str, Any]:
        return {}

    def parse_response(self, response: requests.Response, **kwargs) -> Iterable[Mapping]:
        yield from response.json().get("vendors", [])


class FoodoraStreamOrderDetails(HttpStream, ABC):
    state_checkpoint_interval = 1
    url_base = "https://os-backend.api.eu.prd.portal.restaurant/v1/"

    def __init__(self, config: Mapping[str, Any], **kwargs):
        super().__init__()
        self.username = config.get("username")
        self.password = config.get("password")
        self.start_date = config.get("initial_sync_date")
        self.access_token = None
        self.update_access_token()
        self.access_token_ts = pendulum.now()

        self.orders = None
        self.current_order = None

    @property
    def cursor_field(self) -> str:
        """
        Override to return the cursor field used by this stream e.g: an API entity might always use created_at as the cursor field. This is
        usually id or date based. This field's presence tells the framework this in an incremental stream. Required for incremental.

        :return str: The name of the cursor field.
        """

        return "identifier"

    def next_page_token(self, response: requests.Response) -> Optional[Mapping[str, Any]]:
        return self.current_order

    def update_access_token(self):
        response = requests.post(
            url=f"https://vp-bff.api.eu.prd.portal.restaurant/auth/v4/token",
            json={"username": self.username, "password": self.password},
        )
        self.access_token = response.json().get('accessToken')
        self.access_token_ts = pendulum.now()

    def request_headers(
            self, stream_state: Mapping[str, Any],
            stream_slice: Mapping[str, Any] = None,
            next_page_token: Mapping[str, Any] = None
    ) -> Mapping[str, Any]:
        if (pendulum.now() - self.access_token_ts).in_minutes() >= 10:
            self.update_access_token()

        return {"authorization": f"Bearer {self.access_token}"}

    def request_body_json(
            self, stream_state: Mapping[str, Any], stream_slice: Mapping[str, Any] = None, next_page_token: Mapping[str, Any] = None
    ) -> Mapping[str, Any]:
        return get_vendors()

    def get_updated_state(self, current_stream_state: MutableMapping[str, Any], latest_record: Mapping[str, Any]) -> Mapping[str, Any]:
        """
        Override to determine the latest state after reading the latest record. This typically compared the cursor_field from the latest record and
        the current state and picks the 'most' recent cursor. This is how a stream's state is determined. Required for incremental.
        """
        current_stream_value = pendulum.parse(current_stream_state.get("date", self.start_date))
        if self.current_order:
            latest_record_value = pendulum.parse(self.current_order.get("order_timestamp"))
            new_value = max(current_stream_value, latest_record_value)
        else:
            new_value = current_stream_value
        new_state = {"date": new_value.format("YYYY-MM-DDT00:00:00+00:00")}
        return new_state

    @staticmethod
    def generate_date_intervals(start_date: str, frequency=10):
        datetime_format = "YYYY-MM-DDT00:00:00+00:00"
        start = pendulum.parse(start_date)
        delta = pendulum.duration(days=frequency)
        now = pendulum.today().add(days=1)

        arr = []

        while start <= now:
            arr.append(
                (start.format(datetime_format), (start + delta).format(datetime_format))
            )
            start += delta

        return arr

    def get_orders(self, stream_state):
        vendors = get_vendors().get("vendors")
        global_vendor_codes = [f"{m.get('global_entity_id')};{m.get('vendor_id')}" for m in vendors]
        date_intervals = self.generate_date_intervals(stream_state.get("date", self.start_date))

        orders = []
        for time_from, time_to in date_intervals:
            resp = requests.post(
                url=f"{self.url_base}vendors/orders",
                json={
                    "global_vendor_codes": global_vendor_codes,
                    "time_from": time_from.format("YYYY-MM-DDT00:00:00+00:00"),
                    "time_to": time_to.format("YYYY-MM-DDT00:00:00+00:00"),
                },
                headers={"authorization": f"Bearer {self.access_token}"},
            )

            orders.extend(resp.json().get("orders", []))

        orders = sorted(orders, key=lambda x: x["order_timestamp"])
        self.orders = iter(orders)
        self.current_order = next(self.orders, None)

    def request_params(
            self, stream_state: Mapping[str, Any], stream_slice: Mapping[str, any] = None, next_page_token: Mapping[str, Any] = None
    ) -> MutableMapping[str, Any]:
        return {'order_timestamp': self.current_order.get('order_timestamp')}

    def parse_response(self, response: requests.Response, **kwargs) -> Iterable[Mapping]:
        self.current_order = next(self.orders, None)
        yield from [response.json().get("order", {})]


class OpeningHours(FoodoraStream):
    primary_key = 'vendor_id'

    def path(
            self, stream_state: Mapping[str, Any] = None, stream_slice: Mapping[str, Any] = None, next_page_token: Mapping[str, Any] = None
    ) -> str:
        return "vendors"

    @property
    def http_method(self) -> str:
        return "POST"


class OrderDetails(FoodoraStreamOrderDetails):
    primary_key = 'identifier'

    def path(
            self,
            stream_state: Mapping[str, Any] = None,
            stream_slice: Mapping[str, Any] = None,
            next_page_token: Mapping[str, Any] = None
    ) -> str:
        if self.orders is None:
            self.get_orders(stream_state)
        global_vendor_code = self.current_order.get('global_vendor_code')
        order_id = self.current_order.get('order_id')
        return f"vendors/{global_vendor_code}/orders/{order_id}"


class SourceFoodora(AbstractSource):
    def check_connection(self, logger, config) -> Tuple[bool, any]:
        """
        :param config:  the user-input config object conforming to the connector's spec.yaml
        :param logger:  logger object
        :return Tuple[bool, any]: (True, None) if the input config can be used to connect to the API successfully, (False, error) otherwise.
        """
        return True, None

    def streams(self, config: Mapping[str, Any]) -> List[Stream]:
        """
        :param config: A Mapping of the user input configuration as defined in the connector spec.
        """
        return [OpeningHours(config), OrderDetails(config)]
