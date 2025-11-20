#!/usr/bin/env python3
"""
Analyze Daily Screener Runs

Queries Firestore to get comprehensive screening results from all batches.
More reliable than parsing Cloud Logging which may have retention limits.

Usage:
    python backend/jobs/analyze_daily_runs.py              # Yesterday
    python backend/jobs/analyze_daily_runs.py 2025-11-19   # Specific date
"""

import sys
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.cloud import firestore


def analyze_screening_results(date_str: str) -> None:
    """
    Analyze screening results for a specific date by aggregating all batch runs.

    Args:
        date_str: Date in YYYY-MM-DD format
    """
    db = firestore.Client()

    print("=" * 80)
    print(f"DAILY SCREENING RESULTS ANALYSIS - {date_str}")
    print("=" * 80)
    print()

    # Query both screeners
    screeners = {
        "undiscovered": "The Undiscovered (Low Institutional Ownership)",
        "coiled_spring": "The Coiled Spring (Low Volatility Compression)"
    }

    total_stocks = {"undiscovered": 0, "coiled_spring": 0}

    for screener_id, screener_name in screeners.items():
        print(f"📊 {screener_name}")
        print("-" * 80)

        try:
            # Query all batch documents for this date (batch-1 through batch-5)
            runs_collection = (
                db.collection("screeners")
                .document(screener_id)
                .collection("runs")
            )

            # Get all batch documents for this date
            batch_docs = []
            for batch_num in range(1, 6):  # 5 batches
                doc_id = f"{date_str}-batch-{batch_num}"
                doc = runs_collection.document(doc_id).get()
                if doc.exists:
                    batch_docs.append(doc.to_dict())

            if not batch_docs:
                print(f"  ⚠️  No results found for {date_str}")
                print()
                continue

            # Aggregate results from all batches
            aggregated_results = []
            total_results = 0
            total_screened = 0
            failed_count = 0
            not_found_count = 0
            execution_time = 0

            print(f"  Found {len(batch_docs)} batch(es)")
            print()

            for batch_data in batch_docs:
                batch_num = batch_data.get("batch_number", "?")
                batch_results = batch_data.get("results", [])

                # Aggregate metrics
                total_results += batch_data.get("total_results", 0)
                total_screened += batch_data.get("total_screened", 0)
                failed_count += batch_data.get("failed_count", 0)
                not_found_count += batch_data.get("not_found_count", 0)
                execution_time += batch_data.get("execution_time_seconds", 0)

                # Collect all results
                aggregated_results.extend(batch_results)

                print(f"  Batch {batch_num}: {batch_data.get('total_results', 0)} stocks, "
                      f"{batch_data.get('total_screened', 0):,} screened, "
                      f"{batch_data.get('execution_time_seconds', 0)/60:.1f}m")

            print()

            # Remove duplicates and sort by score
            unique_results = {}
            for stock in aggregated_results:
                ticker = stock.get("ticker")
                if ticker:
                    # Keep the higher-scored entry if duplicate
                    if ticker not in unique_results or stock.get("score", 0) > unique_results[ticker].get("score", 0):
                        unique_results[ticker] = stock

            # Convert to sorted list
            sorted_results = sorted(
                unique_results.values(),
                key=lambda x: x.get("score", 0),
                reverse=True
            )

            total_stocks[screener_id] = len(sorted_results)

            # Display summary
            print(f"  ✓ Total Stocks Passed: {len(sorted_results)} (deduplicated from {total_results} raw results)")
            print(f"  📈 Total Screened: {total_screened:,}")
            print(f"  ⏱  Total Execution Time: {execution_time/60:.1f} minutes ({execution_time/3600:.1f} hours)")
            print(f"  ✗ Failed: {failed_count}")
            print(f"  ⚠️  Not Found (404): {not_found_count}")
            print()

            if len(sorted_results) > 0:
                print(f"  Top {min(10, len(sorted_results))} Results:")
                print()
                print(f"  {'Rank':<6} {'Ticker':<8} {'Score':<8} {'P/E':<8} {'PEG':<8} {'Growth':<10}")
                print(f"  {'-'*6} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*10}")

                for i, stock in enumerate(sorted_results[:10], 1):
                    ticker = stock.get("ticker", "N/A")
                    score = stock.get("score", 0)
                    pe = stock.get("pe_ratio", "N/A")
                    peg = stock.get("peg_ratio", "N/A")

                    # Format growth rate
                    if screener_id == "undiscovered":
                        growth = stock.get("earnings_growth", "N/A")
                        if isinstance(growth, (int, float)):
                            growth_str = f"{growth:.1f}%"
                        else:
                            growth_str = str(growth)
                    else:
                        volatility = stock.get("volatility_30d", "N/A")
                        if isinstance(volatility, (int, float)):
                            growth_str = f"{volatility:.1f}%"
                        else:
                            growth_str = str(volatility)

                    # Format P/E and PEG
                    pe_str = f"{pe:.2f}" if isinstance(pe, (int, float)) else str(pe)
                    peg_str = f"{peg:.2f}" if isinstance(peg, (int, float)) else str(peg)

                    print(f"  {i:<6} {ticker:<8} {score:<8.1f} {pe_str:<8} {peg_str:<8} {growth_str:<10}")

                print()

        except Exception as e:
            print(f"  ❌ Error fetching results: {e}")
            print()

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"  Total Undiscovered Stocks: {total_stocks['undiscovered']}")
    print(f"  Total Coiled Spring Stocks: {total_stocks['coiled_spring']}")
    print(f"  Total Opportunities: {total_stocks['undiscovered'] + total_stocks['coiled_spring']}")
    print()
    print("View full results in Firestore:")
    print(f"  https://console.cloud.google.com/firestore/databases/-default-/data/panel/screeners;namespace=/")
    print()


def main():
    """Main entry point."""
    # Get date from command line or default to yesterday
    if len(sys.argv) > 1:
        date_str = sys.argv[1]
    else:
        yesterday = datetime.now() - timedelta(days=1)
        date_str = yesterday.strftime("%Y-%m-%d")

    # Validate date format
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        print(f"Error: Invalid date format. Use YYYY-MM-DD (e.g., 2025-11-19)")
        sys.exit(1)

    analyze_screening_results(date_str)


if __name__ == "__main__":
    main()
