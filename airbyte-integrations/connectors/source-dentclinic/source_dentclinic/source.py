#
# Copyright (c) 2022 Airbyte, Inc., all rights reserved.
#


from abc import ABC
from typing import Any, Iterable, List, Mapping, Optional, Tuple, Iterator, MutableMapping

import requests
import pendulum
import xmltodict
from airbyte_cdk.sources import AbstractSource
from airbyte_cdk.sources.streams import Stream
from airbyte_cdk.sources.streams.http import HttpStream

from .streams import DentclinicClinicIdsStream, DentclinicStaticStream, DentclinicIncrementalStream, DentclinicIncrementalBookingStream


class BookingsFr(DentclinicIncrementalBookingStream):
    primary_key = "Id"
    endpoint_data_path = ['soap:Envelope', 'soap:Body', 'GetBookingsResponse',
                          'GetBookingsResult', 'BookingModel']
    static_endpoint = "GetBookings"
    date_from_field = "dateTimeStart"
    date_until_field = "dateTimeEnd"

    def path(
            self, stream_state: Mapping[str, Any] = None, stream_slice: Mapping[str, Any] = None, next_page_token: Mapping[str, Any] = None
    ) -> str:
        """
        should return "bookings". Required.
        """
        return ""

    @property
    def http_method(self) -> str:
        return "POST"


class Bookings(DentclinicIncrementalBookingStream):
    state_checkpoint_interval = 1
    primary_key = "Id"
    endpoint_data_path = ['soap:Envelope', 'soap:Body', 'GetBookingsResponse',
                          'GetBookingsResult', 'BookingModel']
    static_endpoint = "GetBookings"
    date_from_field = "dateTimeStart"
    date_until_field = "dateTimeEnd"

    def path(
            self, stream_state: Mapping[str, Any] = None, stream_slice: Mapping[str, Any] = None, next_page_token: Mapping[str, Any] = None
    ) -> str:
        """should return "bookings". Required."""
        return ""

    @property
    def http_method(self) -> str:
        return "POST"

    @property
    def cursor_field(self) -> str:
        """
        This field's presence tells the framework this in an incremental stream. Required for incremental.

        :return str: The name of the cursor field.
        """
        return "Time"

    def get_updated_state(self, current_stream_state: MutableMapping[str, Any], latest_record: Mapping[str, Any]) -> Mapping[str, Any]:
        """
        Override to determine the latest state after reading the latest record. This typically compared the cursor_field from the latest record and
        the current state and picks the 'most' recent cursor. This is how a stream's state is determined. Required for incremental.
        """
        state_mapping = current_stream_state.get(self.cursor_field, {})

        last_record_value = latest_record.get(self.cursor_field)
        if last_record_value:
            state_mapping.update({self.clinic_id: last_record_value})

        return {self.cursor_field: state_mapping}


class UtilizationReport(DentclinicIncrementalStream):
    state_checkpoint_interval = 1
    primary_key = "Id"
    endpoint_data_path = ['soap:Envelope', 'soap:Body',
                          'GetUtilizationReportResponse', 'GetUtilizationReportResult']
    static_endpoint = "GetUtilizationReport"
    date_from_field = "dateFrom"
    date_until_field = "dateUntil"

    def path(
            self, stream_state: Mapping[str, Any] = None, stream_slice: Mapping[str, Any] = None, next_page_token: Mapping[str, Any] = None
    ) -> str:
        """should return "bookings". Required."""
        return ""

    @property
    def http_method(self) -> str:
        return "POST"

    @property
    def cursor_field(self) -> str:
        """
        This field's presence tells the framework this in an incremental stream. Required for incremental.

        :return str: The name of the cursor field.
        """
        return "DateFrom"

    def get_updated_state(self, current_stream_state: MutableMapping[str, Any], latest_record: Mapping[str, Any]) -> Mapping[str, Any]:
        """
        Override to determine the latest state after reading the latest record. This typically compared the cursor_field from the latest record and
        the current state and picks the 'most' recent cursor. This is how a stream's state is determined. Required for incremental.
        """
        state_mapping = current_stream_state.get(self.cursor_field, {})

        last_record_value = latest_record.get(self.cursor_field)
        if last_record_value:
            state_mapping.update({self.clinic_id: last_record_value})

        return {self.cursor_field: state_mapping}


class UtilizationReportFr(DentclinicIncrementalStream):
    # state_checkpoint_interval = 1
    primary_key = "Id"
    endpoint_data_path = ['soap:Envelope', 'soap:Body',
                          'GetUtilizationReportResponse', 'GetUtilizationReportResult']
    static_endpoint = "GetUtilizationReport"
    date_from_field = "dateFrom"
    date_until_field = "dateUntil"

    def path(
            self, stream_state: Mapping[str, Any] = None, stream_slice: Mapping[str, Any] = None, next_page_token: Mapping[str, Any] = None
    ) -> str:
        """
        should return "bookings". Required.
        """
        return ""

    @property
    def http_method(self) -> str:
        return "POST"


