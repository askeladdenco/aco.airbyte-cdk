#
# Copyright (c) 2023 Airbyte, Inc., all rights reserved.
#


from abc import ABC
from typing import Any, Iterable, List, Mapping, MutableMapping, Optional, Tuple
from datetime import timedelta
import requests
from airbyte_cdk.sources import AbstractSource
from airbyte_cdk.sources.streams import Stream
from airbyte_cdk.sources.streams.http import HttpStream
from airbyte_cdk.models import SyncMode
from airbyte_cdk.sources.streams.http.auth import Oauth2Authenticator
from airbyte_cdk import AirbyteLogger
import pendulum

logger = AirbyteLogger()


class WoltStream(HttpStream, ABC):

    url_base = "https://restaurant-api.wolt.com/v1/merchant-admin/"

    def __init__(self, config: Mapping[str, Any]):
        super().__init__(authenticator=config.get("authenticator"))
        self.config = config

    def next_page_token(self, response: requests.Response) -> Optional[Mapping[str, Any]]:
        """

        :param response: the most recent response from the API
        :return If there is another page in the result, a mapping (e.g: dict) containing information needed to query the next page in the response.
                If there are no more pages in the result, return None.
        """
        return None

    def request_params(
        self, stream_state: Mapping[str, Any], stream_slice: Mapping[str, any] = None, next_page_token: Mapping[str, Any] = None
    ) -> MutableMapping[str, Any]:
        """
        TODO: Override this method to define any query parameters to be set. Remove this method if you don't need to define request params.
        Usually contains common params e.g. pagination size etc.
        """
        return {}

    def parse_response(self, response: requests.Response, **kwargs) -> Iterable[Mapping]:
        """
        TODO: Override this method to define how a response is parsed.
        :return an iterable containing each record in the response
        """

        yield from response.json().get("results", [])

    def read_records(self, stream_slice: Mapping[str, Any] = None, **kwargs) -> Iterable[Mapping[str, Any]]:
        # Check if the access token has expired
        if self.authenticator.token_has_expired():

            self.authenticator.refresh_access_token()

        # Call the parent class's read_records method
        return super().read_records(stream_slice=stream_slice, **kwargs)


class Venues(WoltStream):
    """
    TODO: Change class name to match the table/data source this stream corresponds to.
    """

    # TODO: Fill in the primary key. Required. This is usually a unique field in the stream, like an ID or a timestamp.
    primary_key = "id"

    def path(
        self, stream_state: Mapping[str, Any] = None, stream_slice: Mapping[str, Any] = None, next_page_token: Mapping[str, Any] = None
    ) -> str:
        """
        :return The endpoint path for this stream
        """

        return "venues"


# Basic incremental stream
class IncrementalWoltStream(WoltStream, ABC):
    """
    TODO fill in details of this class to implement functionality related to incremental syncs for your connector.
         if you do not need to implement incremental sync for any streams, remove this class.
    """

    state_checkpoint_interval = 100

    @property
    def cursor_field(self) -> str:
        """
        :return str: The name of the cursor field.
        """
        return "start_date"

    def get_updated_state(self, current_stream_state: MutableMapping[str, Any], latest_record: Mapping[str, Any]) -> Mapping[str, Any]:
        """
        Override to determine the latest state after reading the latest record. This typically compared the cursor_field from the latest record and
        the current state and picks the 'most' recent cursor. This is how a stream's state is determined. Required for incremental.
        """
        now = pendulum.now("UTC")
        midnight = now.start_of("day")

        return {self.cursor_field: midnight.to_iso8601_string()}

    def request_params(self, stream_slice: Mapping[str, Any], stream_state: Mapping[str, Any], next_page_token: Mapping[str, Any]) -> MutableMapping[str, Any]:
        start_time = stream_slice[self.cursor_field]
        end_time = start_time.add(days=self.config["slice_interval"])

        return {
            "start_time": start_time.to_iso8601_string(),
            "end_time": end_time.to_iso8601_string(),
            "interval": "P0DT1H"
        }

    def stream_slices(self, stream_state: Mapping[str, Any] = None, **kwargs) -> Iterable[Optional[Mapping[str, any]]]:

        lookback_window = int(self.config.get("lookback_window", 0))

        if stream_state:
            state_start_date = pendulum.parse(
                stream_state.get(self.cursor_field))
        else:
            state_start_date = pendulum.parse(self.config["start_date"])

        start_date = max(pendulum.parse(
            self.config["start_date"]), state_start_date.subtract(days=lookback_window))

        end_date = pendulum.now("UTC").start_of("day")

        venues_stream_data = self.parent.read_records(
            sync_mode=SyncMode.full_refresh)
        venue_codes = [record["id"] for record in venues_stream_data]

        slices = []
        for venue_code in venue_codes:
            current_date = start_date
            while current_date <= end_date:
                slices.append({
                    self.cursor_field: current_date,
                    "venue_code": venue_code,
                })
                current_date = current_date.add(
                    days=self.config["slice_interval"])

        return slices


