<div align="center" id="top"> 
  <img src="image/logo.png" alt="Agent Habitat" width="300px"/>
  &#xa0;
</div>

<h1 align="center">Agent Habitat - Deploy GenAI Agents or Applications on GKE</h1>

<p align="center">
  <img alt="Github top language" src="https://img.shields.io/github/languages/top/gatolgaj/agent-habitat?color=56BEB8">
  <img alt="Github language count" src="https://img.shields.io/github/languages/count/gatolgaj/agent-habitat?color=56BEB8">
  <img alt="Repository size" src="https://img.shields.io/github/repo-size/gatolgaj/agent-habitat?color=56BEB8">
  <img alt="License" src="https://img.shields.io/github/license/gatolgaj/agent-habitat?color=56BEB8">
</p>

<p align="center">
  <a href="#about">About</a> &#xa0; | &#xa0; 
  <a href="#technologies">Technologies</a> &#xa0; | &#xa0;
  <a href="#requirements">Requirements</a> &#xa0; | &#xa0;
  <a href="#starting">Starting</a> &#xa0; | &#xa0;
  <a href="#teardown">Teardown</a> &#xa0; | &#xa0;
  <a href="#license">License</a> &#xa0; | &#xa0;
  <a href="https://github.com/gatolgaj" target="_blank">Author</a>
</p>

<br>

## About

Agent Habitat is a platform to build and deploy Generative AI (GenAI) agents or applications on Google Kubernetes Engine (GKE). All applications are containerized using Docker and have access to a shared Qdrant cluster for vector similarity search.

## Technologies

The following tools were used in this project:

- [Python](https://www.python.org/)
- [Google Cloud SDK (gcloud)](https://cloud.google.com/sdk/docs/install)
- [Terraform](https://www.terraform.io/)
- [Helm](https://helm.sh/)
- [Qdrant](https://qdrant.tech/)

## Requirements

Before starting, ensure you have the following:

- A Google Cloud project with billing enabled.
- Google Cloud SDK installed and configured.
- Terraform installed.
- Helm installed.
- Docker installed.
- Access to the cloned repository.

## Starting

### 1. Set Up Environment Variables

```sh
export PROJECT_ID=<your-google-cloud-project-id>
export REGION=<your-region> # e.g., us-central1
export KUBERNETES_CLUSTER_PREFIX=agent-habitat
```

### 2. Enable Required APIs

```sh
gcloud services enable cloudresourcemanager.googleapis.com compute.googleapis.com container.googleapis.com iamcredentials.googleapis.com gkebackup.googleapis.com
```

### 3. Grant IAM Roles

```sh
gcloud projects add-iam-policy-binding $PROJECT_ID --member="user:<your-email>" --role=<role>
```

Repeat the above command for the following roles:
- roles/storage.objectViewer
- roles/container.admin
- roles/iam.serviceAccountAdmin
- roles/compute.admin
- roles/gkebackup.admin
- roles/monitoring.viewer

### 4. Navigate to the Agent Habitat Directory

Ensure you are in the `agent_habitat` directory of the cloned repository:

```sh
git clone https://github.com/gatolgaj/agent-habitat.git 
```

### 5. Deploy the Agent Habitat Cluster

All the Steps required to setup the cluster is available in the script. Run the deployment script:

```sh
./setupGKE.sh
```

Follow the prompts to enter the necessary details if they are not already set as environment variables.

## Teardown

### 1. Teardown the Agent Habitat Cluster

Teardown script will make sure that you are not wasting resources or money .Run the teardown script:

```sh
./teardownGKE.sh
```

Follow the prompts to enter the necessary details if they are not already set as environment variables.

## Troubleshooting

- Ensure all necessary APIs are enabled in your Google Cloud project.
- Verify that billing is enabled for your Google Cloud project.
- Check that the necessary IAM roles are granted to your user account.
- If the scripts fail, ensure that all required tools (gcloud, terraform, helm) are installed and properly configured.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE.md) file for details.

## Authors

Made with :heart: by Deloitte Consulting BV -- Amsterdam, Netherlands

Authors: Shyam Sundar

&#xa0;

<a href="#top">Back to top</a>