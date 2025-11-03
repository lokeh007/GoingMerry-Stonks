Bootstrap workflow — secrets & OIDC quick start
===============================================

This file explains the minimal steps to configure secrets and the IAM trust policy required to run the
`.github/workflows/bootstrap-backend.yml` workflow using GitHub OIDC (recommended) and the optional
static AWS key fallback.

Secrets to create
- `AWS_ROLE_TO_ASSUME` — (string) the IAM Role ARN that GitHub OIDC will assume. Create as a repository
  secret (Settings  Secrets and variables  Actions) so the `plan` job can access it without environment approvals.
- `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` — optional repository secrets used only as a static fallback.

Environment notes
- The `apply` job uses `environment: prod` and will read environment-protected secrets if you place
  `AWS_ROLE_TO_ASSUME` in the `prod` environment. That will require environment approval when the job runs.
- The repository-level `AWS_ROLE_TO_ASSUME` secret (recommended) allows `plan` to run without approvals and
  keeps `apply` protected via `environment: prod`.

IAM role trust policy (example)
Replace `ACCOUNT_ID`, `YOUR_OWNER`, `YOUR_REPO` and `refs/heads/main` as appropriate.

{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:YOUR_OWNER/YOUR_REPO:ref:refs/heads/main"
        }
      }
    }
  ]
}

Security recommendations
- Scope the trust policy to the smallest set of refs possible (specific branch or tag) and use least-privilege
  IAM policies for the role.
- Prefer OIDC role assumption over storing long-lived AWS credentials in GitHub.
- Remove static AWS keys from the repository once you confirm OIDC-based runs are working.

How to test
- Create the `AWS_ROLE_TO_ASSUME` repo secret with the role ARN.
- Trigger the workflow via Actions  your workflow  Run workflow (choose `plan`).
- Confirm the `plan` step completes and the `Debug: show credential path` step prints the expected `role_to_assume`.

## Note: OIDC + environment-protected runs

When GitHub Actions uses OIDC to assume an AWS role, the token contains `aud` and `sub` claims issued by `token.actions.githubusercontent.com`.

- `aud` should be `sts.amazonaws.com` when assuming an AWS role via OIDC.
- The `sub` claim often contains repository and run context. For runs gated by a repository environment (for example `prod`), the `sub` value may include the environment name.

Use the `OIDC Debug (manual)` workflow to print the actual token payload (look for `aud` and `sub`) and then update the role trust policy to allow that `sub` pattern.

Example trust policy snippet (replace OWNER, REPO, and ENVIRONMENT):

```json
"Condition": {
  "StringEquals": {
    "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
  },
  "StringLike": {
    "token.actions.githubusercontent.com:sub": "repo:OWNER/REPO:environment:ENVIRONMENT"
  }
}
```

Apply the updated trust document to the role with the AWS CLI:

```bash
aws iam update-assume-role-policy --role-name <role-name> --policy-document file://trust.json
```

Tip: prefer a fairly specific `sub` pattern (repository + environment) rather than a wide wildcard to limit the blast radius.

If you want, I can also convert the workflow to make OIDC mandatory (remove the static fallback)  say so and I'll patch it.
