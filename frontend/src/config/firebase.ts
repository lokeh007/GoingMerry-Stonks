/**
 * Firebase Configuration
 *
 * Initializes Firebase app and Firestore for accessing cached screener results.
 * 
 * SECURITY NOTE: This API key is intentionally public and protected by:
 * - HTTP referrer restrictions (only works from approved domains)
 * - Firestore security rules (restricts data access)
 * - API restrictions (limited to Firebase services only)
 * 
 * Allowed referrers:
 * - https://sylvan-earth-477020-u6.web.app/*
 * - https://sylvan-earth-477020-u6.firebaseapp.com/*
 * - http://localhost:* (development)
 */

import { initializeApp } from 'firebase/app';
import { getFirestore } from 'firebase/firestore';

// Firebase configuration
// API key has HTTP referrer and API restrictions applied in GCP Console
const firebaseConfig = {
  apiKey: "AIzaSyBaDXyegUQtJIzybAxfv5vp3U1i6aibZkE",
  authDomain: "sylvan-earth-477020-u6.firebaseapp.com",
  projectId: "sylvan-earth-477020-u6",
  storageBucket: "sylvan-earth-477020-u6.appspot.com",
  messagingSenderId: "591098440727",
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Initialize Firestore
export const db = getFirestore(app);

export default app;
