# Assignment3_space_data_pipeline

## What the Pipeline Does

This project implements an end-to-end ETL pipeline for space mission and launch data.

The pipeline retrieves launch-related data from an external space API, preserves the original API response as raw data, transforms the data into clean and structured datasets, validates the processed data, and loads the final data into a relational SQL Server database.

The pipeline follows this flow:

```text
                           Space API
                              ↓
                           EXTRACT
                              ↓
                         Raw JSON Data
                              ↓
                          TRANSFORM
                              ↓
                       Processed Data
                              ↓
                          VALIDATE
                              ↓
                            LOAD
                              ↓
                    SQL Server Database
                              ↓
              Database Validation and Analytical Queries
```

The pipeline is designed to be repeatable and reliable. Raw API responses are stored separately from processed data so that transformation logic can be changed and the previously extracted data can be processed again without depending on another API request.

## API Used

The pipeline uses The Space Devs — Launch Library API to retrieve space launch and mission-related information.

API:

https://thespacedevs.com/llapi

Base API URL used by the extraction layer:

https://ll.thespacedevs.com/2.3.0

The pipeline currently retrieves data from the following endpoints:

- `launches/`
- `agencies/`
- `launcher_configurations/`
- `pads/`

These datasets are used to build the relational database structure required for launch analytics.

The `launches` dataset contains the main launch records, while agencies, launcher configurations, and pads provide related information that can be connected through foreign-key relationships during transformation and loading.

## Extraction Approach

The extraction layer retrieves data programmatically from The Space Devs Launch Library API using HTTP GET requests.

A reusable `extract_endpoint()` function is used so that the same extraction logic can be applied to multiple API endpoints.

### Extraction Process

1. Create an HTTP session using Python `requests`.
2. Send an HTTP GET request to the API endpoint.
3. Use a request timeout to prevent the pipeline from waiting indefinitely.
4. Check the HTTP response status code.
5. Retry temporary API failures such as:
   - 429
   - 500
   - 502
   - 503
   - 504
6. Use exponential backoff between retry attempts.
7. Handle request timeouts and other request exceptions.
8. Convert the API response into JSON.
9. Validate that the response contains the expected `results` field.
10. Save each API response page as a raw JSON file.
11. Follow the API-provided `next` URL to retrieve subsequent pages.
12. Track and log the number of records retrieved.
13. Continue the process until there are no more pages or the configured page limit is reached.

### Raw Data Preservation

The original API responses are stored separately under the raw-data layer:

```text
data/raw/

    launches/
        page_1.json
        page_2.json

    agencies/
        page_1.json
        ...

    launcher_configurations/
        page_1.json
        ...

    pads/
        page_1.json
        ...
```

The raw data is preserved so that the transformation layer can be re-run if transformation rules change in the future.

This avoids making the transformation process dependent on a fresh API request every time the transformation logic is modified.

## Transformation Approach

The transformation layer reads the preserved raw JSON data, cleans and standardizes the records, handles duplicates and missing values, validates relationships, creates derived fields, and saves the processed datasets as CSV files.

### Key Transformations

- Extract required fields from nested JSON objects.
- Remove duplicate records using primary keys.
- Standardize text and data types.
- Filter invalid launch records.
- Validate foreign-key relationships.
- Save transformed data to `data/processed/`.

### Derived Columns

- `launch_year` and `launch_month` — extracted from the launch date.
- `launch_quarter` — groups launches into Q1–Q4.
- `status_category` — groups launch statuses into Successful, Failure, Partial Failure, etc.
- `orbit_class` — groups detailed orbit types into broader categories such as Earth Orbit and Lunar/Planetary.
- `pad_turnaround_days` — days between consecutive launches from the same pad.
- `agency_launch_gap_days` — days between consecutive launches by the same agency.

## Validation Approach

The validation layer checks the processed datasets before they are loaded into SQL Server. It ensures that the transformed data has the expected structure, valid values, unique identifiers, and correct relationships between related datasets.

### Validation Checks

The following validations are performed:

