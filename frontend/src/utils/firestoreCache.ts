/**
 * Firestore Cache Utilities
 *
 * Functions for loading cached screener results from Firestore.
 * Results are pre-computed daily by Cloud Run Job and stored for instant frontend loading.
 */

import { collection, doc, getDoc, query, orderBy, limit, getDocs } from 'firebase/firestore';
import { db } from '../config/firebase';
import { ScreenerResponse } from '../types/screener';

export interface CachedScreenerResult {
  data: ScreenerResponse;
  lastUpdated: string;
  isCached: true;
}

/**
 * Load the most recent cached screener results from Firestore.
 *
 * @param screenerName - Name of screener (undiscovered, coiled_spring, smart_money)
 * @returns Cached screener data or null if not found
 */
export const loadCachedScreenerResults = async (
  screenerName: string
): Promise<CachedScreenerResult | null> => {
  try {
    console.log(`[Firestore] Loading cached results for: ${screenerName}`);

    // Query: screeners/{screenerName}/runs (ordered by timestamp desc, limit 1)
    const runsCollection = collection(db, 'screeners', screenerName, 'runs');
    const q = query(runsCollection, orderBy('timestamp', 'desc'), limit(1));

    const querySnapshot = await getDocs(q);

    if (querySnapshot.empty) {
      console.log(`[Firestore] No cached results found for: ${screenerName}`);
      return null;
    }

    const docData = querySnapshot.docs[0].data();
    console.log(`[Firestore] Found cached results:`, {
      screener: screenerName,
      timestamp: docData.timestamp,
      resultCount: docData.results?.length || 0
    });

    // Transform Firestore data to ScreenerResponse format
    const screenerResponse: ScreenerResponse = {
      screener_name: docData.screener_name,
      description: `Cached results from ${new Date(docData.timestamp).toLocaleDateString()}`,
      total_results: docData.total_results,
      results: docData.results,
      timestamp: docData.timestamp,
      criteria: docData.parameters || {},
    };

    return {
      data: screenerResponse,
      lastUpdated: docData.timestamp,
      isCached: true,
    };
  } catch (error) {
    console.error(`[Firestore] Error loading cached results for ${screenerName}:`, error);
    return null;
  }
};

/**
 * Load cached results for a specific date.
 *
 * @param screenerName - Name of screener
 * @param date - Date string (YYYY-MM-DD)
 * @returns Cached screener data or null if not found
 */
export const loadCachedScreenerResultsByDate = async (
  screenerName: string,
  date: string
): Promise<CachedScreenerResult | null> => {
  try {
    console.log(`[Firestore] Loading cached results for: ${screenerName} on ${date}`);

    // Direct document access: screeners/{screenerName}/runs/{date}
    const docRef = doc(db, 'screeners', screenerName, 'runs', date);
    const docSnap = await getDoc(docRef);

    if (!docSnap.exists()) {
      console.log(`[Firestore] No cached results found for: ${screenerName} on ${date}`);
      return null;
    }

    const docData = docSnap.data();
    console.log(`[Firestore] Found cached results for ${date}`);

    // Transform to ScreenerResponse format
    const screenerResponse: ScreenerResponse = {
      screener_name: docData.screener_name,
      description: `Cached results from ${date}`,
      total_results: docData.total_results,
      results: docData.results,
      timestamp: docData.timestamp,
      criteria: docData.parameters || {},
    };

    return {
      data: screenerResponse,
      lastUpdated: docData.timestamp,
      isCached: true,
    };
  } catch (error) {
    console.error(`[Firestore] Error loading cached results by date:`, error);
    return null;
  }
};

/**
 * Get list of available cached result dates for a screener.
 *
 * @param screenerName - Name of screener
 * @param limitCount - Maximum number of dates to return
 * @returns Array of date strings (YYYY-MM-DD)
 */
export const getAvailableCachedDates = async (
  screenerName: string,
  limitCount: number = 30
): Promise<string[]> => {
  try {
    const runsCollection = collection(db, 'screeners', screenerName, 'runs');
    const q = query(runsCollection, orderBy('timestamp', 'desc'), limit(limitCount));

    const querySnapshot = await getDocs(q);

    return querySnapshot.docs.map(doc => doc.id);  // Document ID is the date (YYYY-MM-DD)
  } catch (error) {
    console.error(`[Firestore] Error getting available dates:`, error);
    return [];
  }
};

/**
 * Format last updated timestamp for display.
 *
 * @param timestamp - ISO timestamp string
 * @returns Formatted string (e.g., "2 hours ago", "Today at 6:30 PM")
 */
export const formatLastUpdated = (timestamp: string): string => {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffHours / 24);

  if (diffHours < 1) {
    const diffMinutes = Math.floor(diffMs / (1000 * 60));
    return diffMinutes < 1 ? 'Just now' : `${diffMinutes} minute${diffMinutes > 1 ? 's' : ''} ago`;
  }

  if (diffHours < 24) {
    return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
  }

  if (diffDays === 1) {
    return 'Yesterday';
  }

  if (diffDays < 7) {
    return `${diffDays} days ago`;
  }

  // Older than 7 days, show date
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
  });
};

/**
 * Check if cached results are stale (older than 24 hours).
 *
 * @param timestamp - ISO timestamp string
 * @returns True if results are stale
 */
export const isCachedResultStale = (timestamp: string): boolean => {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffHours = diffMs / (1000 * 60 * 60);

  return diffHours > 24;
};
