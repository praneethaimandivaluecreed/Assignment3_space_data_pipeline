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

The pipeline also includes logging, error handling, retry logic, transaction handling, idempotent loading, and validation checks to ensure that successful script execution does not automatically mean that the pipeline produced valid data.
