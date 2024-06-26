#!/bin/bash

# Exit on any error and provide a custom error message
trap 'echo -e "${RED}An error occurred. Exiting...${NC}"; exit 1;' ERR
# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to prompt for user input and read the response
prompt() {
  read -p "$(echo -e $GREEN"$1: "$NC)" response
  echo $response
}

# Verbose message function
verbose_message() {
  echo -e "${BLUE}$1${NC}"
}

# Check and set necessary environment variables
if [ -z "$PROJECT_ID" ]; then
  PROJECT_ID=$(prompt "🚀 Enter your Google Cloud Project ID")
else
  verbose_message "📦 Using existing PROJECT_ID: $PROJECT_ID"
fi

if [ -z "$EMAIL_ADDRESS" ]; then
  EMAIL_ADDRESS=$(prompt "📧 Enter your email address")
else
  verbose_message "📧 Using existing EMAIL_ADDRESS: $EMAIL_ADDRESS"
fi

if [ -z "$REGION" ]; then
  REGION=$(prompt "🌎 Enter the region (e.g., us-central1)")
else
  verbose_message "🌎 Using existing REGION: $REGION"
fi

if [ -z "$KUBERNETES_CLUSTER_PREFIX" ]; then
  KUBERNETES_CLUSTER_PREFIX=$(prompt "🔧 Enter the Kubernetes cluster prefix (e.g., qdrant)")
else
  verbose_message "🔧 Using existing KUBERNETES_CLUSTER_PREFIX: $KUBERNETES_CLUSTER_PREFIX"
fi

# Reminder to create Google Cloud project and enable billing
verbose_message "⚠️  Make sure you have created a Google Cloud project and enabled billing for the project."
read -p "Press [Enter] to continue after completing the above steps... 💡"

# Set environment variables
export PROJECT_ID
export KUBERNETES_CLUSTER_PREFIX
export REGION

# Set the Google Cloud project
verbose_message "🔧 Setting the Google Cloud project..."
gcloud config set project $PROJECT_ID

# Enable necessary APIs
verbose_message "🌐 Enabling necessary APIs..."
gcloud services enable cloudresourcemanager.googleapis.com compute.googleapis.com container.googleapis.com iamcredentials.googleapis.com gkebackup.googleapis.com

# Grant IAM roles to the user
verbose_message "🔑 Granting IAM roles to the user..."
ROLES=(
  "roles/storage.objectViewer"
  "roles/container.admin"
  "roles/iam.serviceAccountAdmin"
  "roles/compute.admin"
  "roles/gkebackup.admin"
  "roles/monitoring.viewer"
)

for ROLE in "${ROLES[@]}"; do
  verbose_message "👥 Granting role $ROLE..."
  gcloud projects add-iam-policy-binding $PROJECT_ID --member="user:$EMAIL_ADDRESS" --role=$ROLE
done

# Set up environment
verbose_message "🔍 Checking Helm version..."
helm version

if [ $? -ne 0 ]; then
  verbose_message "📥 Installing Helm..."
  curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
fi

# Assume the script is already in the qdrant directory
QDRANT_DIR=$(pwd)
verbose_message "📂 Current directory is $QDRANT_DIR"

# Create cluster infrastructure
verbose_message "🏗️ Creating cluster infrastructure..."
export GOOGLE_OAUTH_ACCESS_TOKEN=$(gcloud auth print-access-token)

terraform -chdir=terraform/gke-autopilot init
terraform -chdir=terraform/gke-autopilot apply -var project_id=${PROJECT_ID} -var region=${REGION} -var cluster_prefix=${KUBERNETES_CLUSTER_PREFIX}

# Connect to the cluster
verbose_message "🔗 Connecting to the cluster..."
gcloud container clusters get-credentials ${KUBERNETES_CLUSTER_PREFIX}-cluster --region ${REGION}

# Add Helm repository and create namespace
verbose_message "📦 Adding Helm repository and creating namespace..."
helm repo add qdrant https://qdrant.github.io/qdrant-helm
kubectl create ns ${KUBERNETES_CLUSTER_PREFIX}

# Create regional persistent SSD disk StorageClass
verbose_message "💾 Creating regional persistent SSD disk StorageClass..."
kubectl apply -n ${KUBERNETES_CLUSTER_PREFIX} -f manifests/01-regional-pd/regional-pd.yaml

# Deploy Qdrant and metrics configurations
verbose_message "🚀 Deploying Qdrant and metrics configurations..."
kubectl apply -n ${KUBERNETES_CLUSTER_PREFIX} -f manifests/03-prometheus-metrics/metrics-cm.yaml
helm install qdrant-database qdrant/qdrant -n ${KUBERNETES_CLUSTER_PREFIX} -f manifests/02-values-file/values.yaml
kubectl apply -n ${KUBERNETES_CLUSTER_PREFIX} -f manifests/01-regional-pd/ha-app.yaml

# Create PodMonitoring resource
verbose_message "📊 Creating PodMonitoring resource..."
kubectl apply -n ${KUBERNETES_CLUSTER_PREFIX} -f manifests/03-prometheus-metrics/pod-monitoring.yaml

# Create Cloud Monitoring dashboard
verbose_message "📈 Creating Cloud Monitoring dashboard..."
gcloud --project "${PROJECT_ID}" monitoring dashboards create --config-from-file monitoring/dashboard.json

verbose_message "🎉 Qdrant deployment on GKE is complete! 🎉"