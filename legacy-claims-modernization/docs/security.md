# Security Controls

## Overview

This document describes implemented security controls and remaining gaps for the Claims API training project.

## Authentication and Authorization

### Implemented

**JWT/OIDC Authentication:**
- Business API endpoints require valid JWT tokens
- Token validation includes:
  - Signature verification using JWKS from trusted issuer
  - Issuer (iss) validation
  - Audience (aud) validation
  - Expiration (exp) validation
  - Algorithm allowlist (RS256, RS384, RS512, ES256, ES384, ES512)
- JWKS caching with configurable TTL and automatic refresh on key rotation
- Health endpoints remain anonymous for load balancer checks

**Implementation Details:**
- Library: python-jose with cryptography backend
- JWKS endpoint URL validated and hard-coded (not user-supplied)
- Token parsing rejects tokens without required headers
- No homemade crypto or authentication logic

**Local Development:**
- Authentication can be disabled with AUTH_ENABLED=false
- **Never deploy with authentication disabled**
- Test tokens must match configured issuer and audience

### Not Implemented

- Fine-grained authorization (role-based access control)
- API rate limiting per user
- OAuth 2.0 token refresh
- Revocation checking

## Network Security

### Implemented

**VPC and Subnets:**
- Dedicated VPC with CIDR 10.0.0.0/16
- Public subnets (10.0.1.0/24, 10.0.2.0/24) for ALB only
- Private subnets (10.0.11.0/24, 10.0.12.0/24) for ECS tasks and database
- No public IPs assigned to ECS tasks or database

**Security Groups:**
- ALB security group:
  - Inbound HTTPS (443) from configurable allow-list CIDRs
  - Inbound HTTP (80) redirects to HTTPS
  - Outbound to ECS task security group only
- ECS task security group:
  - Inbound HTTP (8000) from ALB security group only
  - Outbound to database security group and internet (via NAT)
- Database security group:
  - Inbound PostgreSQL (5432) from ECS task security group only
  - Outbound: none required
  - Extension point: Add DMS replication instance SG for Week 2 migration

**TLS/HTTPS:**
- ALB requires HTTPS using ACM certificate
- HTTP listener redirects to HTTPS
- Certificate validation performed by ACM and ALB
- Database connections use TLS with sslmode=prefer (configurable)

**Internet Access:**
- Private subnets route through NAT Gateway for:
  - Pulling container images from ECR
  - Fetching secrets from Secrets Manager
  - Retrieving JWKS from identity provider
  - Sending logs to CloudWatch
  - Installing packages (bootstrap only)

### Not Implemented

- WAF rules for common attack patterns
- Network ACLs (using security groups only)
- VPC Flow Logs for network traffic analysis
- DDoS protection beyond standard AWS Shield
- Private Link / VPC Endpoints (using NAT for cost)

## Container Security

### Implemented

**Dockerfile:**
- Multi-stage build separates build and runtime
- Runtime uses python:3.11-slim-bookworm (Debian-based official image)
- Non-root user (uid 1000) runs application
- Minimal runtime dependencies (only libpq5)
- No compiler or build tools in runtime image
- PYTHONDONTWRITEBYTECODE=1 prevents .pyc files
- PYTHONUNBUFFERED=1 ensures log visibility

**ECR:**
- Image scanning enabled on push
- Immutable image tags enforced
- Lifecycle policy removes images after 10 retained
- Deployment uses image digest, not tags
- Encryption at rest with AES256

**ECS Task Configuration:**
- Read-only root filesystem attempted (Alembic requires writable /tmp)
- Unprivileged port (8000) for application
- No privileged mode
- No host network mode
- Resource limits (CPU and memory) defined

**Runtime:**
- Uvicorn runs as non-root user
- No shell available in runtime image (unless debugging)
- Signal handling for graceful shutdown
- Health checks restart unhealthy containers

### Not Implemented

- Distroless or scratch-based runtime image
- Fully read-only root filesystem
- AppArmor or SELinux profiles
- Runtime security monitoring
- Image signing and verification

## Secrets Management

### Implemented

**Secrets Manager:**
- Database credentials stored in Secrets Manager
- No credentials in:
  - Git repository
  - CloudFormation templates
  - Environment variables visible in ECS console
  - Application logs
  - Docker image layers
- ECS execution role retrieves secrets at task startup
- Task environment variables reference secrets by ARN

**Code:**
- .gitignore prevents committing .env files
- .dockerignore prevents including secrets in images
- .env.example provides safe template
- Logging redacts authorization headers
- Error responses hide database connection strings

### Not Implemented

- Automatic secret rotation with task refresh
- Runtime secret fetching (task restart required after rotation)
- Customer-managed KMS keys for Secrets Manager
- Audit logging of secret access

## IAM

### Implemented

**Principle of Least Privilege:**

**ECS Execution Role** (used by ECS service):
- ECR pull permissions (scoped to repository)
- CloudWatch Logs write permissions (scoped to log group)
- Secrets Manager read permissions (scoped to database secret)

**ECS Task Role** (used by application):
- Currently none (application makes no AWS API calls)
- Would add permissions for S3, SNS, etc. if needed