- **Dataset validation** — verifies that processed datasets are not empty and contain the expected number of records.
- **Column validation** — checks that all required columns are present.
- **Duplicate validation** — checks for duplicate primary-key values.
- **Required-field validation** — verifies that important fields such as IDs, names, dates, and derived fields are not NULL.
- **Range validation** — validates numeric values such as latitude, longitude, launch probability, month, and quarter.
- **Category validation** — ensures that `status_category` and `orbit_class` contain only the expected values.
- **Derived-column validation** — verifies that `launch_year`, `launch_month`, `launch_quarter`, `pad_turnaround_days`, and `agency_launch_gap_days` contain valid values.
- **Foreign-key validation** — checks relationships between launches and the related agencies, launcher configurations, and pads.

### Foreign-Key Relationships

The following relationships are validated:

```text
launches.agency_id
        ↓
agencies.agency_id

launches.launcher_configuration_id
        ↓
launcher_configurations.launcher_configuration_id

launches.pad_id
        ↓
pads.pad_id
```

## Database Schema

The processed datasets are loaded into four relational tables in SQL Server:

- `agencies` — stores space agency information.
- `launcher_configurations` — stores launcher configuration and manufacturer information.
- `pads` — stores launch pad and location information.
- `launches` — stores launch-level information and references the related agency, launcher configuration, and pad.

### Primary Keys

Each table has a primary key:

- `agencies.agency_id`
- `launcher_configurations.launcher_configuration_id`
- `pads.pad_id`
- `launches.launch_id`

### Foreign Keys

The `launches` table contains foreign keys to the related dimension tables:

```text
launches.agency_id
        ↓
agencies.agency_id

launches.launcher_configuration_id
        ↓
launcher_configurations.launcher_configuration_id

launches.pad_id
        ↓
pads.pad_id
```

## Loading Strategy

The processed CSV files are loaded into SQL Server using `pyodbc`.

The tables are loaded in dependency order:

```text
agencies
    ↓
launcher_configurations
    ↓
pads
    ↓
launches
```

## Transaction Strategy

The loading process uses transactions at the batch level.

For each batch:

```text
Process records
      ↓
Database operations
      ↓
Success → COMMIT
      ↓
Failure → ROLLBACK
```

## Error Handling

The pipeline includes error handling across the extraction, transformation, validation, and loading stages.

Database operations handle `pyodbc.Error` exceptions and:

- Log the error.
- Roll back the affected batch.
- Stop the loading process.

The main pipeline also checks the return code of every pipeline step.

If any step fails, the pipeline stops immediately and the remaining steps are not executed.

```text
extract
   ↓
transform
   ↓
validate
   ↓
load
   ↓
failure
   ↓
pipeline stops
```

## Retry Strategy

The extraction layer implements retry handling for temporary API failures.

The API requests use:

- Request timeout
- Multiple attempts
- Retry delays
- Handling for connection errors
- Handling for request timeouts
- Handling for temporary server-side errors

Temporary failures are retried because they may recover on a later request.

Permanent client-side errors are not repeatedly retried.

Database loading does not automatically retry failed transactions. If a database batch fails, the batch is rolled back and the pipeline stops so that the failure can be investigated.

## Idempotency

The loading process is designed to be idempotent.

Before inserting a record, the loader checks whether the record already exists using its primary key.

```text
Record already exists
        ↓
      UPDATE

Record does not exist
        ↓
      INSERT
```

## Configuration

Database and pipeline configuration values are stored in the `.env` file instead of being hardcoded in the Python source code.

Current configuration:

```env
DB_DRIVER=ODBC Driver 17 for SQL Server
DB_SERVER=.\SQLEXPRESS
DB_DATABASE=student4
DB_TRUSTED_CONNECTION=yes
DB_TRUST_SERVER_CERTIFICATE=yes
BATCH_SIZE=500
```

## How to Run the Project

1. Install dependencies: `pip install -r requirements.txt`
2. Create the `.env` file in the project root.
3. Open SSMS and create the `student4` database.
4. Run the SQL scripts in this order: `agencies` → `launcher_configurations` → `pads` → `launches`.
5. From the project root, run: `python src\main.py`
6. Check the pipeline log at: `logs/pipeline.log`
7. Verify the loaded data in SSMS.
