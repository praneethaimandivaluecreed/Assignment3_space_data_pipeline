import json
from pathlib import Path

import pandas as pd

from logger import logger


# Configuration

PROJECT_ROOT = Path(__file__).resolve().parent.parent

RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"

# Create processed folder if it does not already exist
PROCESSED_DATA_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# Read raw JSON files

def read_raw_dataset(dataset_name):
    dataset_dir = RAW_DATA_DIR / dataset_name
    all_records = []

    json_files = sorted(
        dataset_dir.glob("page_*.json")
    )

    logger.info(
        f"Reading raw dataset: {dataset_name}"
    )

    if not json_files:
        raise FileNotFoundError(
            f"No raw JSON files found for "
            f"{dataset_name}"
        )

    # Read every raw JSON page belonging to the dataset.
    # This allows the transformation layer to work with
    # multiple API pages instead of depending on one file.
    for file_path in json_files:
        logger.info(
            f"Reading: {file_path}"
        )

        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(file)

        records = data.get(
            "results",
            []
        )

        all_records.extend(records)

        logger.info(
            f"Records loaded from file: "
            f"{len(records)}"
        )

    logger.info(
        f"Total raw records for "
        f"{dataset_name}: {len(all_records)}"
    )

    return all_records


# Transform agency data

def transform_agencies(records):
    logger.info("=" * 70)
    logger.info("TRANSFORMING: AGENCIES")
    logger.info("=" * 70)

    transformed = []

    for record in records:

        # The API can return country information as a list,
        # dictionary, or another value depending on the record.
        # We extract only the country name needed by our database.
        country = record.get("country")
        country_name = None

        if isinstance(country, list):
            country_names = []

            for country_item in country:
                if isinstance(country_item, dict):
                    name = country_item.get("name")

                    if name:
                        country_names.append(name)

            if country_names:
                country_name = ", ".join(
                    country_names
                )

        elif isinstance(country, dict):
            country_name = country.get(
                "name"
            )

        elif country is not None:
            logger.warning(
                f"Agency {record.get('id')} has "
                f"unexpected country data type: "
                f"{type(country).__name__}"
            )

        # Agency type is also returned as a nested object.
        # Only the readable type name is required in the processed data.
        agency_type = record.get("type")
        agency_type_name = None

        if isinstance(agency_type, dict):
            agency_type_name = (
                agency_type.get("name")
            )

        elif agency_type is not None:
            logger.warning(
                f"Agency {record.get('id')} has "
                f"unexpected type data."
            )

        agency = {
            "agency_id": record.get("id"),
            "agency_name": record.get("name"),
            "abbreviation": record.get("abbrev"),
            "agency_type": agency_type_name,
            "country": country_name,
            "founding_year": record.get("founding_year")
        }

        transformed.append(agency)

    df = pd.DataFrame(transformed)

    # Remove duplicate agency records using the primary key.
    before = len(df)

    df = df.drop_duplicates(
        subset=["agency_id"]
    )

    duplicates_removed = before - len(df)

    logger.info(
        f"Duplicate agencies removed: "
        f"{duplicates_removed}"
    )

    # Standardize text columns by converting them to
    # pandas string type and removing unnecessary spaces.
    text_columns = [
        "agency_name",
        "abbreviation",
        "agency_type",
        "country"
    ]

    for column in text_columns:
        df[column] = (
            df[column]
            .astype("string")
            .str.strip()
        )

    # Convert numeric fields to nullable integer types.
    # Int64 allows missing values while still keeping the
    # column logically integer-based.
    df["agency_id"] = pd.to_numeric(
        df["agency_id"],
        errors="coerce"
    ).astype("Int64")

    df["founding_year"] = pd.to_numeric(
        df["founding_year"],
        errors="coerce"
    ).astype("Int64")

    logger.info(
        f"Missing agency country values: "
        f"{df['country'].isna().sum()}"
    )

    logger.info(
        f"Missing agency type values: "
        f"{df['agency_type'].isna().sum()}"
    )

    logger.info(
        f"Processed agency records: "
        f"{len(df)}"
    )

    return df


# Transform launcher configuration data

