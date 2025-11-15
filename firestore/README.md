# Firestore Security Rules - Environment-Specific Configuration

## Overview

This directory contains environment-specific Firestore security rules to avoid hardcoding environment details and improve maintainability.

## Files

- **`firestore.rules.template`** - Template file with placeholders for environment-specific values
- **`firestore.rules.prod`** - Production rules (project: sylvan-earth-477020-u6)
- **`firestore.rules.dev`** - Development rules (update with dev project details)

## Why Environment-Specific Rules?

**Problem with hardcoding:**
- ❌ Can't reuse rules across dev/staging/prod environments
- ❌ Manual updates required when service accounts or projects change
- ❌ Risk of deploying wrong rules to wrong environment
- ❌ Violates DRY (Don't Repeat Yourself) principle

**Benefits of this approach:**
- ✅ Clear separation between environments
- ✅ Easy to see which service account is allowed per environment
- ✅ Safer deployments (explicit environment selection)
- ✅ Better documentation (comments include project and service account details)

## Deployment

### Production Deployment

```bash
# Copy production rules to root (required by firebase.json)
cp firestore/firestore.rules.prod firestore.rules

# Deploy to production
firebase deploy --only firestore:rules --project goingmerry-stonks
```

### Development Deployment

```bash
# First, update firestore.rules.dev with your dev project details
# Then copy dev rules to root
cp firestore/firestore.rules.dev firestore.rules

# Deploy to development
firebase deploy --only firestore:rules --project [YOUR_DEV_PROJECT_ID]
```

### Automated Deployment (Recommended)

Add to your CI/CD pipeline:

```bash
# In your GitHub Actions or deployment script
if [ "$ENVIRONMENT" == "production" ]; then
  cp firestore/firestore.rules.prod firestore.rules
elif [ "$ENVIRONMENT" == "development" ]; then
  cp firestore/firestore.rules.dev firestore.rules
fi

firebase deploy --only firestore:rules --project $FIREBASE_PROJECT_ID
```

## Service Account Configuration

Each environment should have its own service account:

### Production
- **Project:** `sylvan-earth-477020-u6`
- **Service Account:** `prod-backend-sa@sylvan-earth-477020-u6.iam.gserviceaccount.com`
- **Used by:** Backend API (Cloud Run) + Batch Screeners (Cloud Run Jobs)

### Development
- **Project:** `[UPDATE_WITH_DEV_PROJECT]`
- **Service Account:** `[UPDATE_WITH_DEV_SERVICE_ACCOUNT]`
- **Used by:** Local development / dev Cloud Run instances

## Security Rules Explanation

```javascript
// PUBLIC READ: Anyone can read screener results
allow read: if true;

// SERVICE ACCOUNT WRITE: Only specific backend service account can write
allow write: if request.auth != null &&
             request.auth.token.email == 'prod-backend-sa@sylvan-earth-477020-u6.iam.gserviceaccount.com';
```

This ensures:
- ✅ Frontend can read cached screener results instantly
- ✅ Only authenticated backend services can write new results
- ✅ Prevents unauthorized writes from users or external services

## Updating Rules

1. **Make changes to the template** (`firestore.rules.template`)
2. **Generate environment-specific files** manually or with a script
3. **Test in development first**
4. **Deploy to production** after validation

## Testing Rules Locally

```bash
# Install Firebase emulators
npm install -g firebase-tools

# Start Firestore emulator
firebase emulators:start --only firestore

# Emulator will load rules from firestore.rules in the root directory
```

## Troubleshooting

### "Permission denied" errors
- Check that the service account email in the rules matches your backend service account
- Verify the service account has `Firebase Admin` or appropriate Firestore permissions
- Ensure requests include valid authentication tokens

### Rules not applying
- Rules can take a few minutes to propagate after deployment
- Clear browser cache if testing from frontend
- Check Firebase Console > Firestore > Rules for the currently deployed version

## References

- [Firestore Security Rules Documentation](https://firebase.google.com/docs/firestore/security/get-started)
- [Service Account Authentication](https://cloud.google.com/docs/authentication/production)
- [Firebase CLI Reference](https://firebase.google.com/docs/cli)
