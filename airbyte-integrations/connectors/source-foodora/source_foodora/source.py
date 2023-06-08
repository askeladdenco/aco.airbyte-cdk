#
# Copyright (c) 2022 Airbyte, Inc., all rights reserved.
#


from abc import ABC, abstractmethod
from typing import Any, Iterable, List, Mapping, MutableMapping, Optional, Tuple

import requests
import pendulum
from airbyte_cdk.sources import AbstractSource
from airbyte_cdk.sources.streams import Stream
from airbyte_cdk.sources.streams.http import HttpStream, HttpSubStream
from airbyte_cdk.sources.streams.http.auth import TokenAuthenticator
from airbyte_cdk.models import SyncMode


def get_vendors() -> list:
    vendors = [
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
    ]

    return vendors


class FoodoraStream(HttpStream, ABC):

    auth_url = "https://vp-bff.api.eu.prd.portal.restaurant/auth/v4/token"

    def __init__(self, config: Mapping[str, Any], **kwargs):
        super().__init__()
        self.username = config.get("username")
        self.password = config.get("password")
        self.start_date = config.get("initial_sync_date")
        self.vendors = get_vendors()
        self.access_token = None
        self.access_token_exp = pendulum.now()

        # TODO: Remove this
        self.num_orders = 0

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
            url=FoodoraStream.auth_url,
            json={"username": self.username, "password": self.password},
        )
        resp_json = response.json()
        self.access_token = resp_json.get('accessToken')
        self.access_token_exp = pendulum.from_timestamp(
            resp_json.get("accessTokenContent", {}).get("exp", 0))

    def request_headers(
            self, stream_state: Mapping[str, Any], stream_slice: Mapping[str, Any] = None, next_page_token: Mapping[str, Any] = None
    ) -> Mapping[str, Any]:
        if not self.access_token or self.access_token_exp < pendulum.now():
            self.update_access_token()
        return {"authorization": f"Bearer {self.access_token}"}

    def request_params(
        self, stream_state: Mapping[str, Any], stream_slice: Mapping[str, any] = None, next_page_token: Mapping[str, Any] = None
    ) -> MutableMapping[str, Any]:
        return {}

    @property
    def http_method(self) -> str:
        return "POST"

    @abstractmethod
    def request_body_json(
            self, stream_state: Mapping[str, Any], stream_slice: Mapping[str, Any] = None, next_page_token: Mapping[str, Any] = None
    ) -> Mapping[str, Any]:
        pass


class FoodoraOrdersStream(FoodoraStream, ABC):
    primary_key = "orderId"
    url_base = "https://vagw-api.eu.prd.portal.restaurant/query"

    def path(
        self, stream_state: Mapping[str, Any] = None, stream_slice: Mapping[str, Any] = None, next_page_token: Mapping[str, Any] = None
    ) -> str:
        return ""


class OpeningHours(FoodoraStream):
    primary_key = 'vendor_id'
    url_base = "https://vp-bff.api.eu.prd.portal.restaurant/vendors/v1/"

    def path(
        self, stream_state: Mapping[str, Any] = None, stream_slice: Mapping[str, Any] = None, next_page_token: Mapping[str, Any] = None
    ) -> str:
        return "vendors"

    def request_body_json(
            self, stream_state: Mapping[str, Any], stream_slice: Mapping[str, Any] = None, next_page_token: Mapping[str, Any] = None
    ) -> Mapping[str, Any]:
        return {"vendors": self.vendors}

    def parse_response(self, response: requests.Response, **kwargs) -> Iterable[Mapping]:
        yield from response.json().get("vendors", [])


class Orders(FoodoraOrdersStream):

    @property
    def use_cache(self) -> bool:
        return True

    def request_body_json(
            self, stream_state: Mapping[str, Any], stream_slice: Mapping[str, Any] = None, next_page_token: Mapping[str, Any] = None
    ) -> Mapping[str, Any]:
        print("Next page token", next_page_token)
        vendors = get_vendors()
        query = "query ListOrders($params: ListOrdersReq!) {\n  orders {\n    listOrders(input: $params) {\n      nextPageToken\n      resultTimestamp\n      orders {\n        ...OrderListingFields\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n}\n\nfragment OrderListingFields on OrderSummary {\n  orderId\n  globalEntityId\n  vendorId\n  vendorName\n  orderStatus\n  placedTimestamp\n  subtotal\n  billing {\n    commissionAmount\n    customerRefundGrossAmount\n    netRevenue\n    __typename\n  }\n  __typename\n}"
        pagination = {"pageSize": 50}
        if next_page_token:
            pagination.update({"pageToken": next_page_token})
        return {"operationName": "ListOrders",
                "variables": {"params":
                              {"pagination": pagination, "timeFrom": str(stream_slice.get("from")), "timeTo": str(stream_slice.get("to")), "globalVendorCodes": [{"globalEntityId": "FO_NO", "vendorId": "n7iy"}, {"globalEntityId": "FO_NO", "vendorId": "u5iq"}, {"globalEntityId": "FO_NO", "vendorId": "zp04"}, {"globalEntityId": "FO_NO", "vendorId": "pv2d"}]}},
                "query": query}

    def stream_slices(
        self, *, sync_mode: SyncMode, cursor_field: List[str] = None, stream_state: Mapping[str, Any] = None
    ) -> Iterable[Optional[Mapping[str, Any]]]:
        for start, end in self.generate_date_intervals(self.start_date):
            yield {"from": start, "to": end}

    def parse_response(self, response: requests.Response, **kwargs) -> Iterable[Mapping]:
        print(response.url)
        data = response.json().get("data", {}).get("orders", {})
        if not data:
            orders = []
        else:
            orders = data.get("listOrders", {}).get("orders", [])
        print(orders)
        self.num_orders += len(orders)
        print(f"Num orders: {self.num_orders}")
        yield from orders

    def next_page_token(self, response: requests.Response) -> Optional[Mapping[str, Any]]:

        data = response.json().get("data", {}).get(
            "orders", {})
        if data is None:
            return None
        next_page_token = data.get("listOrders", {}).get("nextPageToken")
        return next_page_token if next_page_token else None

    @staticmethod
    def generate_date_intervals(start_date: str, frequency=10):
        start = pendulum.parse(start_date)
        delta = pendulum.duration(days=frequency)
        stop = pendulum.today().add(days=1)

        while start < stop:
            stop = min(start + delta, stop)
            yield start, stop
            start = stop


