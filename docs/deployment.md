# Manual AWS deployment

This runbook documents the existing MVP deployment and the repeatable steps for publishing a future frontend build. It does not create resources, grant permissions, or replace an infrastructure-as-code workflow.

## Current deployment

- Region: `us-east-2`
- Frontend URL: <https://d1jzmtqwkf5hmn.cloudfront.net>
- API base URL: <https://apgc1a8kvi.execute-api.us-east-2.amazonaws.com>
- S3 bucket: `grocery-price-tracker-frontend-102429469952`
- CloudFront distribution: `E15IQ8G4RFTLO8`

Use placeholders such as `<region>`, `<bucket-name>`, and `<distribution-id>` in scripts that are intended for reuse. The identifiers above describe this deployment only.

### Selecting an AWS CLI profile

Use the profile that owns or is authorized to publish the frontend. In PowerShell,
either set it for the current shell:

```powershell
$env:AWS_PROFILE = "<profile-name>"
```

or add `--profile "<profile-name>"` to each AWS CLI command. Omit both when using
the default profile. Do not put access keys in this document or in the repository.

## Architecture and security requirements

The frontend bucket is private. S3 Block Public Access remains enabled, and CloudFront uses an Origin Access Control (OAC) with signed requests to read objects. End users receive content through CloudFront rather than direct public S3 URLs.

The bucket policy should grant only `s3:GetObject` to the CloudFront service principal, restricted to the intended distribution ARN and account. A reusable policy shape is:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowCloudFrontOACReadOnly",
      "Effect": "Allow",
      "Principal": {
        "Service": "cloudfront.amazonaws.com"
      },
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::<bucket-name>/*",
      "Condition": {
        "StringEquals": {
          "AWS:SourceArn": "arn:aws:cloudfront::<account-id>:distribution/<distribution-id>"
        }
      }
    }
  ]
}
```

Do not add `Principal: "*"` or `s3:ListBucket` for public website access. Keep the bucket policy, OAC, distribution origin, default root object, and error responses aligned with the actual distribution configuration.

## Read-only checks

These commands inspect configuration or the published site; they do not upload files or change AWS resources. They require AWS CLI credentials for the S3 and CloudFront calls.

```powershell
aws sts get-caller-identity
aws s3api get-public-access-block --bucket "<bucket-name>" --region "<region>"
aws s3api get-bucket-policy --bucket "<bucket-name>" --region "<region>"
aws cloudfront get-distribution --id "<distribution-id>"
curl.exe -I "https://<cloudfront-domain>/"
curl.exe -sS "https://<api-id>.execute-api.<region>.amazonaws.com/products"
```

Check that the bucket blocks public access, the policy names only the expected distribution, CloudFront is enabled, the site returns `200`, and the API returns the expected JSON envelope. These checks do not prove full operational monitoring or data freshness.

## Build and publish a frontend update

1. Confirm the API base URL that should be compiled into the Vite build. Do not commit `.env.local` or credentials.
2. Run the existing frontend tests, lint, and production build locally:

   ```powershell
   cd frontend
   npm.cmd ci
   npm.cmd test
   npm.cmd run lint
   $env:VITE_API_BASE_URL = "https://<api-id>.execute-api.<region>.amazonaws.com"
   npm.cmd run build
   ```

3. Review `.\dist` before publishing. Upload hashed assets first so an already-cached
   document can continue to load its existing JavaScript and CSS chunks. The following
   commands change S3 objects and must be run only with an approved deployment identity:

   ```powershell
   aws s3 sync .\dist\assets\ "s3://<bucket-name>/assets/" `
     --region "<region>" `
     --cache-control "public,max-age=31536000,immutable"

   aws s3 cp .\dist\index.html "s3://<bucket-name>/index.html" `
     --region "<region>" `
     --cache-control "no-cache,no-store,must-revalidate" `
     --content-type "text/html"
   ```

   Vite's hashed JavaScript and CSS assets can use a long immutable cache lifetime.
   Do not use `--delete`: retaining older hashed assets lets cached HTML and
   lazy-loaded chunks continue working during cache propagation. Uploading
   `index.html` separately with `no-cache` lets browsers revalidate the entry
   document and discover the new asset manifest.

4. CloudFront may continue serving an older cached entry document. An invalidation
   is optional and changes CloudFront state:

   ```powershell
   aws cloudfront create-invalidation `
     --distribution-id "<distribution-id>" `
     --paths "/" "/index.html"
   ```

   The root path and `/index.html` are the relevant entry paths. Hashed assets do
   not normally need invalidation because each build gives them new paths.

5. Repeat the read-only browser/API checks. Confirm the deployed page loads, product data can be fetched, a comparison can be selected, and a history period renders. This is a basic smoke check, not a substitute for the automated test suites or full production monitoring.

## Backend deployment note

The backend and scheduled ingestion were configured manually for the current MVP. The repository contains the Lambda application code and packaging helpers, but it does not provide an approved SAM or CI/CD deployment pipeline. Do not create or modify AWS resources from this documentation; make backend changes through an explicitly approved deployment procedure.

## Troubleshooting checklist

- `403` from CloudFront: inspect OAC association, the distribution ARN in the bucket policy, S3 Block Public Access, and the object key.
- Old frontend after publishing: check `index.html` cache headers and optionally invalidate `/` and `/index.html`.
- Frontend API errors: inspect the compiled `VITE_API_BASE_URL`, API Gateway routes/CORS configuration, and the browser network response.
- API data errors: inspect the API Lambda logs and DynamoDB table/GSI configuration; do not treat an empty history as evidence that ingestion is broken without checking the selected product, store, and period.
