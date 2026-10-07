import json
from pathlib import Path
import pandas as pd
from pyspark.sql.functions import explode


def read_raw_dataset(dataset_name):
    # Get the folder for the selected dataset
    dataset_dir = RAW_DATA_DIR / dataset_name

    # Read all page JSON files using Spark
    df = (
        spark.read
        .option("multiLine", True)
        .json(str(dataset_dir / "page_*.json"))
    )

    # Flatten the results array into individual records
    df = df.select(
        explode("results").alias("record")
    )

    # Expand the record struct into normal columns
    df = df.select("record.*")

    return df




def transform_agencies(df):
   
    # Select the required agency fields from the raw DataFrame
    df = df.select(
        col("id").alias("agency_id"),
        col("name").alias("agency_name"),
        col("abbrev").alias("abbreviation"),
        col("type.name").alias("agency_type"),
        col("country.name").alias("country"),
        col("founding_year")
    )

    # Remove duplicate agency records using the primary key
    before = df.count()

    df = df.dropDuplicates(
        ["agency_id"]
    )

    after = df.count()

    duplicates_removed = before - after

    # Standardize text columns by removing unnecessary spaces
    text_columns = [
        "agency_name",
        "abbreviation",
        "agency_type",
        "country"
    ]

    for column in text_columns:
        df = df.withColumn(
            column,
            trim(col(column))
        )

    # Convert numeric fields to integer types
    df = df.withColumn(
        "agency_id",
        col("agency_id").cast(IntegerType())
    )

    df = df.withColumn(
        "founding_year",
        col("founding_year").cast(IntegerType())
    )

    # Count missing agency country values
    missing_country = df.filter(
        col("country").isNull()
    ).count()

    # Count missing agency type values
    missing_type = df.filter(
        col("agency_type").isNull()
    ).count()

    # Get the total number of processed agencies
    processed_count = df.count()

    return df



def transform_launcher_configurations(df):

    # Select required launcher configuration fields
    df = df.select(
        col("id").alias("launcher_configuration_id"),
        col("name").alias("launcher_name"),
        col("full_name"),
        col("variant"),
        col("manufacturer.id").alias("manufacturer_id"),
        col("manufacturer.name").alias("manufacturer_name"),
        col("active"),
        col("reusable")
    )

    # Remove duplicate launcher configurations using the primary key
    before = df.count()

    df = df.dropDuplicates(
        ["launcher_configuration_id"]
    )

    after = df.count()

    duplicates_removed = before - after

    # Standardize text fields
    text_columns = [
        "launcher_name",
        "full_name",
        "variant",
        "manufacturer_name"
    ]

    for column in text_columns:
        df = df.withColumn(
            column,
            trim(col(column)).cast(StringType())
        )

    # Convert ID fields into integer types
    df = (
        df
        .withColumn(
            "launcher_configuration_id",
            col("launcher_configuration_id").cast(IntegerType())
        )
        .withColumn(
            "manufacturer_id",
            col("manufacturer_id").cast(IntegerType())
        )
    )


def transform_pads(df):

    # Select required pad fields
    df = df.select(
        col("id").alias("pad_id"),
        col("name").alias("pad_name"),
        col("active"),
        col("latitude"),
        col("longitude"),
        col("country.name").alias("country_name"),
        col("location.id").alias("location_id"),
        col("location.name").alias("location_name"),
        col("total_launch_count"),
        col("orbital_launch_attempt_count")
    )

    # Remove duplicate pad records using the primary key
    before = df.count()

    df = df.dropDuplicates(
        ["pad_id"]
    )

    duplicates_removed = before - df.count()

    # Standardize text columns
    text_columns = [
        "pad_name",
        "country_name",
        "location_name"
    ]

    for column in text_columns:
        df = df.withColumn(
            column,
            trim(col(column).cast(StringType()))
        )

    # Convert ID and numeric fields into appropriate types
    df = (
        df
        .withColumn(
            "pad_id",
            col("pad_id").cast(IntegerType())
        )
        .withColumn(
            "location_id",
            col("location_id").cast(IntegerType())
        )
        .withColumn(
            "latitude",
            col("latitude").cast(DoubleType())
        )
        .withColumn(
            "longitude",
            col("longitude").cast(DoubleType())
        )
        .withColumn(
            "total_launch_count",
            col("total_launch_count").cast(IntegerType())
        )
        .withColumn(
            "orbital_launch_attempt_count",
            col("orbital_launch_attempt_count").cast(IntegerType())
        )
    )

    return df



