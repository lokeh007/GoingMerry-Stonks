/**
 * Firebase Configuration
 *
 * Initializes Firebase app and Firestore for accessing cached screener results.
 */

import { initializeApp } from 'firebase/app';
import { getFirestore } from 'firebase/firestore';

// Firebase configuration - CORRECTED to use actual GCP project
// Backend writes to: sylvan-earth-477020-u6
// Frontend must read from same project!
const firebaseConfig = {
  apiKey: "AIzaSyBPcd7OIEzDDocG8kjfMpRFT8MHUQxwFgQ",
  authDomain: "sylvan-earth-477020-u6.firebaseapp.com",
  projectId: "sylvan-earth-477020-u6",  // FIXED: Was "goingmerry-stonks"
  storageBucket: "sylvan-earth-477020-u6.appspot.com",
  messagingSenderId: "591098440727",
  // Note: appId is optional for Firestore-only usage
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Initialize Firestore
export const db = getFirestore(app);

export default app;
