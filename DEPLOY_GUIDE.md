# Deployment Guide: Google Cloud Function for Git History Variation

This guide will walk you through the one-time setup required to deploy and run the Google Cloud Function that automatically varies your Git history.

This process uses a secure, passwordless authentication method called **Workload Identity Federation**, which is Google Cloud's recommended way to connect from GitHub Actions.

## 1. Prerequisites

- You have a Google Cloud Platform (GCP) project.
- You have the `gcloud` command-line tool installed and authenticated locally, or you can use the Google Cloud Shell.
- You have sufficient permissions in your GCP project to create service accounts, grant IAM roles, and enable APIs (e.g., `Owner` or `Editor` role).

## 2. Enable Required GCP APIs

First, enable the necessary APIs for your project.

```bash
# Replace YOUR_PROJECT_ID with your actual GCP Project ID
export PROJECT_ID="YOUR_PROJECT_ID"

gcloud services enable \
  iam.googleapis.com \
  iamcredentials.googleapis.com \
  cloudbuild.googleapis.com \
  cloudfunctions.googleapis.com \
  pubsub.googleapis.com \
  cloudscheduler.googleapis.com \
  --project=${PROJECT_ID}
```

## 3. Create a Service Account

This is the identity the GitHub Action will assume when running.

```bash
# The name for your new service account
export SA_NAME="github-history-faker-sa"

gcloud iam service-accounts create ${SA_NAME} \
  --display-name="GitHub History Faker Service Account" \
  --project=${PROJECT_ID}

# Get the full email of the service account for later use
export SERVICE_ACCOUNT=$(gcloud iam service-accounts list --filter="displayName='GitHub History Faker Service Account'" --format='value(email)' --project=${PROJECT_ID})
echo "Service Account created: ${SERVICE_ACCOUNT}"
```

Now, grant this service account the roles it needs to deploy and run the Cloud Function.

```bash
# Grant roles to the service account
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/cloudfunctions.developer"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/run.invoker" # Required for Gen 2 functions

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/iam.serviceAccountUser" # Allows the SA to act as itself during deployment
```

## 4. Set up Workload Identity Federation

This step securely links your GitHub repository to the service account you just created.

```bash
# Create the Workload Identity Pool
gcloud iam workload-identity-pools create "github-pool" \
  --project=${PROJECT_ID} \
  --location="global" \
  --display-name="GitHub Actions Pool"

# Get the full ID of the pool
export WORKLOAD_IDENTITY_POOL_ID=$(gcloud iam workload-identity-pools describe "github-pool" --project="${PROJECT_ID}" --location="global" --format="value(name)")

# Create the Workload Identity Provider within the pool
# Replace YOUR_GITHUB_OWNER/YOUR_GITHUB_REPO with your repository details
gcloud iam workload-identity-pools providers create-oidc "github-provider" \
  --project=${PROJECT_ID} \
  --location="global" \
  --workload-identity-pool="github-pool" \
  --display-name="GitHub Actions Provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
  --issuer-uri="https://token.actions.githubusercontent.com"

# Allow authentications from the provider to impersonate your service account
# This is the final binding step.
gcloud iam service-accounts add-iam-policy-binding ${SERVICE_ACCOUNT} \
  --project=${PROJECT_ID} \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/${WORKLOAD_IDENTITY_POOL_ID}/attribute.repository/YOUR_GITHUB_OWNER/YOUR_GITHUB_REPO"
```
**Note:** In the last command, replace `YOUR_GITHUB_OWNER/YOUR_GITHUB_REPO` with your repository's path (e.g., `my-cool-user/my-history-faker-repo`).

## 5. Create GitHub Repository Secrets

Go to your GitHub repository's settings page under **Secrets and variables > Actions** and create the following secrets.

- **`GCP_PROJECT_ID`**: Your Google Cloud Project ID.
- **`GCP_REGION`**: The region to deploy your function in (e.g., `us-central1`).
- **`GCP_FUNCTION_NAME`**: The name for your cloud function (e.g., `github-history-faker`).
- **`GCP_WORKLOAD_IDENTITY_PROVIDER`**: The full path of the Workload Identity Provider you created. You can get this by running:
  `gcloud iam workload-identity-pools providers describe "github-provider" --project="${PROJECT_ID}" --location="global" --workload-identity-pool="github-pool" --format="value(name)"`
- **`GCP_SERVICE_ACCOUNT`**: The email address of the service account you created (e.g., `github-history-faker-sa@your-project-id.iam.gserviceaccount.com`).
- **`GH_PAT`**: A GitHub Personal Access Token with `repo` scope. This is required by the function itself to push changes back to the repository.
- **`REPO_URL`**: The URL of your repository without `https://` (e.g., `github.com/YourUser/YourRepo.git`).

## 6. Create the Pub/Sub Topic and Scheduler

The final step is to set up a trigger that runs your function on a schedule.

1.  **Create the Pub/Sub Topic:**
    The deployment workflow is configured to use a topic named `github-history-faker`. Create it:
    ```bash
    gcloud pubsub topics create github-history-faker --project=${PROJECT_ID}
    ```

2.  **Create a Cloud Scheduler Job:**
    This job will publish a message to the Pub/Sub topic on a schedule. You can set it to run daily at a random time.

    Go to the [GCP Cloud Scheduler Console](https://console.cloud.google.com/cloudscheduler) and create a new job with the following settings:
    - **Frequency:** Use a cron expression. For a random time between 9am and 5pm UTC, you can't do it directly in cron. The simplest approach is to run it once a day, e.g., `0 9 * * *` (every day at 9am). The `is_time_to_work` logic inside the function will then handle whether it actually runs.
    - **Target type:** `Pub/Sub`
    - **Topic:** `github-history-faker`
    - **Message body:** `{}` (can be an empty JSON object)

---

Once all these steps are complete, you can trigger the deployment by pushing a change to your `main` branch. Subsequent runs will be handled by the Cloud Scheduler.