class OrderDetails(HttpSubStream, FoodoraOrdersStream):

    def __init__(self, parent: Orders, config: Mapping[str, Any]):
        super().__init__(parent=parent, config=config)

    def request_body_json(
            self, stream_state: Mapping[str, Any], stream_slice: Mapping[str, Any] = None, next_page_token: Mapping[str, Any] = None
    ) -> Mapping[str, Any]:
        print("Next page token", next_page_token)
        print("Stream slice", stream_slice)
        vendors = get_vendors()
        query = "query GetOrderDetails($params: OrderReq!) {\n  orders {\n    order(input: $params) {\n      order {\n        orderId\n        placedTimestamp\n        status\n        globalEntityId\n        vendorId\n        vendorName\n        orderValue\n        billableStatus\n        delivery {\n          provider\n          location {\n            AddressText\n            city\n            district\n            postCode\n            __typename\n          }\n          __typename\n        }\n        items {\n          ...ItemFields\n          __typename\n        }\n        __typename\n      }\n      orderReceipt {\n        uploadedAt\n        __typename\n      }\n      orderStatuses {\n        status\n        timestamp\n        detail {\n          ... on Accepted {\n            estimatedDeliveryTime\n            __typename\n          }\n          ... on Cancelled {\n            owner\n            reason\n            __typename\n          }\n          ... on Delivered {\n            timestamp\n            __typename\n          }\n          __typename\n        }\n        __typename\n      }\n      billing {\n        billingStatus\n        estimatedVendorNetRevenue\n        taxTotalAmount\n        vendorPayout\n        payment {\n          cashAmountCollectedByVendor\n          paymentType\n          method\n          paymentFee\n          __typename\n        }\n        expense {\n          totalDiscountGross\n          jokerFeeGross\n          commissions {\n            grossAmount\n            rate\n            base\n            __typename\n          }\n          vendorCharges {\n            grossAmount\n            reason\n            __typename\n          }\n          __typename\n        }\n        revenue {\n          platformFundedDiscountGross\n          partnerFundedDiscountGross\n          containerChargesGross\n          minimumOrderValueGross\n          deliveryFeeGross\n          tipGross\n          taxCharge\n          vendorRefunds {\n            grossAmount\n            reason\n            __typename\n          }\n          __typename\n        }\n        __typename\n      }\n      previousVersions {\n        changeAt\n        reason\n        orderState {\n          orderValue\n          items {\n            ...ItemFields\n            __typename\n          }\n          __typename\n        }\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n}\n\nfragment ItemFields on Item {\n  id: productId\n  name\n  parentName\n  quantity\n  unitPrice\n  options {\n    id\n    name\n    quantity\n    type\n    unitPrice\n    __typename\n  }\n  __typename\n}"
        pagination = {"pageSize": 50}
        if next_page_token:
            pagination.update({"pageToken": next_page_token})
        return {"operationName": "GetOrderDetails",
                "variables": {
                    "params": {"orderId": "u5iq-4e4g",
                               "GlobalVendorCode":
                                   {"globalEntityId": "FO_NO", "vendorId": "u5iq"},
                                   "placedTimestamp": "2023-06-06T09:20:52.000Z", "isBillingDataFlagEnabled": False}},
                "query": query}

    def stream_slices(
        self, *, sync_mode: SyncMode, cursor_field: List[str] = None, stream_state: Mapping[str, Any] = None
    ) -> Iterable[Optional[Mapping[str, Any]]]:
        for start, end in self.generate_date_intervals(self.start_date):
            yield {"from": start, "to": end}

    def parse_response(self, response: requests.Response, **kwargs) -> Iterable[Mapping]:
        print(response.url)
        data = response.json().get("data", {}).get("orders", {})
        if not data:
            orders = []
        else:
            orders = data.get("listOrders", {}).get("orders", [])
        print(orders)
        self.num_orders += len(orders)
        print(f"Num orders: {self.num_orders}")
        yield from orders

    def next_page_token(self, response: requests.Response) -> Optional[Mapping[str, Any]]:

        data = response.json().get("data", {}).get(
            "orders", {})
        if data is None:
            return None
        next_page_token = data.get("listOrders", {}).get("nextPageToken")
        return next_page_token if next_page_token else None

    @staticmethod
    def generate_date_intervals(start_date: str, frequency=10):
        start = pendulum.parse(start_date)
        delta = pendulum.duration(days=frequency)
        stop = pendulum.today().add(days=1)

        while start < stop:
            stop = min(start + delta, stop)
            yield start, stop
            start = stop


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
        orders = Orders(config)
        return [OpeningHours(config), orders, OrderDetails(parent=orders, config=config)]
