# Instructor Guide - Legacy Claims API Modernization

## Training Session Overview

**Duration**: 2 hours
**Audience**: 2 experienced software engineers
**Focus**: Containerization and AWS deployment patterns
**Format**: Live Zoom session with hands-on demonstration

## Learning Objectives

By the end of this session, participants will be able to:

1. Evaluate AWS compute services (EC2, ECS, Lambda, EKS) and justify choices
2. Containerize an existing application with production-oriented practices
3. Deploy a containerized application to ECS Fargate
4. Configure observability with CloudWatch
5. Demonstrate recovery from task failure and deployment rollback
6. Understand security boundaries and operational responsibilities
7. Use infrastructure as code without writing YAML during the session

## Pre-Session Preparation (Instructor)

### 1 Week Before

- [ ] Verify AWS account access and permissions
- [ ] Request ACM certificate for demo domain
- [ ] Configure test OIDC provider or prepare mock tokens
- [ ] Deploy network stack
- [ ] Deploy ECR repository
- [ ] Test full deployment in staging

### 1 Day Before

- [ ] Build and push container image to ECR
- [ ] Deploy legacy database stack
- [ ] Run migrations and seed data
- [ ] Verify authentication configuration
- [ ] Test all API endpoints
- [ ] Prepare fallback slides if cloud access fails
- [ ] Test Zoom screen sharing and terminal visibility

### 1 Hour Before

- [ ] Verify application is running and healthy
- [ ] Prepare terminal windows and browser tabs
- [ ] Open CloudWatch dashboard
- [ ] Have AWS CLI ready in terminal
- [ ] Test DNS resolution
- [ ] Prepare Postman or curl commands for API testing

## Session Outline

### Segment 1: Context and Legacy Application (0-15 min)

**Topics:**
- Insurance claims processing background
- Current pain points with legacy deployment
- Modernization goals and constraints
- Quick architecture walkthrough

**Demo:**
1. Show local Docker Compose environment
2. Start application: `docker-compose up`
3. Create a claim via API
4. Show data persisting in PostgreSQL
5. Explain why this needs AWS deployment

**Key Points:**
- Legacy app works but deployment is manual and fragile
- Need scalability, observability, and standardized operations
- Business logic shouldn't change during modernization
- Focus is infrastructure and deployment, not rewriting the app

**Questions for Participants:**
- "What deployment challenges have you faced with legacy applications?"
- "What would you prioritize in a modernization project?"

### Segment 2: AWS Service Selection (15-35 min)

**Topics:**
- EC2 vs ECS Fargate vs Lambda vs EKS
- When to choose each service
- Cost, operational complexity, and control tradeoffs

**Discussion Framework:**

| Service | Best For | Operational Overhead | Cost Model | When to Avoid |
|---------|----------|---------------------|------------|---------------|
| EC2 | Full control, legacy compatibility | High | Per-instance, always running | Undifferentiated heavy lifting |
| ECS Fargate | Containers without cluster management | Medium | Per-task, pay for use | Need Kubernetes, advanced orchestration |
| Lambda | Event-driven, stateless functions | Low | Per-invocation | Long-running, stateful, large dependencies |
| EKS | Kubernetes ecosystem, advanced orchestration | Very High | Cluster + worker costs | Simple workloads, small teams |

**Interactive Exercise:**
Present 3 scenarios and have participants recommend a service:

1. **Batch Image Processing**
   - Triggered by S3 uploads
   - Runs 30 seconds per image
   - Sporadic traffic
   - **Answer**: Lambda

2. **Legacy Java Monolith**
   - Runs on Tomcat
   - Heavy in-memory caching
   - Long startup time (2+ minutes)
   - **Answer**: EC2 or ECS with large tasks

3. **API Microservices**
   - Multiple containerized services
   - Need rolling deployments
   - Want managed infrastructure
   - No Kubernetes requirement
   - **Answer**: ECS Fargate (our project!)