def transform_launcher_configurations(records):
    logger.info("=" * 70)
    logger.info(
        "TRANSFORMING: LAUNCHER CONFIGURATIONS"
    )
    logger.info("=" * 70)

    transformed = []

    for record in records:

        # Manufacturer information is nested inside
        # the launcher configuration object.
        manufacturer = (
            record.get("manufacturer") or {}
        )

        # Protect the transformation from unexpected
        # API structures.
        if not isinstance(
            manufacturer,
            dict
        ):
            logger.warning(
                f"Launcher configuration "
                f"{record.get('id')} has "
                f"unexpected manufacturer format."
            )

            manufacturer = {}

        transformed.append({
            "launcher_configuration_id":
                record.get("id"),

            "launcher_name":
                record.get("name"),

            "full_name":
                record.get("full_name"),

            "variant":
                record.get("variant"),

            "manufacturer_id":
                manufacturer.get("id"),

            "manufacturer_name":
                manufacturer.get("name"),

            "active":
                record.get("active"),

            "reusable":
                record.get("reusable")
        })

    df = pd.DataFrame(transformed)

    # The launcher configuration ID acts as the primary key,
    # so duplicate IDs are removed.
    before = len(df)

    df = df.drop_duplicates(
        subset=[
            "launcher_configuration_id"
        ]
    )

    duplicates_removed = before - len(df)

    logger.info(
        f"Duplicate launcher configurations "
        f"removed: {duplicates_removed}"
    )

    # Standardize text fields.
    text_columns = [
        "launcher_name",
        "full_name",
        "variant",
        "manufacturer_name"
    ]

    for column in text_columns:
        df[column] = (
            df[column]
            .astype("string")
            .str.strip()
        )

    # Convert ID fields into nullable integers.
    df["launcher_configuration_id"] = (
        pd.to_numeric(
            df["launcher_configuration_id"],
            errors="coerce"
        ).astype("Int64")
    )

    df["manufacturer_id"] = (
        pd.to_numeric(
            df["manufacturer_id"],
            errors="coerce"
        ).astype("Int64")
    )

    logger.info(
        "Launcher configuration transformation "
        "completed."
    )

    logger.info(
        f"Processed records: {len(df)}"
    )

    return df


# Transform launch pad data

def transform_pads(records):
    logger.info("=" * 70)
    logger.info("TRANSFORMING: PADS")
    logger.info("=" * 70)

    transformed = []

    for record in records:

        # Country and location are nested objects in the API response.
        country = (
            record.get("country") or {}
        )

        location = (
            record.get("location") or {}
        )

        country_name = None

        if isinstance(country, dict):
            country_name = country.get(
                "name"
            )

        location_id = None
        location_name = None

        if isinstance(location, dict):
            location_id = location.get(
                "id"
            )

            location_name = location.get(
                "name"
            )

        transformed.append({
            "pad_id":
                record.get("id"),

            "pad_name":
                record.get("name"),

            "active":
                record.get("active"),

            "latitude":
                record.get("latitude"),

            "longitude":
                record.get("longitude"),

            "country":
                country_name,

            "location_id":
                location_id,

            "location_name":
                location_name,

            "total_launch_count":
                record.get(
                    "total_launch_count"
                ),

            "orbital_launch_attempt_count":
                record.get(
                    "orbital_launch_attempt_count"
                ),

            "fastest_turnaround":
                record.get(
                    "fastest_turnaround"
                )
        })

    df = pd.DataFrame(transformed)

    # Remove duplicate pads using the pad primary key.
    before = len(df)

    df = df.drop_duplicates(
        subset=["pad_id"]
    )

    duplicates_removed = before - len(df)

    logger.info(
        f"Duplicate pads removed: "
        f"{duplicates_removed}"
    )

    # Standardize text columns.
    text_columns = [
        "pad_name",
        "country",
        "location_name"
    ]

    for column in text_columns:
        df[column] = (
            df[column]
            .astype("string")
            .str.strip()
        )

    # Convert identifiers to nullable integer types.
    df["pad_id"] = pd.to_numeric(
        df["pad_id"],
        errors="coerce"
    ).astype("Int64")

    df["location_id"] = pd.to_numeric(
        df["location_id"],
        errors="coerce"
    ).astype("Int64")

    # Latitude and longitude are numeric geographic values.
    df["latitude"] = pd.to_numeric(
        df["latitude"],
        errors="coerce"
    )

    df["longitude"] = pd.to_numeric(
        df["longitude"],
        errors="coerce"
    )

    # Launch count fields are numeric counters.
    df["total_launch_count"] = pd.to_numeric(
        df["total_launch_count"],
        errors="coerce"
    ).astype("Int64")

    df["orbital_launch_attempt_count"] = (
        pd.to_numeric(
            df["orbital_launch_attempt_count"],
            errors="coerce"
        ).astype("Int64")
    )

    logger.info(
        f"Processed pad records: "
        f"{len(df)}"
    )

    return df


