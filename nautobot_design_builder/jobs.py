"""Populate Nautobot with an Excel file."""

# pylint: disable=logging-fstring-interpolation

import json

from typing import Union

from django.conf import settings
from pandas import DataFrame, read_excel
from nautobot.apps.jobs import BooleanVar, FileVar, Job
from nautobot.apps.jobs import register_jobs

from nautobot_design_builder.contrib.ext import LookupExtension
from nautobot_design_builder.design_job import Environment

DEFAULT_LOGGING_LEVEL: str = settings.LOG_LEVEL


def pretty_json(msg: Union[list, dict]) -> str:
    """Pretty print in Nautobot JobResult (markdown format)."""
    return "```json\n" + json.dumps(msg, indent=2) + "\n```"


class DataPopulationFromExcelFile(Job):
    """Populate Nautobot with an Excel file."""

    file = FileVar(label="Excel file", required=True, description="Upload Excel file")
    debug = BooleanVar(label="Debug", default=False, description="Enable more verbose messages.")
    has_sensitive_variables: bool = False

    class Meta:  # pylint: disable=too-few-public-methods
        """Meta attribute for the Job."""

        name = "Data population from Excel file"
        description = "Import various entries from an Excel file"

    def _get_index_values(self, sheet: dict) -> tuple[str, str, str]:
        """Get the index values: model, sheet_name, keys."""
        try:
            model: str = sheet["model"]
        except (AttributeError, KeyError) as ex:
            self.logger.warning(f"Error in Index data (row {sheet['sheet_name']}, cell 'model'): {ex}.")
            raise
        try:
            sheet_name: str = sheet["sheet_name"]
        except (AttributeError, KeyError) as ex:
            self.logger.warning(f"Error in Index data (row {sheet['sheet_name']}, cell 'sheet_name'): {ex}.")
            raise
        try:
            keys: list[str] = sheet["keys"].split(",")
        except (AttributeError, KeyError) as ex:
            self.logger.warning(f"Probable error in Index data (row {sheet['sheet_name']}, cell 'keys'): {ex}.")
            keys = []
        try:
            json_fields: list[str] = sheet["json_fields"].split(",")
        except (AttributeError, KeyError):
            json_fields = []
        return {"model": model, "sheet_name": sheet_name, "keys": keys, "json_fields": json_fields}

    def _read_sheet(self, file: str, sheet_name: str) -> DataFrame:
        """Get contents of a specific sheet from a given Excel file using Pandas."""
        self.logger.debug(msg=f"Loading data from {sheet_name}...")
        try:
            return read_excel(file, sheet_name=sheet_name)
        except ValueError:
            self.logger.error(msg=f"No sheet named {sheet_name}. Aborting...")
            raise

    def _handle_keys(self, sheet_data: DataFrame, keys: list[str]) -> DataFrame:
        """Prepend "!create_or_update:" to keys."""
        rename_keys_map = {key: f"!create_or_update:{key}" for key in keys}
        return sheet_data.rename(columns=rename_keys_map)

    @staticmethod
    def _handle_content_types(sheet_data: DataFrame) -> DataFrame:
        """Handle Content Types."""

        def _transform_content_type(content_type: str) -> dict[str, str]:
            """Replace Content Type string (e.g. 'dcim.device') with DesignBuilder-appropriate entry."""
            app_label, model = content_type.split(".")
            return {"!get:app_label": app_label, "!get:model": model}

        def _transform_content_types(content_types: str) -> list[dict[str, str]]:
            """Perform `_transform_content_type` for a list of Content Type strings."""
            ct_list = []
            for content_type in content_types.split(","):
                ct = _transform_content_type(content_type=content_type)
                ct_list.append(ct)
            return ct_list

        # Handle singular Content Type ("content_type" column)
        try:
            sheet_data["content_type"] = sheet_data["content_type"].apply(_transform_content_type)
        except KeyError:
            pass

        # Handle list of Content Types ("content_types" column)
        try:
            sheet_data["content_types"] = sheet_data["content_types"].apply(_transform_content_types)
        except KeyError:
            pass
        return sheet_data

    @staticmethod
    def _handle_json_fields(sheet_data: DataFrame, json_fields: list[str]) -> dict:
        """Load JSON data into object."""
        try:
            for json_field in json_fields:
                sheet_data[json_field] = sheet_data[json_field].apply(json.loads)
        except KeyError:
            pass
        return sheet_data

    @staticmethod
    def _handle_primary_ip_addresses(sheet_data: DataFrame) -> DataFrame:
        """Handle primary IP assignments."""

        def _transform_primary_ip(ip: str) -> dict:
            """Handle Primary IP addresses."""
            return {"!get:address": ip, "deferred": True}

        try:
            sheet_data["primary_ip4"] = sheet_data["primary_ip4"].apply(_transform_primary_ip)
        except KeyError:
            pass
        return sheet_data

    @staticmethod
    def _handle_cables(cables: list[dict[str, str]]) -> list[dict[str, str]]:
        """Handle designs about Cables - restructured required to use Design Builder's "LookupExtension"."""

        def _transform_cable(cable: dict) -> dict:
            """Restructure cable dictionary."""
            return {
                "status__name": cable.get("status__name"),
                "!lookup:termination_a": {
                    "content-type": cable.get("termination_a_type"),
                    "device__name": cable.get("termination_a__device__name"),
                    "name": cable.get("termination_a__name"),
                },
                "!lookup:termination_b": {
                    "content-type": cable.get("termination_b_type"),
                    "device__name": cable.get("termination_b__device__name"),
                    "name": cable.get("termination_b__name"),
                },
            }

        return [_transform_cable(cable) for cable in cables]

    def _process_sheet_data(self, sheet_data: DataFrame, sheet_metadata: dict) -> dict:
        """Perform all required actions to make the dataframe ready for Design Builder."""
        model = sheet_metadata["model"]
        keys = sheet_metadata["keys"]
        json_fields = sheet_metadata["json_fields"]

        sheet_data = self._handle_keys(sheet_data=sheet_data, keys=keys)
        sheet_data = self._handle_content_types(sheet_data=sheet_data)
        sheet_data = self._handle_json_fields(sheet_data=sheet_data, json_fields=json_fields)
        sheet_data = self._handle_primary_ip_addresses(sheet_data=sheet_data)

        # Special case: Cables - restructure the design to use Design Builder's "LookupExtension"
        if model == "cables":
            return {model: self._handle_cables(sheet_data.to_dict(orient="records"))}
        return {model: sheet_data.to_dict(orient="records")}

    def _import_objects_db(self, sheet_name: str, design: str) -> None:
        """Import objects into Nautobot using Design Builder."""
        self.logger.debug(msg=f"Importing data from {sheet_name} using Design Builder...")
        try:
            builder = Environment(job_result=self.job_result, extensions=[LookupExtension])
            builder.implement_design(design)
        except Exception as ex:  # pylint: disable=broad-exception-caught
            self.logger.error(msg=f"Error while importing data: ({ex}). Aborting...")
            raise

    def run(self, file: str, debug: bool):  # pylint: disable=arguments-differ
        """Execute the Data Population Job."""
        self.logger.setLevel("DEBUG" if debug else DEFAULT_LOGGING_LEVEL)

        # Load the schema of the Excel file from the "Index" sheet
        index: DataFrame = self._read_sheet(file=file, sheet_name="Index").to_dict(orient="records")
        self.logger.debug(msg=pretty_json(index), extra={"object": "Index"})

        # Loop through the sheets of the Excel file.
        for sheet in index:
            self.logger.info(msg=f"**Processing {sheet['sheet_name']}...**")

            # Readability counts!
            sheet_metadata = self._get_index_values(sheet=sheet)
            sheet_name = sheet_metadata["sheet_name"]

            # Read the relevant Excel worksheet into a Pandas DataFrame.
            sheet_data: DataFrame = self._read_sheet(file=file, sheet_name=sheet_name)
            self.logger.debug(msg=pretty_json(sheet_data.to_dict(orient="records")), extra={"object": sheet_name})

            # Process sheet data, convert to design, log
            design = self._process_sheet_data(sheet_data=sheet_data, sheet_metadata=sheet_metadata)
            self.logger.debug(
                msg=pretty_json(design),
                extra={"object": f"{sheet_name} design"},
            )

            # Implement design using Design Builder's "Environment" class
            self._import_objects_db(sheet_name=sheet_name, design=design)

    # def on_success(self, retval, task_id, args, kwargs):
    #     """Mirror the overall "import Objects" status to JobResult."""
    #     self.job_result.status = self.overall_import_status
    #     self.job_result.validated_save()
    #     super().on_success(retval, task_id, args, kwargs)

    # def after_return(self, status, retval, task_id, args, kwargs, einfo):  # pylint: disable=too-many-arguments
    #     """Cumulative log of all import errors."""
    #     if self.errors_to_report:
    #         self.logger.warning(
    #             msg="```json\n" + json.dumps(self.errors_to_report, indent=2) + "\n```",
    #             extra={"object": "Import Errors"},
    #         )
    #     super().after_return(status, retval, task_id, args, kwargs, einfo=einfo)


jobs = [DataPopulationFromExcelFile]
register_jobs(*jobs)
