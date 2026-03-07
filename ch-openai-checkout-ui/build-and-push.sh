#!/bin/bash

set -e 

AWS_REGION=${AWS_REGION:-"us-east-1"}
VERSION=$(node -p "require('./package.json').version")
REGISTRY=${REGISTRY:-"014071048740.dkr.ecr.us-east-1.amazonaws.com"}
IMAGE_NAME=${IMAGE_NAME:-"ch-openai-checkout-ui"}
IMAGE_TAG="${REGISTRY}/${IMAGE_NAME}:${VERSION}"

# Check for NPM auth token
if [ -z "$NPM_AUTH_TOKEN" ]; then
    echo "Error: NPM_AUTH_TOKEN environment variable is not set"
    echo "Set it with: export NPM_AUTH_TOKEN=<your-npm-token>"
    exit 1
fi

echo "Building Docker image: ${IMAGE_TAG}"

docker build \
    --platform linux/amd64 \
    --build-arg NPM_AUTH_TOKEN="${NPM_AUTH_TOKEN}" \
    -t "${IMAGE_TAG}" \
    .

echo "Successfully built image: ${IMAGE_TAG}"

echo "Pushing to ECR..."
aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$REGISTRY"
docker push ${IMAGE_TAG}
echo "Successfully pushed image to ECR"

echo "Triggering deployment..."
curl -X POST https://codepipeline-us-east-1.gbs-agentic-commerce-dev-nonprod.aws.fisv.cloud \
  -H "Content-Type: application/json" \
  -d "{
    \"ServiceName\": \"ch-openai-checkout-ui\",
    \"ServiceVersion\": \"${VERSION}\",
    \"TIER\": \"dev\",
    \"DesiredCount\": \"1\",
    \"ECSTaskSize\": \"Medium\"
  }"
echo ""
echo "Deployment triggered successfully"

# Increment patch version in package.json for next build
MAJOR=$(echo ${VERSION} | cut -d. -f1)
MINOR=$(echo ${VERSION} | cut -d. -f2)
PATCH=$(echo ${VERSION} | cut -d. -f3)
NEW_PATCH=$((PATCH + 1))
NEW_VERSION="${MAJOR}.${MINOR}.${NEW_PATCH}"
node -e "const fs = require('fs'); const pkg = require('./package.json'); pkg.version = '${NEW_VERSION}'; fs.writeFileSync('./package.json', JSON.stringify(pkg, null, 2) + '\n');"
echo "Updated package.json version to ${NEW_VERSION} for next build"

