#!/bin/bash
# Exit on any error and provide a custom error message
trap 'echo -e "${RED}An error occurred. Exiting...${NC}"; exit 1;' ERR

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Set environment variables
export PROJECT_ID
export KUBERNETES_CLUSTER_PREFIX
export REGION

# Teardown message
verbose_message "🧹 Starting teardown process..."

# Run terraform destroy
verbose_message "💥 Destroying Terraform-managed infrastructure..."
export GOOGLE_OAUTH_ACCESS_TOKEN=$(gcloud auth print-access-token)

read -p "Is your GKE cluster 'gke-autopilot' or 'gke-standard'? (Enter 'autopilot' or 'standard'): " GKE_FOLDER

# When prompted, type yes
verbose_message "💬 Type 'yes' when prompted to confirm the destruction..."

terraform -chdir=terraform/gke-${GKE_FOLDER} destroy -var project_id=${PROJECT_ID} -var region=${REGION} -var cluster_prefix=${KUBERNETES_CLUSTER_PREFIX}


# Find all unattached disks
verbose_message "🔍 Finding all unattached disks..."
export disk_list=$(gcloud compute disks list --filter="-users:* AND labels.name=${KUBERNETES_CLUSTER_PREFIX}-cluster" --format "value[separator=|](name,region)")

# Delete the disks
verbose_message "🗑️ Deleting unattached disks..."
for I in $disk_list; do
  disk_name=$(echo $I | cut -d'|' -f1)
  disk_region=$(echo $I | cut -d'|' -f2 | sed 's|.*/||')
  verbose_message "Deleting $disk_name in region $disk_region"
  gcloud compute disks delete $disk_name --region $disk_region --quiet
done

verbose_message "✅ Teardown process complete!"