# Transform launch data

def transform_launches(
    records,
    agencies_df,
    launcher_configs_df,
    pads_df
):
    logger.info("=" * 70)
    logger.info("TRANSFORMING: LAUNCHES")
    logger.info("=" * 70)

    transformed = []

    for record in records:

        # The launch API response contains several nested objects.
        # We extract only the fields required by the relational model
        # and the analytical transformations.
        status = (
            record.get("status") or {}
        )

        provider = (
            record.get(
                "launch_service_provider"
            ) or {}
        )

        rocket = (
            record.get("rocket") or {}
        )

        configuration = (
            rocket.get("configuration") or {}
        )

        mission = (
            record.get("mission") or {}
        )

        pad = (
            record.get("pad") or {}
        )

        # Orbit information is nested inside:
        #
        # mission
        #     -> orbit
        #          -> name
        #
        # We extract the orbit name so that it can later be
        # converted into a higher-level business category.
        orbit = (
            mission.get("orbit") or {}
        )

        orbit_name = None

        if isinstance(orbit, dict):
            orbit_name = orbit.get(
                "name"
            )

        transformed.append({
            "launch_id":
                record.get("id"),

            "launch_name":
                record.get("name"),

            "launch_datetime":
                record.get("net"),

            "status_id":
                status.get("id"),

            "status_name":
                status.get("name"),

            "launch_probability":
                record.get("probability"),

            "weather_concerns":
                record.get(
                    "weather_concerns"
                ),

            "failure_reason":
                record.get(
                    "failreason"
                ),

            "agency_id":
                provider.get("id"),

            "launcher_configuration_id":
                configuration.get("id"),

            "pad_id":
                pad.get("id"),

            "mission_name":
                mission.get("name"),

            "mission_type":
                mission.get("type"),

            # Keep the raw orbit name temporarily.
            # It will be converted into orbit_class later.
            "orbit_name":
                orbit_name
        })

    df = pd.DataFrame(transformed)

    # Remove duplicate launch records using launch_id,
    # which acts as the primary key in the database.
    before = len(df)

    df = df.drop_duplicates(
        subset=["launch_id"]
    )

    duplicates_removed = before - len(df)

    logger.info(
        f"Duplicate launches removed: "
        f"{duplicates_removed}"
    )

    # Standardize text columns.
    text_columns = [
        "launch_name",
        "status_name",
        "weather_concerns",
        "failure_reason",
        "mission_name",
        "mission_type",
        "orbit_name"
    ]

    for column in text_columns:
        df[column] = (
            df[column]
            .astype("string")
            .str.strip()
        )

    # Launch IDs are stored as strings because the API uses
    # UUID-style identifiers rather than numeric IDs.
    df["launch_id"] = (
        df["launch_id"]
        .astype("string")
        .str.strip()
    )

    # Convert status and foreign-key fields to nullable integers.
    df["status_id"] = pd.to_numeric(
        df["status_id"],
        errors="coerce"
    ).astype("Int64")

    df["agency_id"] = pd.to_numeric(
        df["agency_id"],
        errors="coerce"
    ).astype("Int64")

    df["launcher_configuration_id"] = (
        pd.to_numeric(
            df["launcher_configuration_id"],
            errors="coerce"
        ).astype("Int64")
    )

    df["pad_id"] = pd.to_numeric(
        df["pad_id"],
        errors="coerce"
    ).astype("Int64")

    # Probability is numeric but can contain missing values.
    df["launch_probability"] = pd.to_numeric(
        df["launch_probability"],
        errors="coerce"
    )

    # Convert the API datetime into a proper timezone-aware
    # pandas datetime value.
    df["launch_datetime"] = pd.to_datetime(
        df["launch_datetime"],
        errors="coerce",
        utc=True
    )

    # ------------------------------------------------------------
    # FILTER INVALID LAUNCH RECORDS
    # ------------------------------------------------------------

    # A launch cannot be loaded into the relational database
    # without a primary key or a valid launch timestamp.
    #
    # Therefore, records missing either of these essential fields
    # are removed before creating derived columns.
    before_filter = len(df)

    df = df.dropna(
        subset=[
            "launch_id",
            "launch_datetime"
        ]
    )

    filtered_records = (
        before_filter - len(df)
    )

    logger.info(
        f"Invalid launch records filtered: "
        f"{filtered_records}"
    )

    # ------------------------------------------------------------
    # BASIC DATE DERIVED COLUMNS
    # ------------------------------------------------------------

    # Extract the year from the launch timestamp.
    df["launch_year"] = (
        df["launch_datetime"]
        .dt.year
        .astype("Int64")
    )

    # Extract the month from the launch timestamp.
    df["launch_month"] = (
        df["launch_datetime"]
        .dt.month
        .astype("Int64")
    )

    # Divide the year into four calendar quarters.
    #
    # 1-3   -> Q1
    # 4-6   -> Q2
    # 7-9   -> Q3
    # 10-12 -> Q4
    #
    # This is more useful for analytical grouping than storing
    # only the raw month number.
    df["launch_quarter"] = (
        df["launch_datetime"]
        .dt.quarter
        .astype("Int64")
    )

    # ------------------------------------------------------------
    # STATUS DERIVED COLUMN
    # ------------------------------------------------------------

    # Convert the detailed API status into a smaller business
    # category that is easier to use in reporting and SQL analysis.
    #
    # Partial Failure must be checked before Failure because
    # "Partial Failure" contains the word "Failure".
    def categorize_status(status):
        if pd.isna(status):
            return "Unknown"

        status = str(status).strip().lower()

        if "partial" in status and "failure" in status:
            return "Partial Failure"

        if "success" in status:
            return "Successful"

        if "failure" in status:
            return "Failure"

        return "Other"

    df["status_category"] = (
        df["status_name"]
        .apply(categorize_status)
        .astype("string")
    )

    # Keep the existing boolean success field because it is
    # useful for simple filtering and validation.
    df["is_successful"] = (
        df["status_name"]
        .fillna("")
        .str.lower()
        .str.contains(
            "success",
            na=False
        )
    )

    # ------------------------------------------------------------
    # ORBIT DERIVED COLUMN
    # ------------------------------------------------------------

    # The API contains many detailed orbit names.
    # For analysis, these are grouped into broader categories.
    #
    # Example:
    # Low Earth Orbit       -> Earth Orbit
    # Medium Earth Orbit    -> Earth Orbit
    # Lunar Orbit           -> Lunar/Planetary
    # Mars flyby            -> Lunar/Planetary
    #
    # This gives the database a useful business-level classification
    # without losing the original API-derived information during
    # transformation.

    def classify_orbit(orbit_name):
        if pd.isna(orbit_name):
            return "Unknown"

        orbit_name = str(
            orbit_name
        ).strip().lower()

        earth_orbits = {
            "low earth orbit",
            "medium earth orbit",
            "polar orbit",
            "sun-synchronous orbit",
            "geosynchronous orbit",
            "elliptical orbit"
        }

        planetary_orbits = {
            "lunar orbit",
            "lunar impactor",
            "lunar flyby",
            "mars flyby",
            "venus flyby"
        }

        if orbit_name in earth_orbits:
            return "Earth Orbit"

        if orbit_name == "suborbital":
            return "Suborbital"

        if orbit_name in planetary_orbits:
            return "Lunar/Planetary"

        if orbit_name == "heliocentric n/a":
            return "Heliocentric"

        return "Unknown"

    df["orbit_class"] = (
        df["orbit_name"]
        .apply(classify_orbit)
        .astype("string")
    )

    # ------------------------------------------------------------
    # PAD TURNAROUND
    # ------------------------------------------------------------

    # Save the original order so that the dataframe can be restored
    # after calculating the time-based derived columns.
    df["_original_order"] = range(len(df))

    # Calculate the number of days between consecutive launches
    # from the same launch pad.
    #
    # We must first sort by pad and launch time.
    # Otherwise, diff() would compare launches in the wrong order.

    df = df.sort_values(
        [
            "pad_id",
            "launch_datetime"
        ],
        kind="stable"
    )

    df["pad_turnaround_days"] = (
        df.groupby("pad_id")[
            "launch_datetime"
        ]
        .diff()
        .dt.total_seconds()
        / 86400
    )

    # ------------------------------------------------------------
    # AGENCY LAUNCH GAP
    # ------------------------------------------------------------

    # Calculate the number of days between consecutive launches
    # performed by the same launch service provider/agency.
    #
    # IMPORTANT:
    # The dataframe above was sorted by pad_id.
    # We cannot calculate agency gaps using that ordering because
    # launches belonging to the same agency may not be chronological.
    #
    # Therefore, sort separately by agency_id and launch_datetime
    # before using groupby().diff().

    df = df.sort_values(
        [
            "agency_id",
            "launch_datetime"
        ],
        kind="stable"
    )

    df["agency_launch_gap_days"] = (
        df.groupby("agency_id")[
            "launch_datetime"
        ]
        .diff()
        .dt.total_seconds()
        / 86400
    )

    # Restore the original API record order after calculating
    # the group-based time differences.
    df = (
        df.sort_values(
            "_original_order"
        )
        .drop(
            columns=["_original_order"]
        )
    )

    # ------------------------------------------------------------
    # FOREIGN KEY VALIDATION
    # ------------------------------------------------------------

    # Build sets containing valid primary keys from the
    # corresponding processed dimension datasets.
    #
    # These checks prevent invalid foreign-key values from being
    # loaded into the SQL Server launch table.

    valid_agency_ids = set(
        agencies_df["agency_id"]
        .dropna()
        .astype(int)
    )

    missing_agencies = (
        df["agency_id"].notna()
        & ~df["agency_id"]
        .isin(valid_agency_ids)
    )

    logger.info(
        f"Launches with unmatched agencies: "
        f"{missing_agencies.sum()}"
    )

    # An unmatched foreign key is converted to NULL rather than
    # allowing the database load to fail because of an invalid
    # relationship.
    df.loc[
        missing_agencies,
        "agency_id"
    ] = pd.NA

    valid_launcher_ids = set(
        launcher_configs_df[
            "launcher_configuration_id"
        ]
        .dropna()
        .astype(int)
    )

    missing_launchers = (
        df["launcher_configuration_id"].notna()
        & ~df["launcher_configuration_id"]
        .isin(valid_launcher_ids)
    )

    logger.info(
        f"Launches with unmatched launcher "
        f"configurations: "
        f"{missing_launchers.sum()}"
    )

    df.loc[
        missing_launchers,
        "launcher_configuration_id"
    ] = pd.NA

    valid_pad_ids = set(
        pads_df["pad_id"]
        .dropna()
        .astype(int)
    )

    missing_pads = (
        df["pad_id"].notna()
        & ~df["pad_id"]
        .isin(valid_pad_ids)
    )

    logger.info(
        f"Launches with unmatched pads: "
        f"{missing_pads.sum()}"
    )

    df.loc[
        missing_pads,
        "pad_id"
    ] = pd.NA

    # ------------------------------------------------------------
    # FINAL COLUMN SELECTION
    # ------------------------------------------------------------

    # Keep only the fields that are required by the processed
    # launch dataset and the SQL Server launch table.
    #
    # orbit_name is removed because orbit_class is the business-level
    # derived field that will be stored.
    df = df[
        [
            "launch_id",
            "launch_name",
            "launch_datetime",
            "status_id",
            "status_name",
            "launch_probability",
            "weather_concerns",
            "failure_reason",
            "agency_id",
            "launcher_configuration_id",
            "pad_id",
            "mission_name",
            "mission_type",
            "launch_year",
            "launch_month",
            "launch_quarter",
            "status_category",
            "orbit_class",
            "pad_turnaround_days",
            "agency_launch_gap_days",
            "is_successful"
        ]
    ]

    # ------------------------------------------------------------
    # TRANSFORMATION SUMMARY
    # ------------------------------------------------------------

    logger.info(
        f"Successful launches: "
        f"{df['is_successful'].sum()}"
    )

    logger.info(
        f"Processed launch records: "
        f"{len(df)}"
    )

    logger.info(
        f"Successful launch categories: "
        f"{(df['status_category'] == 'Successful').sum()}"
    )

    logger.info(
        f"Failure launch categories: "
        f"{(df['status_category'] == 'Failure').sum()}"
    )

    logger.info(
        f"Partial failure launches: "
        f"{(df['status_category'] == 'Partial Failure').sum()}"
    )

    logger.info(
        f"Launches with orbit classification: "
        f"{df['orbit_class'].notna().sum()}"
    )

    logger.info(
        f"Pad turnaround values calculated: "
        f"{df['pad_turnaround_days'].notna().sum()}"
    )

    logger.info(
        f"Agency launch gap values calculated: "
        f"{df['agency_launch_gap_days'].notna().sum()}"
    )

    return df