def transform_launches(df, agencies_df, launcher_configs_df,pads_df):
  

    # Select required fields from nested API structures
    df = df.select(
        col("id").alias("launch_id"),
        col("name").alias("launch_name"),
        col("net").alias("launch_datetime"),

        col("status.id").alias("status_id"),
        col("status.name").alias("status_name"),

        col("probability").alias("launch_probability"),
        col("weather_concerns"),
        col("failreason").alias("failure_reason"),

        col("launch_service_provider.id").alias("agency_id"),

        col("rocket.configuration.id")
        .alias("launcher_configuration_id"),

        col("pad.id").alias("pad_id"),

        col("mission.name").alias("mission_name"),
        col("mission.type").alias("mission_type"),

        # Keep orbit name temporarily
        # It will be converted into orbit_class later
        col("mission.orbit.name").alias("orbit_name")
    )



    # Count records before removing duplicates
    before = df.count()

    # Remove duplicate launches using launch_id
    df = df.dropDuplicates(["launch_id"])

    # Count records after removing duplicates
    after = df.count()

    duplicates_removed = before - after

    logger.info(
        f"Duplicate launches removed: {duplicates_removed}"
    )

    # Columns that contain text values
    text_columns = [
        "launch_name",
        "status_name",
        "mission_name",
        "mission_type",
        "failure_reason",
        "orbit_name"
    ]

    # Remove unnecessary spaces from text values
    for column in text_columns:
        df = df.withColumn(
            column,
            trim(col(column).cast(StringType()))
        )


    # Convert IDs and numeric values to required data types
    df = (
        df
        .withColumn(
            "status_id",
            col("status_id").cast(IntegerType())
        )
        .withColumn(
            "agency_id",
            col("agency_id").cast(IntegerType())
        )
        .withColumn(
            "launcher_configuration_id",
            col("launcher_configuration_id").cast(IntegerType())
        )
        .withColumn(
            "pad_id",
            col("pad_id").cast(IntegerType())
        )
        .withColumn(
            "launch_probability",
            col("launch_probability").cast(DoubleType())
        )
    )

    # Keep launch_id as string
    df = df.withColumn(
        "launch_id",
        col("launch_id").cast(StringType())
    )

    # Convert launch time into Spark timestamp
    # The API datetime contains timezone information
    df = df.withColumn(
        "launch_datetime",
        to_timestamp(col("launch_datetime"))
    )

    # Count records before validation
    before = df.count()

    # launch_id and launch_datetime are required fields
    df = df.filter(
        col("launch_id").isNotNull()
        & col("launch_datetime").isNotNull()
    )

    # Count records after validation
    after = df.count()

    invalid_records = before - after

    logger.info(
        f"Invalid launch records removed: {invalid_records}"
    )

    # Extract year from launch datetime
    df = df.withColumn(
        "launch_year",
        year(col("launch_datetime"))
    )

    # Extract month from launch datetime
    df = df.withColumn(
        "launch_month",
        month(col("launch_datetime"))
    )

    # Extract quarter from launch datetime
    df = df.withColumn(
        "launch_quarter",
        quarter(col("launch_datetime"))
    )


    # Convert status name to lowercase for comparison
    status_lower = lower(col("status_name"))

    # Categorize launch status
    # Partial Failure must be checked before Failure
    df = df.withColumn(
        "status_category",
        when(
            status_lower.contains("partial"),
            "Partial Failure"
        )
        .when(
            status_lower.contains("success"),
            "Successful"
        )
        .when(
            status_lower.contains("failure"),
            "Failure"
        )
        .when(
            col("status_name").isNull(),
            "Unknown"
        )
        .otherwise(
            "Other"
        )
    )


    # Mark successful launches as True
    df = df.withColumn(
        "is_successful",
        when(
            col("status_category") == "Successful",
            True
        )
        .otherwise(False)
    )


    # Convert orbit name to lowercase for comparison
    orbit_lower = lower(col("orbit_name"))

    # Earth orbit types
    earth_orbits = [
        "low earth orbit",
        "medium earth orbit",
        "polar orbit",
        "sun-synchronous orbit",
        "geosynchronous orbit",
        "elliptical orbit"
    ]

    # Suborbital type
    suborbital_types = [
        "suborbital"
    ]

    # Lunar and planetary orbit types
    planetary_orbits = [
        "lunar orbit",
        "lunar impactor",
        "lunar flyby",
        "mars flyby",
        "venus flyby"
    ]

    # Create broader orbit classification
    df = df.withColumn(
        "orbit_class",
        when(
            orbit_lower.isin(earth_orbits),
            "Earth Orbit"
        )
        .when(
            orbit_lower.isin(suborbital_types),
            "Suborbital"
        )
        .when(
            orbit_lower.isin(planetary_orbits),
            "Lunar/Planetary"
        )
        .when(
            orbit_lower == "heliocentric n/a",
            "Heliocentric"
        )
        .otherwise(
            "Unknown"
        )
    )

    # Create a window for each launch pad
    # Launches are ordered chronologically within each pad
    pad_window = (
        Window
        .partitionBy("pad_id")
        .orderBy("launch_datetime")
    )

    # Get the previous launch date from the same pad
    df = df.withColumn(
        "previous_pad_launch",
        lag("launch_datetime").over(pad_window)
    )

    # Calculate difference between current and previous launch
    # Convert seconds into days
    df = df.withColumn(
        "pad_turnaround_days",
        (
            unix_timestamp(col("launch_datetime"))
            - unix_timestamp(col("previous_pad_launch"))
        ) / 86400.0
    )


    # Create a separate window for each agency
    # Launches are ordered chronologically within each agency
    agency_window = (
        Window
        .partitionBy("agency_id")
        .orderBy("launch_datetime")
    )

    # Get the previous launch date from the same agency
    df = df.withColumn(
        "previous_agency_launch",
        lag("launch_datetime").over(agency_window)
    )

    # Calculate difference between current and previous launch
    # Convert seconds into days
    df = df.withColumn(
        "agency_launch_gap_days",
        (
            unix_timestamp(col("launch_datetime"))
            - unix_timestamp(col("previous_agency_launch"))
        ) / 86400.0
    )

    # creating dataframes containing valid IDS with foreign keys
    # combining launches table with remaining tables 
    valid_agencies = (
        agencies_df
        .select(
            col("agency_id").alias("valid_agency_id")
        )
        .dropDuplicates()
    )

    valid_launcher_configs = (
        launcher_configs_df
        .select(
            col("launcher_configuration_id")
            .alias("valid_launcher_configuration_id")
        )
        .dropDuplicates()
    )

    valid_pads = (
        pads_df
        .select(
            col("pad_id").alias("valid_pad_id")
        )
        .dropDuplicates()
    )

    # Join launches with valid agency IDs
    df = df.join(
        valid_agencies,
        df.agency_id == valid_agencies.valid_agency_id,
        "left"
    )

    # Join launches with valid launcher configuration IDs
    df = df.join(
        valid_launcher_configs,
        df.launcher_configuration_id
        == valid_launcher_configs.valid_launcher_configuration_id,
        "left"
    )

    # Join launches with valid pad IDs
    df = df.join(
        valid_pads,
        df.pad_id == valid_pads.valid_pad_id,
        "left"
    )

    # Setting invalid foreign keys to NULL
    df = (
        df
        .withColumn(
            "agency_id",
            when(
                col("valid_agency_id").isNotNull(),
                col("agency_id")
            ).otherwise(None)
        )
        .withColumn(
            "launcher_configuration_id",
            when(
                col("valid_launcher_configuration_id").isNotNull(),
                col("launcher_configuration_id")
            ).otherwise(None)
        )
        .withColumn(
            "pad_id",
            when(
                col("valid_pad_id").isNotNull(),
                col("pad_id")
            ).otherwise(None)
        )
    )

    # Remove temporary validation columns
    df = df.drop(
        "valid_agency_id",
        "valid_launcher_configuration_id",
        "valid_pad_id"
    )
 #casting derived columns
    df = (
        df
        .withColumn(
            "pad_turnaround_days",
            col("pad_turnaround_days").cast(DoubleType())
        )
        .withColumn(
            "agency_launch_gap_days",
            col("agency_launch_gap_days").cast(DoubleType())
        )
    )

    # Selecting final columns 
    df = df.select(
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
    )

    return df