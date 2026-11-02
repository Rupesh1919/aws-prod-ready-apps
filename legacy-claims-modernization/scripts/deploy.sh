#!/bin/bash
# Deployment script for Claims API to AWS
set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Parse arguments
ENVIRONMENT="${1:-dev}"
DEPLOY_STEP="${2:-all}"

log_info "Starting deployment for environment: ${ENVIRONMENT}"

# Validate AWS credentials
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    log_error "AWS credentials not configured or invalid"
    exit 1
fi

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=$(aws configure get region || echo "us-east-1")

log_info "AWS Account: ${AWS_ACCOUNT_ID}"
log_info "AWS Region: ${AWS_REGION}"

# Load parameters
PARAM_FILE="${PROJECT_ROOT}/cloudformation/parameters/${ENVIRONMENT}.json"
if [[ ! -f "${PARAM_FILE}" ]]; then
    log_error "Parameter file not found: ${PARAM_FILE}"
    exit 1
fi

# Deploy network stack
deploy_network() {
    log_info "Deploying network stack..."
    
    aws cloudformation deploy \
        --template-file cloudformation/01-network.yaml \
        --stack-name "${ENVIRONMENT}-claims-network" \
        --parameter-overrides EnvironmentName="${ENVIRONMENT}" \
        --tags Environment="${ENVIRONMENT}" Project=Claims \
        --no-fail-on-empty-changeset
    
    log_info "Network stack deployed successfully"
}

# Deploy ECR stack
deploy_ecr() {
    log_info "Deploying ECR repository..."
    
    aws cloudformation deploy \
        --template-file cloudformation/02-ecr.yaml \
        --stack-name "${ENVIRONMENT}-claims-ecr" \
        --parameter-overrides EnvironmentName="${ENVIRONMENT}" \
        --tags Environment="${ENVIRONMENT}" Project=Claims \
        --no-fail-on-empty-changeset
    
    log_info "ECR repository deployed successfully"
}

# Build and push Docker image
build_and_push() {
    log_info "Building and pushing Docker image..."
    
    # Get ECR repository URI
    REPO_URI=$(aws cloudformation describe-stacks \
        --stack-name "${ENVIRONMENT}-claims-ecr" \
        --query 'Stacks[0].Outputs[?OutputKey==`RepositoryUri`].OutputValue' \
        --output text)
    
    if [[ -z "${REPO_URI}" ]]; then
        log_error "Could not retrieve ECR repository URI"
        exit 1
    fi
    
    log_info "ECR Repository: ${REPO_URI}"
    
    # Login to ECR
    aws ecr get-login-password --region "${AWS_REGION}" | \
        docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
    
    # Build image
    IMAGE_TAG="$(date +%Y%m%d-%H%M%S)-$(git rev-parse --short HEAD 2>/dev/null || echo 'local')"
    
    log_info "Building image with tag: ${IMAGE_TAG}"
    docker build -t "${REPO_URI}:${IMAGE_TAG}" -t "${REPO_URI}:latest" .
    
    # Push image
    log_info "Pushing image to ECR..."
    docker push "${REPO_URI}:${IMAGE_TAG}"
    docker push "${REPO_URI}:latest"
    
    # Get image digest
    IMAGE_DIGEST=$(aws ecr describe-images \
        --repository-name "${ENVIRONMENT}-claims-api" \
        --image-ids imageTag="${IMAGE_TAG}" \
        --query 'imageDetails[0].imageDigest' \
        --output text)
    
    log_info "Image pushed successfully"
    log_info "Image URI: ${REPO_URI}@${IMAGE_DIGEST}"
    
    # Save for next steps
    echo "${REPO_URI}@${IMAGE_DIGEST}" > /tmp/claims-image-uri.txt
}

# Main deployment logic
case "${DEPLOY_STEP}" in
    network)
        deploy_network
        ;;
    ecr)
        deploy_ecr
        ;;
    build)
        build_and_push
        ;;
    all)
        deploy_network
        deploy_ecr
        build_and_push
        log_info "All deployment steps completed"
        log_warn "Next steps:"
        log_warn "1. Deploy legacy database stack (optional)"
        log_warn "2. Run database migrations"
        log_warn "3. Deploy application stack"
        ;;
    *)
        log_error "Unknown deployment step: ${DEPLOY_STEP}"
        echo "Usage: $0 <environment> [network|ecr|build|all]"
        exit 1
        ;;
esac

log_info "Deployment completed successfully!"