# Save processed data

def save_processed_data(
    df,
    filename
):
    output_file = (
        PROCESSED_DATA_DIR / filename
    )

    # Save the transformed DataFrame as CSV.
    # The CSV becomes the input to the validation and loading layers.
    df.to_csv(
        output_file,
        index=False
    )

    logger.info(
        f"Processed data saved to: "
        f"{output_file}"
    )


# Main transformation pipeline

def main():
    logger.info("=" * 70)
    logger.info(
        "SPACE DATA TRANSFORMATION PIPELINE STARTED"
    )
    logger.info("=" * 70)

    try:

        # Read all raw datasets first.
        # Transformation is intentionally performed from the
        # preserved raw JSON layer instead of directly from the API.
        agencies_raw = read_raw_dataset(
            "agencies"
        )

        launcher_configs_raw = (
            read_raw_dataset(
                "launcher_configurations"
            )
        )

        pads_raw = read_raw_dataset(
            "pads"
        )

        launches_raw = read_raw_dataset(
            "launches"
        )

        # Transform the reference/dimension datasets first.
        # Launches depend on these datasets for foreign-key validation.
        agencies_df = transform_agencies(
            agencies_raw
        )

        launcher_configs_df = (
            transform_launcher_configurations(
                launcher_configs_raw
            )
        )

        pads_df = transform_pads(
            pads_raw
        )

        # Transform launches after the related datasets are available.
        launches_df = transform_launches(
            launches_raw,
            agencies_df,
            launcher_configs_df,
            pads_df
        )

        # Save all transformed datasets.
        save_processed_data(
            agencies_df,
            "agencies.csv"
        )

        save_processed_data(
            launcher_configs_df,
            "launcher_configurations.csv"
        )

        save_processed_data(
            pads_df,
            "pads.csv"
        )

        save_processed_data(
            launches_df,
            "launches.csv"
        )

        # Log a summary so that the transformation result
        # can be verified from the pipeline log.
        logger.info("=" * 70)
        logger.info("TRANSFORMATION SUMMARY")
        logger.info("=" * 70)

        logger.info(
            f"Agencies: "
            f"{len(agencies_df)}"
        )

        logger.info(
            f"Launcher configurations: "
            f"{len(launcher_configs_df)}"
        )

        logger.info(
            f"Pads: "
            f"{len(pads_df)}"
        )

        logger.info(
            f"Launches: "
            f"{len(launches_df)}"
        )

        logger.info("=" * 70)
        logger.info(
            "SPACE DATA TRANSFORMATION PIPELINE "
            "COMPLETED"
        )
        logger.info("=" * 70)

    except Exception as e:
        logger.exception(
            f"Transformation pipeline failed: {e}"
        )
        raise


if __name__ == "__main__":
    main()