class TreatmentsReport(DentclinicIncrementalStream):
    state_checkpoint_interval = 1
    primary_key = "Id"
    endpoint_data_path = ['soap:Envelope', 'soap:Body',
                          'GetTreatmentsReportResponse', 'GetTreatmentsReportResult', 'ExecutedTreatmentModel']
    static_endpoint = "GetTreatmentsReport"
    date_from_field = "dateFrom"
    date_until_field = "dateUntil"

    def path(
            self, stream_state: Mapping[str, Any] = None, stream_slice: Mapping[str, Any] = None, next_page_token: Mapping[str, Any] = None
    ) -> str:
        """should return "bookings". Required."""
        return ""

    @property
    def http_method(self) -> str:
        return "POST"

    @property
    def cursor_field(self) -> str:
        """
        This field's presence tells the framework this in an incremental stream. Required for incremental.

        :return str: The name of the cursor field.
        """
        return "Date"

    def get_updated_state(self, current_stream_state: MutableMapping[str, Any], latest_record: Mapping[str, Any]) -> Mapping[str, Any]:
        """
        Override to determine the latest state after reading the latest record. This typically compared the cursor_field from the latest record and
        the current state and picks the 'most' recent cursor. This is how a stream's state is determined. Required for incremental.
        """
        state_mapping = current_stream_state.get(self.cursor_field, {})

        last_record_value = latest_record.get(self.cursor_field)
        if last_record_value:
            state_mapping.update({self.clinic_id: last_record_value})

        return {self.cursor_field: state_mapping}


class TreatmentsReportFr(DentclinicIncrementalStream):
    # state_checkpoint_interval = 1
    primary_key = "Id"
    endpoint_data_path = ['soap:Envelope', 'soap:Body',
                          'GetTreatmentsReportResponse', 'GetTreatmentsReportResult', 'ExecutedTreatmentModel']
    static_endpoint = "GetTreatmentsReport"
    date_from_field = "dateFrom"
    date_until_field = "dateUntil"

    def path(
            self, stream_state: Mapping[str, Any] = None, stream_slice: Mapping[str, Any] = None, next_page_token: Mapping[str, Any] = None
    ) -> str:
        """
        should return "bookings". Required.
        """
        return ""

    @property
    def http_method(self) -> str:
        return "POST"


class Resources(DentclinicClinicIdsStream):
    primary_key = "Id"

    def path(
            self, stream_state: Mapping[str, Any] = None, stream_slice: Mapping[str, Any] = None, next_page_token: Mapping[str, Any] = None
    ) -> str:
        """
        should return "resources". Required.
        """
        return ""

    @property
    def http_method(self) -> str:
        return "POST"


class Clinics(DentclinicStaticStream):
    primary_key = "Id"
    static_endpoint = 'GetClinics'
    endpoint_data_path = ['soap:Envelope', 'soap:Body',
                          'GetClinicsResponse', 'GetClinicsResult', 'ClinicModel']

    def path(
            self, stream_state: Mapping[str, Any] = None, stream_slice: Mapping[str, Any] = None, next_page_token: Mapping[str, Any] = None
    ) -> str:
        """
        should return "clinics". Required.
        """
        return ""

    @property
    def http_method(self) -> str:
        return "POST"


class PatientsReport(DentclinicStaticStream):
    primary_key = "PatientId"
    static_endpoint = 'GetPatientsReport'
    endpoint_data_path = ['soap:Envelope', 'soap:Body',
                          'GetPatientsReportResponse', 'GetPatientsReportResult', 'PatientsReportModel']

    def path(
            self, stream_state: Mapping[str, Any] = None, stream_slice: Mapping[str, Any] = None, next_page_token: Mapping[str, Any] = None
    ) -> str:
        """
        should return "clinics". Required.
        """
        return ""

    @property
    def http_method(self) -> str:
        return "POST"


class Services(DentclinicStaticStream):
    primary_key = "Id"
    static_endpoint = 'GetServices'
    endpoint_data_path = ['soap:Envelope', 'soap:Body',
                          'GetServicesResponse', 'GetServicesResult', 'ServiceModel']

    def path(
            self, stream_state: Mapping[str, Any] = None, stream_slice: Mapping[str, Any] = None, next_page_token: Mapping[str, Any] = None
    ) -> str:
        """
        should return "clinics". Required.
        """
        return ""

    @property
    def http_method(self) -> str:
        return "POST"


# Source
class SourceDentclinic(AbstractSource):
    def check_connection(self, logger, config) -> Tuple[bool, any]:
        """
        See https://github.com/airbytehq/airbyte/blob/master/airbyte-integrations/connectors/source-stripe/source_stripe/source.py#L232
        for an example.

        :param config:  the user-input config object conforming to the connector's spec.yaml
        :param logger:  logger object
        :return Tuple[bool, any]: (True, None) if the input config can be used to connect to the API successfully, (False, error) otherwise.
        """
        return True, None

    def streams(self, config: Mapping[str, Any]) -> List[Stream]:
        """
        :param config: A Mapping of the user input configuration as defined in the connector spec.
        """
        return [BookingsFr(config=config, enable_days_back_limit=True), Bookings(config=config, enable_days_back_limit=False), Clinics(config=config),
                Services(config=config), Resources(config=config), PatientsReport(config=config), UtilizationReport(
                    config=config, enable_days_back_limit=False), UtilizationReportFr(config=config, enable_days_back_limit=True),
                TreatmentsReportFr(config=config, enable_days_back_limit=True), TreatmentsReport(config=config, enable_days_back_limit=False)]