class Purchases(IncrementalWoltStream):

    cursor_field = "start_date"
    primary_key = "id"

    def __init__(self, parent: Stream, config: Mapping[str, Any]):
        super().__init__(config)
        self.parent = parent

    # override the parse_response method to parse the response
    def parse_response(self, response: requests.Response, **kwargs) -> Iterable[Mapping]:

        yield from response.json().get("purchases", [])

    def path(self, stream_slice: Mapping[str, Any], **kwargs) -> str:
        venue_code = stream_slice["venue_code"]
        return f"venues/{venue_code}/purchases"

    def request_params(self, stream_slice: Mapping[str, Any], stream_state: Mapping[str, Any], next_page_token: Mapping[str, Any]) -> MutableMapping[str, Any]:
        start_time = stream_slice[self.cursor_field]
        end_time = start_time.add(days=self.config["slice_interval"])

        return {
            "start_time": start_time.to_iso8601_string(),
            "end_time": end_time.to_iso8601_string(),
            "statuses": "received,delivered",  # TODO: ADD MORE STATUSES?
        }


class OfflineMinutes(IncrementalWoltStream):
    """
    TODO: Change class name to match the table/data source this stream corresponds to.
    """

    cursor_field = "start_time"
    primary_key = ["start_time", "venue_code"]

    def __init__(self, parent: Stream, config: Mapping[str, Any]):
        super().__init__(config)
        self.parent = parent

    # override the parse_response method to parse the response
    def parse_response(self, response: requests.Response, **kwargs) -> Iterable[Mapping]:

        try:
            records = response.json()
        except ValueError:
            logger.warning(
                f"Error parsing OfflineMinutes JSON response: {response.text}")
            # Return an empty array if there's an error parsing the JSON response
            return []

        # Access the venue_code from the stream_slice
        venue_code = kwargs.get("stream_slice", {}).get("venue_code")

        for record in records:
            # Add the venue_code to each record
            record["venue_code"] = venue_code
            yield record

    def path(self, stream_slice: Mapping[str, Any], **kwargs) -> str:
        venue_code = stream_slice["venue_code"]
        return f"venues/{venue_code}/offline-minutes"


# Source
class SourceWolt(AbstractSource):

    def get_authenticator(self, config):
        token_refresh_endpoint = "https://authentication.wolt.com/v1/wauth2/access_token"
        return Oauth2Authenticator(
            token_refresh_endpoint=token_refresh_endpoint,
            client_id=None,
            client_secret=None,
            refresh_token=config.get('refresh_token'),
            scopes=None,
        )

    def check_connection(self, logger, config) -> Tuple[bool, any]:
        """

        :param config:  the user-input config object conforming to the connector's spec.yaml
        :param logger:  logger object
        :return Tuple[bool, any]: (True, None) if the input config can be used to connect to the API successfully, (False, error) otherwise.
        """

        config["authenticator"] = self.get_authenticator(config)
        stream = Venues(config)
        stream.records_limit = 1
        try:
            next(stream.read_records(sync_mode=SyncMode.full_refresh), None)
            return True, None
        except Exception as e:
            return False, e

    def streams(self, config: Mapping[str, Any]) -> List[Stream]:
        """
        :param config: A Mapping of the user input configuration as defined in the connector spec.
        """

        config["authenticator"] = self.get_authenticator(config)
        venues = Venues(config)

        return [Venues(config), Purchases(parent=venues, config=config), OfflineMinutes(parent=venues, config=config)]
