# Legacy Claims API Modernization

Production-oriented AWS training project demonstrating containerization and deployment of a Python FastAPI application on AWS ECS Fargate.

## Project Overview

This repository contains a complete, hands-on training project for modernizing a legacy claims processing API. Built for a 2-hour instructor-led session teaching experienced engineers AWS containerization and deployment patterns.

**Key Technologies:**
- Python 3.11+ with FastAPI, SQLAlchemy, Alembic
- PostgreSQL for persistence
- Docker containers on Amazon ECS Fargate
- Application Load Balancer with HTTPS
- CloudWatch observability
- JWT/OIDC authentication
- Infrastructure as Code with CloudFormation

## Quick Start

### Prerequisites

- Python 3.11 or 3.12
- Docker and Docker Compose
- PostgreSQL client tools (psql)
- AWS CLI v2 configured
- AWS account with appropriate permissions
- ACM certificate for HTTPS
- OIDC/JWT identity provider (for authentication)

### Local Development

1. **Clone and setup**:
```bash
git clone <repository-url>
cd legacy-claims-modernization
```

2. **Create virtual environment and install dependencies**:
```bash
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
```

3. **Configure environment**:
```bash
cp .env.example .env
# Edit .env with your database credentials
# For local testing, AUTH_ENABLED=false is acceptable
```

4. **Start local environment with Docker Compose**:
```bash
docker-compose up -d postgres
```

5. **Run database migrations**:
```bash
python scripts/migrate.py
```

6. **Seed synthetic data**:
```bash
python scripts/seed.py
```

7. **Start the API**:
```bash
uvicorn claims_api.main:app --reload
```

8. **Access the application**:
- API: http://localhost:8000
- Health: http://localhost:8000/health/live
- OpenAPI Docs: http://localhost:8000/api/docs (if enabled)

### Running Tests

```bash
# Unit tests only
pytest tests/unit -v

# Integration tests (requires PostgreSQL)
pytest tests/integration -v -m integration

# All tests with coverage
pytest --cov=claims_api --cov-report=html

# Linting
ruff check claims_api tests

# Type checking
mypy claims_api
```

### Building the Container

```bash
# Build image
docker build -t claims-api:latest .

# Run locally
docker run -p 8000:8000 \
  -e DATABASE_HOST=host.docker.internal \
  -e DATABASE_PASSWORD=your_password \
  -e AUTH_ENABLED=false \
  claims-api:latest
```

## API Examples

**Create a claim** (requires authentication in production):
```bash
curl -X POST http://localhost:8000/api/claims \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "policy_reference": "POL-2024-123456",
    "claim_type": "ACCIDENT",
    "description": "Vehicle collision requiring front bumper repair",
    "claimed_amount": 2500.00
  }'
```

**Get a claim**:
```bash
curl http://localhost:8000/api/claims/{claim-id} \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**List claims**:
```bash
curl "http://localhost:8000/api/claims?offset=0&limit=20" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Update claim status**:
```bash
curl -X PATCH http://localhost:8000/api/claims/{claim-id}/status \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "status": "UNDER_REVIEW",
    "version": 1
  }'
```

## AWS Deployment

See [docs/deployment-guide.md](docs/deployment-guide.md) for complete deployment instructions.

**High-level steps:**

1. Deploy network infrastructure
2. Create ECR repository
3. Build and push container image
4. Deploy legacy database (optional for training)
5. Run database migrations
6. Deploy application stack
7. Configure DNS and test

## Project Structure

```
legacy-claims-modernization/
├── claims_api/           # Python application source
│   ├── api/             # FastAPI routes
│   ├── core/            # Configuration, logging, security
│   ├── db/              # Database session and repository
│   └── models/          # SQLAlchemy models and Pydantic schemas
├── alembic/             # Database migrations
├── cloudformation/      # AWS infrastructure templates
├── scripts/             # Deployment and management scripts
├── tests/               # Unit and integration tests
├── docs/                # Documentation
├── Dockerfile           # Container build definition
├── compose.yaml         # Local Docker Compose
└── requirements.txt     # Python dependencies
```

## Security Features

- HTTPS required on ALB
- JWT/OIDC authentication for business endpoints
- Secrets Manager for credentials
- Non-root container user
- Read-only container filesystem (where compatible)
- IMDSv2 required on EC2
- Security group ingress restrictions
- TLS for database connections
- Request correlation IDs
- No credentials in logs or Git

## Training Focus

This project teaches:

1. **Service Selection**: EC2 vs ECS vs Lambda tradeoffs
2. **Containerization**: Docker best practices, multi-stage builds
3. **Deployment**: ECS task definitions, rolling deployments, health checks
4. **Observability**: CloudWatch logs, metrics, dashboards, alarms
5. **Recovery**: Task replacement, deployment rollback, circuit breakers
6. **Security**: IAM roles, secrets management, network isolation
7. **Operations**: Database migrations, zero-downtime updates

## Production Gaps

This is a training deployment with documented limitations:

- Single NAT Gateway (no AZ redundancy)
- Simulated legacy database (single EC2 instance)
- Basic autoscaling configuration
- No advanced monitoring or distributed tracing
- No disaster recovery automation
- No multi-region setup
- Training-appropriate resource sizing

See [docs/production-gaps.md](docs/production-gaps.md) for details.

## Documentation

- [Architecture Overview](docs/architecture.md)
- [Service Decisions](docs/service-decisions.md)
- [Security Controls](docs/security.md)
- [Operations Runbook](docs/operations-runbook.md)
- [Instructor Guide](docs/instructor-guide.md)
- [Cost and Cleanup](docs/cost-and-cleanup.md)
- [Week 2 Migration Handoff](docs/week2-migration-handoff.md)

## License

This is a training project. Adapt as needed for your own use.

## Support

For issues or questions, see the instructor guide or open an issue in the repository.