**Database EC2 Instance Role:**
- SSM Session Manager permissions only
- No S3, ECR, or other service access

**GitHub Actions Role** (OIDC federation):
- Trust policy restricts to specific repository and branch/environment
- ECR push permissions
- ECS task definition and service update permissions
- CloudFormation stack read permissions
- No IAM permission management

### Not Implemented

- Service Control Policies (SCPs) at organization level
- Permission boundaries
- Session tags for fine-grained access
- Automated IAM policy analysis and right-sizing

## Data Security

### Implemented

**Encryption:**
- EBS volumes encrypted with AWS-managed keys
- ECR encryption at rest
- Secrets Manager encryption at rest
- TLS in transit for:
  - Client to ALB (HTTPS required)
  - ECS task to database (PostgreSQL TLS)
  - ECS task to AWS services (SDK uses HTTPS)

**Database:**
- PostgreSQL authentication required
- Parameterized queries via SQLAlchemy (SQL injection protection)
- Connection pooling with validation and timeouts
- No raw SQL string concatenation

**Application:**
- Pydantic validation on all inputs
- Decimal type for currency (no floating point precision loss)
- Request size limits via FastAPI
- CORS disabled by default

**Logging:**
- Structured JSON logs with correlation IDs
- Sensitive data redacted:
  - Authorization headers
  - Database passwords
  - Request bodies (potentially contain PII)
- CloudWatch Logs retention: 7 days (configurable)

### Not Implemented

- Customer-managed KMS keys
- Field-level encryption for sensitive data
- Database encryption at rest (using EBS encryption only)
- Comprehensive PII detection and masking
- Log forwarding to SIEM

## EC2 Database Instance

### Implemented

**Access Control:**
- No SSH key pair assigned
- Systems Manager Session Manager for administration
- IMDSv2 required (prevents SSRF attacks)
- Security group restricts inbound to application tier
- Private subnet, no public IP

**Hardening:**
- Minimal OS (Amazon Linux 2023)
- Automatic security updates enabled
- No unnecessary services running
- PostgreSQL binds to private IP only

### Not Implemented

- Host-based intrusion detection
- File integrity monitoring
- OS-level audit logging to CloudWatch
- Regular vulnerability scanning

## Monitoring and Incident Response

### Implemented

**CloudWatch:**
- Logs from ECS tasks with correlation IDs
- Metrics for CPU, memory, request count, latency
- Alarms for:
  - Target health critical threshold
  - Elevated error rate
  - High resource utilization
- Dashboard for real-time visibility

**Structured Logging:**
- JSON format enables automated parsing
- Correlation IDs link requests across services
- Log levels (DEBUG, INFO, WARNING, ERROR)
- Exception stack traces captured

### Not Implemented

- Distributed tracing (X-Ray)
- Security event alerting
- Automated incident response
- Log aggregation and analysis platform
- Anomaly detection

## Supply Chain Security

### Implemented

**Dependencies:**
- Pinned versions in requirements.txt
- Lock file captures transitive dependencies
- Safety checks in CI pipeline (advisory)
- Trivy scanning for known vulnerabilities

**CI/CD:**
- GitHub Actions with OIDC (no long-lived credentials)
- Actions pinned to commit SHAs
- Branch protection on main
- Required checks before merge

### Not Implemented

- Dependency provenance verification
- Software bill of materials (SBOM)
- Build attestations and signing
- Supply chain level for software artifacts (SLSA)

## Compliance and Audit

### Implemented

**Traceability:**
- All deployments traceable to Git commits
- CloudFormation stack events recorded
- CloudWatch Logs retained
- IAM actions logged to CloudTrail (AWS default)

**Documentation:**
- Security controls documented
- Architecture diagrams maintained
- Deployment procedures recorded

### Not Implemented

- Automated compliance scanning (CIS, NIST)
- Regular security assessments
- Penetration testing
- Security champions program
- Formal incident response plan

## Production Gaps Summary

This training deployment implements foundational security controls but is **not production-ready**. To reach production:

1. **Enable WAF** with OWASP Top 10 rule sets
2. **Implement comprehensive authorization** beyond authentication
3. **Add VPC Flow Logs** and automated analysis
4. **Use customer-managed KMS keys** for encryption
5. **Enable X-Ray** for distributed tracing
6. **Implement secret rotation** with automatic task refresh
7. **Add SIEM integration** for security event correlation
8. **Regular vulnerability assessments** and penetration testing
9. **Disaster recovery** planning and testing
10. **Security training** for development and operations teams

## Security Review Checklist

Before deploying to production:

- [ ] Authentication enabled (AUTH_ENABLED=true)
- [ ] JWKS URL and issuer verified
- [ ] ACM certificate valid and auto-renewing
- [ ] ALB ingress CIDRs appropriately restricted
- [ ] Database passwords rotated from defaults
- [ ] IAM roles reviewed for least privilege
- [ ] CloudWatch Logs retention policy set
- [ ] Alarms configured and tested
- [ ] Security scanning results reviewed
- [ ] Secrets not in Git history
- [ ] Incident response contacts documented

## Contact

For security concerns or questions:
- Instructor email
- Security team contact (if applicable)
- AWS Support (for account-level issues)
