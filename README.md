# Assignment3_space_data_pipeline
## What the Pipeline Does

This project implements an end-to-end ETL pipeline for space mission and launch data.

The pipeline retrieves launch-related data from an external space API, preserves the original API response as raw data, transforms the data into clean and structured datasets, validates the processed data, and loads the final data into a relational SQL Server database.

The pipeline follows this flow:

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

The raw data is preserved so that the transformation layer can be re-run if transformation rules change in the future.

This avoids making the transformation process dependent on a fresh API request every time the transformation logic is modified.

### Development Extraction Limit

During development and testing, the launches endpoint is configured to retrieve two pages with a page size of 100 records.

This allows the pipeline to be tested using a controlled amount of data while retaining the pagination logic required for larger datasets.

The pipeline also includes logging, error handling, retry logic, transaction handling, idempotent loading, and validation checks to ensure that successful script execution does not automatically mean that the pipeline produced valid data.
