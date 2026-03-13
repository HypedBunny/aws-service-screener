# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Service Screener (v2.4.0) is an open-source AWS environment assessment tool that runs automated read-only checks against AWS services and generates recommendations based on the AWS Well-Architected Framework. It is designed to run in AWS CloudShell.

## Running the Tool

```bash
# Setup (CloudShell or local)
python3 -m venv .
source bin/activate
pip install -r requirements.txt
alias screener='python3 $(pwd)/main.py'

# Basic scan
screener --regions ap-southeast-1

# Scan specific services
screener --regions ap-southeast-1 --services s3,ec2,iam

# With beta features (concurrent checks, API buttons in HTML)
screener --regions ap-southeast-1 --beta 1

# With tag filtering
screener --regions ap-southeast-1 --tags env=prod%department=hr

# Local development with named profile
screener --regions ap-southeast-1 --profile myprofile
```

There is no formal test framework. Manual testing is done by running scans against real AWS accounts.

## Architecture

**Execution flow:** `main.py` → `Screener.scanByService()` (multiprocessing pool, 4 workers) → per-service `Service.advise()` → per-resource `Evaluator.run()` → auto-discovered `_check*()` methods → `Reporter` → HTML/JSON/Excel output.

### Two-class model per service

1. **Service class** (`services/{svc}/{Svc}.py` extends `services/Service.py`): Enumerates AWS resources via boto3, handles pagination and tag filtering, orchestrates driver execution.
2. **Driver/Evaluator class** (`services/{svc}/drivers/{Driver}.py` extends `services/Evaluator.py`): Contains `_check*()` methods that evaluate a single resource. Results stored as `self.results['CheckName'] = [status, value]` where status is `-1` (attention), `0` (info), or `1` (pass).

### Reporter configuration

Each service has a `{svc}.reporter.json` mapping check names to metadata:
```json
{
    "CheckName": {
        "category": "S|R|O|P|C",
        "^description": "Text with {$COUNT} placeholder",
        "shortDesc": "Brief text",
        "criticality": "H|M|L",
        "downtime": 0, "slowness": 0, "additionalCost": 0, "needFullTest": 0,
        "ref": ["[Link text]<https://url>"]
    }
}
```
Categories map to Well-Architected pillars: S(ecurity), R(eliability), O(perational), P(erformance), C(ost).

### Dynamic service loading

`Screener.getServiceModuleDynamically()` imports `services.{folder}.{ClassName}` where `ClassName = service.title()`. No explicit registration needed — just create the folder structure. The default services list is in `utils/ArguParser.py` `CLI_ARGUMENT_RULES["services"]["default"]`.

Special cases: `lambda` uses folder `lambda_` (Python keyword). Global services (`iam`, `cloudfront`) scan only once in us-east-1.

### Config system

`utils/Config.py` is a static key-value cache (`Config.set`/`Config.get`). Stores boto3 session (`ssBoto`), STS info, rules, scanned resources, and per-service caches.

### Output

Reports go to `adminlte/aws/{account-id}/`: `index.html` (dashboard), `api-raw.json`, `api-full.json`, Excel workbook, `all.csv`. Packaged as `output.zip`.

## Creating New Services

### Scaffolding script (basic)
```bash
python3 CreateService.py -s {service-name}
```
Generates boilerplate in `services/{service}/` from templates in `utils/services-template/`.

### AI-assisted scaffolding (preferred method)

Use the prompt templates in `q-dev/prompts/templates/` to generate services. **Always follow this workflow — do not manually write service code from scratch.**

#### Step 1: Define checks (prompt-template-define.md)
1. Copy the template: `cp q-dev/prompts/templates/prompt-template-define.md ./prompt-template-define-{service}.md`
2. Replace `{AWS_SERVICE_NAME}` with the target service (e.g., `ECS`)
3. Read `q-dev/context.md` and `docs/DevelopmentGuide.md` for project context
4. Execute the template instructions — this generates a reporter JSON in `docs/generated_reporter.json`
5. Reference `services/cloudwatch/cloudwatch.reporter.json` as the example format

#### Step 2: Create service (prompt-template-create-service.md)
1. Copy the template: `cp q-dev/prompts/templates/prompt-template-create-service.md ./prompt-template-create-service-{service}.md`
2. Replace `{SERVICE_NAME}` with the service name and `{REPORTER_JSON_CONTENT}` with the generated reporter JSON
3. Execute the template instructions — this generates the service class, driver classes, and reporter JSON
4. Copy the reporter JSON to `services/{service}/{service}.reporter.json`

#### Step 3: Register the service
Add the service name to the default services list in `utils/ArguParser.py` → `CLI_ARGUMENT_RULES["services"]["default"]`.

#### Extending an existing service (prompt-template-extend-service.md)
1. Copy: `cp q-dev/prompts/templates/prompt-template-extend-service.md ./prompt-template-extend-service-{service}.md`
2. Replace `{SERVICE_NAME}` and `{NEW_REPORTER_JSON_CONTENT}` with new checks to add
3. Execute — this adds new `_check*` methods and reporter entries without modifying existing ones

## Conventions

- Check methods **must** start with `_check` and use camelCase: `_checkEncryptionAtRest` (codebase migrated from PHP)
- Driver classes **must** set `self._resourceName` (string) — used for CSV tracking and report identifiers
- Result keys in drivers must exactly match keys in the reporter JSON
- `Config.extractDriversClassPrefix()` extracts first 3 chars of driver class name as prefix (special handling for `s3`, `elastic*`, `cloud*`)
- Resource identifiers in `advise()` use format `ResourceType::name` (e.g., `Cluster::my-cluster`)
- Use `_pi(group, resource)` from `utils/Tools.py` for progress indicators
- Handle `botocore.exceptions.ClientError` in checks; skip on `AccessDenied`
- Use `self.ssBoto.client()` for boto3 clients, `self.bConfig` for regional config with retries
