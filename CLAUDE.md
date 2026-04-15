# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Growlithe is a compliance tool for serverless applications that enforces data policies through static and runtime checks. It analyzes application dataflow graphs using CodeQL and inserts policy assertions into the code.

Paper: [Growlithe: A Developer-Centric Compliance Tool for Serverless Applications (IEEE S&P 2025)](https://cirrus.ece.ubc.ca/papers/sp25_growlithe.pdf)

## Build & Development Commands

```bash
# Setup (Python 3.10 required)
python -m venv venv
source venv/bin/activate
pip install -e .

# For JavaScript functions
npm install --prefix growlithe/graph/adg/js

# Run all tests
python -m unittest -v

# Run a single test file
python -m unittest tests.test_cli -v

# Format code (run before commits)
black .

# Or use pre-commit hooks
pre-commit install

# Docker alternative
docker build -t growlithe .
docker run -it growlithe bash
```

## CLI Usage

```bash
growlithe --config growlithe_config.yaml analyze  # Analyze source code, generate ADG
growlithe --config growlithe_config.yaml apply    # Apply policies after configuring policy_spec.json
```

## Architecture

### Core Pipeline

1. **Analyze Phase** (`growlithe/cli/analyze.py`):
   - Creates CodeQL database from source code
   - Runs CodeQL queries to extract dataflows and metadataflows
   - Parses cloud config (SAM/Terraform) to identify functions and resources
   - Generates Application Dependency Graph (ADG)
   - Outputs `policy_spec.json` template for user policy configuration

2. **Apply Phase** (`growlithe/cli/apply.py`):
   - Loads analyzed graph from pickle files
   - Reads user-configured policies from `policy_spec.json`
   - Runs taint tracking to propagate labels through dataflows
   - Inserts policy assertions into the application code
   - Updates cloud configuration (SAM/Terraform)

### Key Components

- **ADG (Application Dependency Graph)** (`growlithe/graph/adg/`): Core data structures for representing dataflow graphs
  - `Graph`: Contains nodes, edges, functions, and resources
  - `Node`: Represents data sources/sinks (S3_BUCKET, DYNAMODB_TABLE, PARAM, RETURN, etc.)
  - `Edge`: Connects nodes with types DATA, METADATA, or INDIRECT
  - `Function`: Lambda function with AST and code location
  - `Resource`: Cloud resources (S3, DynamoDB, Lambda)

- **CodeQL Analysis** (`growlithe/graph/codeql/`): Static analysis using CodeQL
  - `intra_function_analyzer.py`: Creates CodeQL databases and runs queries
  - `python/queries/`: CodeQL queries for Python (dataflows.ql, metadataflows.ql)
  - `Config.qll`: Updated dynamically with function list to analyze

- **Config Parsers** (`growlithe/graph/parsers/`): Parse cloud infrastructure configs
  - `sam.py`: AWS SAM template parser
  - `terraform.py`: Terraform config parser
  - `sarif.py`: CodeQL SARIF output parser

- **Enforcement** (`growlithe/enforcement/`):
  - `taint/taint_tracker.py`: Inserts taint tracking code into AST
  - `policy/policy_enforcer.py`: Policy assertion generation
  - `policy/platform_predicates/`: AWS/GCP-specific runtime predicates

### Configuration

- **`growlithe_config.yaml`**: Main config file specifying app_name, src_dir, app_config_path, app_config_type (SAM/Terraform), cloud_provider (AWS/GCP)
- **`growlithe/common/dev_config.py`**: Development flags (CREATE_CODEQL_DB, RUN_CODEQL_QUERIES, etc.)
- **`growlithe/config.py`**: Singleton Config class; update `get_defaults()` for debugging

## CodeQL Setup

CodeQL CLI must be installed and on PATH. Fetch dependencies:
```bash
cd growlithe/graph/codeql/python/queries && codeql pack analyze
```

## Supported Platforms

- Cloud providers: AWS, GCP
- Config types: SAM, Terraform
- Languages: Python (primary), JavaScript (partial)