**Demo:**
- Show claims-api running on Fargate
- Open ECS console and explain task definition
- Show CloudFormation template structure (don't write from scratch)

**Key Points:**
- No single "best" service - depends on requirements
- Fargate removes cluster management overhead
- Pay for what you use, scale to zero (with adjustments)
- CloudFormation captures decisions as code

### Segment 3: Deployment Walkthrough (35-70 min)

**Topics:**
- Network architecture (VPC, subnets, security groups)
- ECR and container image management
- ECS task definition and service configuration
- Secrets management
- Health checks and load balancing

**Demonstration Sequence:**

#### Network Infrastructure (5 min)
```bash
# Show deployed network stack
aws cloudformation describe-stacks --stack-name dev-claims-network

# Explain outputs
aws cloudformation describe-stacks --stack-name dev-claims-network \
  --query 'Stacks[0].Outputs' --output table
```

**Explain:**
- 2 AZs for redundancy
- Public subnets for ALB
- Private subnets for ECS tasks and database
- NAT Gateway for outbound internet (ECR, Secrets Manager, JWKS)

#### Container Image (10 min)
```bash
# Show Dockerfile
cat Dockerfile

# Multi-stage build explanation
# - Builder stage: compiles dependencies
# - Runtime stage: minimal production image
# - Non-root user
# - Read-only filesystem (mostly)

# Build and push (if time permits, or show pre-built)
docker build -t claims-api:demo .
```

**Key Points:**
- Multi-stage builds reduce final image size
- Non-root user improves security
- Immutable tags and digest-based deployment
- ECR scanning catches vulnerabilities

#### Database Setup (10 min)
```bash
# Show database stack (legacy simulation)
aws cloudformation describe-stack-resources \
  --stack-name dev-claims-database

# Connect via Session Manager
aws ssm start-session --target i-xxxxxxxxxxxxx

# Inside the instance
sudo -u postgres psql -d claims_db -c "\dt"
```

**Explain:**
- Simulates on-prem database (not RDS yet - Week 2 topic)
- No SSH, no public IP - Session Manager only
- Security group restricted to application tier
- Credentials in Secrets Manager
- Logical replication configured for future DMS migration

#### Application Deployment (15 min)
```bash
# Show ECS service
aws ecs describe-services \
  --cluster dev-claims-cluster \
  --services dev-claims-api

# Show task definition
aws ecs describe-task-definition \
  --task-definition dev-claims-api:5 \
  --query 'taskDefinition.{cpu:cpu,memory:memory,image:containerDefinitions[0].image}'

# Show running tasks
aws ecs list-tasks --cluster dev-claims-cluster --service-name dev-claims-api
```

**Explain:**
- Task definition: Docker image, CPU/memory, environment variables
- Execution role: Pull image, get secrets, write logs
- Task role: Application permissions (none needed currently)
- Service: Desired count, deployment strategy, health checks
- ALB target group integration

#### Smoke Testing (10 min)
```bash
# Health checks
curl https://claims-api-dev.example.com/health/live
curl https://claims-api-dev.example.com/health/ready

# Create claim (with authentication)
export TOKEN="your-jwt-token"
curl -X POST https://claims-api-dev.example.com/api/claims \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "policy_reference": "POL-2024-DEMO",
    "claim_type": "ACCIDENT",
    "description": "Demo claim created during training session",
    "claimed_amount": 1500.00
  }'

# Get claim
CLAIM_ID="<from-response>"
curl https://claims-api-dev.example.com/api/claims/$CLAIM_ID \
  -H "Authorization: Bearer $TOKEN"
```

**Key Points:**
- Liveness: process health, no DB dependency
- Readiness: includes DB check, used by ALB
- Authentication required for business endpoints
- Correlation IDs in responses

### Segment 4: Observability and Testing (70-90 min)

**Topics:**
- CloudWatch Logs and log groups
- Structured JSON logging
- CloudWatch metrics and alarms
- Dashboard for real-time monitoring

**Demo:**

#### Logs (5 min)
```bash
# Show log groups
aws logs describe-log-groups --log-group-name-prefix /ecs/dev-claims

# Tail logs
aws logs tail /ecs/dev-claims-api --follow

# Find specific request by correlation ID
aws logs filter-log-events \
  --log-group-name /ecs/dev-claims-api \
  --filter-pattern '{ $.correlation_id = "abc-123-xyz" }'
```

**Explain:**
- Structured JSON enables filtering and searching
- Correlation IDs link request across logs
- Log retention configured (7 days in training)

#### Metrics and Alarms (5 min)
- Open CloudWatch Console
- Show Container Insights metrics
- Demonstrate custom dashboard
- Explain alarm thresholds

**Dashboard Metrics:**
- Request count and latency (ALB)
- Target health (ALB)
- CPU and memory utilization (ECS)
- Error rate (custom metric if implemented)

#### Task Failure Recovery (10 min)
```bash
# Stop a task to simulate failure
TASK_ARN=$(aws ecs list-tasks --cluster dev-claims-cluster \
  --service-name dev-claims-api --query 'taskArns[0]' --output text)

aws ecs stop-task --cluster dev-claims-cluster --task $TASK_ARN \
  --reason "Instructor demo: simulating task failure"

# Watch ECS service replace it
watch aws ecs describe-services \
  --cluster dev-claims-cluster \
  --services dev-claims-api \
  --query 'services[0].{desired:desiredCount,running:runningCount,pending:pendingCount}'
```

**Observe:**
- ECS detects unhealthy task
- New task launched automatically
- ALB removes failed task from rotation
- Service maintains desired count
- No downtime if multiple tasks running

### Segment 5: Deployment Rollback Demo (90-110 min)

**Topics:**
- Deployment strategies
- Health check integration
- Circuit breaker behavior
- Rollback procedures

**Demo:**

#### Deploy Unhealthy Version (15 min)

Prepare a broken task definition ahead of time:
- Set invalid environment variable causing startup failure
- Or point to non-existent database

```bash
# Update service with bad task definition
aws ecs update-service \
  --cluster dev-claims-cluster \
  --service dev-claims-api \
  --task-definition dev-claims-api-broken:1

# Watch deployment fail
watch aws ecs describe-services \
  --cluster dev-claims-cluster \
  --services dev-claims-api \
  --query 'services[0].deployments'
```

**Observe:**
- New tasks start but fail health checks
- Circuit breaker detects failure
- Service automatically stops deployment
- Original tasks remain running
- **No user impact** - bad version never receives traffic

**Explain:**
- ECS deployment circuit breaker
- Minimum healthy percent configuration
- ALB health checks protect against bad deployments
- Rollback is just deploying previous good task definition

#### Manual Rollback (5 min)
```bash
# Rollback to previous task definition
aws ecs update-service \
  --cluster dev-claims-cluster \
  --service dev-claims-api \
  --task-definition dev-claims-api:5  # Good version

# Verify recovery
curl https://claims-api-dev.example.com/health/ready
```

**Key Points:**
- Infrastructure rollback (CloudFormation) vs application rollback (ECS task def)
- Database migrations are one-way (need forward-compatible changes)
- Importance of immutable infrastructure
- Blue/green deployments for zero-downtime

### Segment 6: Wrap-up and Q&A (110-120 min)

**Topics:**
- Cost discussion
- Security boundaries review
- Production gaps and next steps
- Week 2 preview (database migration)

**Cost Breakdown:**
- Fargate tasks: ~$0.04/hour per task (512 CPU, 1GB mem) × 2 × 24 = ~$2/day
- ALB: ~$0.025/hour + data processing = ~$20/month
- NAT Gateway: ~$0.045/hour + data processing = ~$35/month
- ECR: Storage negligible with lifecycle policy
- RDS (Week 2): ~$30/month for db.t4g.micro
- **Total estimate**: $100-150/month for training environment

**Cleanup Instructions:**
```bash
# Delete stacks in reverse order
aws cloudformation delete-stack --stack-name dev-claims-app
aws cloudformation delete-stack --stack-name dev-claims-database
aws cloudformation delete-stack --stack-name dev-claims-ecr
aws cloudformation delete-stack --stack-name dev-claims-network

# Verify deletion
aws cloudformation list-stacks --stack-status-filter DELETE_COMPLETE
```

**Production Gaps to Discuss:**
1. Single NAT Gateway (should be per-AZ in prod)
2. Legacy database simulation (moving to RDS in Week 2)
3. Basic autoscaling (need more sophisticated metrics)
4. No distributed tracing
5. Training-sized resources

**Optional Assignment:**
"Add a new claim type and test end-to-end deployment including:
- Code change
- Docker build
- Push to ECR
- Deploy to ECS
- Verify in CloudWatch Logs"

**Week 2 Preview:**
- AWS Database Migration Service (DMS)
- Setting up RDS PostgreSQL
- Full-load plus CDC migration
- Minimal downtime cutover
- Validation and rollback planning

## Fallback Plan (Cloud Issues)

If AWS access fails or deployments are too slow:

1. **Run everything locally** with Docker Compose
2. **Walk through CloudFormation templates** with slides
3. **Show pre-recorded deployment** video
4. **Discuss architecture** using diagrams
5. **Live code review** of application implementation

Have slides ready with:
- Architecture diagrams
- CloudFormation resource graphs
- ECS console screenshots
- CloudWatch dashboard examples
- Cost breakdowns

## Common Questions and Answers

**Q: Why not use RDS from the start?**
A: Week 2 focuses on database migration. Starting with EC2 PostgreSQL simulates a real legacy database migration scenario.

**Q: Why not use VPC Endpoints instead of NAT Gateway?**
A: Cost and complexity tradeoff. NAT Gateway is $35/month. Interface endpoints are $7/month each, and we'd need several (ECR API, ECR DKR, S3, Secrets Manager, CloudWatch Logs). For training, NAT is simpler. Production might justify endpoints.

**Q: Why synchronous database calls in FastAPI?**
A: Keeping it simple for training. Async adds complexity without significant benefit for this workload pattern. Blocking DB calls with async handlers would be worse.

**Q: What about database connection pooling with multiple tasks?**
A: Each task has its own connection pool (SQLAlchemy). Database server manages concurrent connections. RDS proxy would help with connection management at scale.

**Q: How do we handle secrets rotation?**
A: Current implementation reads secrets at task startup. Rotation requires task refresh. Better pattern: fetch secrets periodically at runtime, but adds complexity.

**Q: What about CORS?**
A: Disabled by default. Enable in application code if frontend requires it, with explicit allowed origins.

## Materials Checklist

- [ ] GitHub repository access for participants
- [ ] AWS Console access (read-only acceptable)
- [ ] Sample JWT tokens for testing
- [ ] Postman collection or curl commands
- [ ] CloudFormation templates
- [ ] Architecture diagrams
- [ ] Cost calculator spreadsheet
- [ ] Week 2 handoff document

## Success Criteria

Participants should be able to:
- [ ] Explain when to choose ECS Fargate vs other compute options
- [ ] Describe the deployment flow from code to running container
- [ ] Find and interpret CloudWatch Logs for a specific request
- [ ] Understand how ECS maintains service availability
- [ ] Demonstrate recovery from task failure
- [ ] List remaining production gaps

## Post-Session

- [ ] Share repository with complete code
- [ ] Send optional assignment description
- [ ] Provide Week 2 preparation materials
- [ ] Share cost tracking spreadsheet
- [ ] Collect feedback on session

## Additional Resources

- [AWS ECS Best Practices](https://docs.aws.amazon.com/AmazonECS/latest/bestpracticesguide/)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [Container Security Guide](https://docs.docker.com/develop/security-best-practices/)
- [CloudFormation User Guide](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/)
