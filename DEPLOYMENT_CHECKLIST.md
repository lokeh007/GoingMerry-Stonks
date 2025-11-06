# Deployment Checklist

## 🚀 Quick Deployment Commands

### Frontend Deployment (PRIMARY)
```bash
cd frontend
npm run build
firebase deploy --only hosting
```
**Deploys to**: https://goingmerry-stonks.web.app

### Backend Deployment
```bash
cd backend
docker build -t us-east5-docker.pkg.dev/sylvan-earth-477020-u6/prod-backend/api:latest .
docker push us-east5-docker.pkg.dev/sylvan-earth-477020-u6/prod-backend/api:latest
gcloud run services update prod-backend-api \
  --image=us-east5-docker.pkg.dev/sylvan-earth-477020-u6/prod-backend/api:latest \
  --region=us-east5
```

---

## ⚠️ IMPORTANT

### Frontend Deployment
- **✅ PRIMARY**: Firebase Hosting (`firebase deploy --only hosting`)
  - Users access: https://goingmerry-stonks.web.app
  - Instant deployment with global CDN
  - **ALWAYS USE THIS FOR PRODUCTION**

- **⚠️ BACKUP**: Cloud Storage (`gsutil rsync`)
  - Bucket: gs://sylvan-earth-477020-u6-frontend
  - Only use for testing or backup
  - **NOT CONNECTED TO MAIN DOMAIN**

### Common Mistake
❌ Deploying to Cloud Storage and expecting users to see changes
✅ Always deploy to Firebase Hosting for user-facing updates

---

## 📋 Pre-Deployment Checklist

### Frontend
- [ ] Run tests: `npm test`
- [ ] Build successfully: `npm run build`
- [ ] Check bundle size (should be ~146 KB gzipped)
- [ ] Deploy: `firebase deploy --only hosting`
- [ ] Verify at: https://goingmerry-stonks.web.app
- [ ] Hard refresh browser (Ctrl+Shift+R) to clear cache

### Backend
- [ ] Run tests: `pytest --cov`
- [ ] Check code quality: `black`, `flake8`, `mypy`
- [ ] Build Docker image
- [ ] Push to Artifact Registry
- [ ] Deploy to Cloud Run
- [ ] Verify API docs: https://prod-backend-api-rlfl2vcoda-ul.a.run.app/api/docs

---

## 🐛 Troubleshooting

### "I deployed but don't see changes"
1. **Check deployment target**: Did you use `firebase deploy`?
2. **Clear browser cache**: Ctrl+Shift+R (hard refresh)
3. **Try incognito mode**: Open in private window
4. **Check deployment succeeded**: Look for "✔ Deploy complete!" message
5. **Verify Firebase console**: https://console.firebase.google.com/project/goingmerry-stonks/hosting

### "Which deployment am I using?"
- Check the URL in your browser
- If it's `goingmerry-stonks.web.app` → Firebase Hosting ✅
- If it's `storage.googleapis.com` → Cloud Storage (wrong!)

---

**Last Updated**: November 6, 2025
**Maintained by**: Development Team
