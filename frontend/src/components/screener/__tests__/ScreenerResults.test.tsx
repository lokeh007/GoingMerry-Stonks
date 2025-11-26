/**
 * Tests for ScreenerResults component
 *
 * Critical tests for null/zero value handling in className conditionals.
 * This test suite ensures that zero values (e.g., debt_to_equity = 0) are
 * correctly treated as valid numbers and not as falsy values.
 *
 * Background: JavaScript's truthiness coercion treats 0 as falsy, which can
 * cause bugs when using && operators for conditional class names. For financial
 * data, zero is often a valid and even excellent value (e.g., debt-free company).
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import ScreenerResults from '../ScreenerResults';
import { ScreenerResponse, StockScreenerResult, LynchCategory } from '../../../types/screener';

describe('ScreenerResults', () => {
  /**
   * Helper function to create mock screener response
   */
  const createMockResponse = (results: Partial<StockScreenerResult>[]): ScreenerResponse => {
    const completeResults: StockScreenerResult[] = results.map((partial) => ({
      ticker: partial.ticker || 'TEST',
      company_name: partial.company_name || 'Test Corporation',
      sector: partial.sector || 'Technology',
      market_cap: partial.market_cap,
      price: partial.price,
      pe_ratio: partial.pe_ratio,
      peg_ratio: partial.peg_ratio,
      revenue_growth: partial.revenue_growth,
      earnings_growth: partial.earnings_growth,
      debt_to_equity: partial.debt_to_equity,
      current_ratio: partial.current_ratio,
      roe: partial.roe,
      institutional_ownership: partial.institutional_ownership,
      score: partial.score || 70,
      reasons: partial.reasons || ['Test reason'],
    }));

    return {
      screener_name: 'Test Screener',
      description: 'Test Description',
      total_results: completeResults.length,
      results: completeResults,
      timestamp: '2025-01-01T00:00:00Z',
      criteria: {
        lynch_category: LynchCategory.FAST_GROWERS,
      },
    };
  };

  describe('Loading State', () => {
    it('should display loading spinner when loading is true', () => {
      render(
        <ScreenerResults
          response={null}
          loading={true}
          currentPage={1}
          pageSize={10}
          onPageChange={() => {}}
        />
      );

      expect(screen.getByText(/Running screener.../i)).toBeInTheDocument();
      expect(document.querySelector('.spinner')).toBeInTheDocument();
    });
  });

  describe('Empty State', () => {
    it('should return null when response is null and not loading', () => {
      const { container } = render(
        <ScreenerResults
          response={null}
          loading={false}
          currentPage={1}
          pageSize={10}
          onPageChange={() => {}}
        />
      );

      expect(container.firstChild).toBeNull();
    });

    it('should display no results message when total_results is 0', () => {
      const emptyResponse = createMockResponse([]);

      render(
        <ScreenerResults
          response={emptyResponse}
          loading={false}
          currentPage={1}
          pageSize={10}
          onPageChange={() => {}}
        />
      );

      expect(screen.getByText(/No stocks match your criteria/i)).toBeInTheDocument();
    });
  });

  describe('debt_to_equity highlighting (CRITICAL BUG FIX)', () => {
    it('should apply value-good class when debt_to_equity is 0 (debt-free company)', () => {
      const mockStock: Partial<StockScreenerResult> = {
        ticker: 'AAPL',
        company_name: 'Apple Inc.',
        sector: 'Technology',
        debt_to_equity: 0, // ← The critical case: zero is valid and financially excellent
        score: 85,
      };

      const { container } = render(
        <ScreenerResults
          response={createMockResponse([mockStock])}
          loading={false}
          currentPage={1}
          pageSize={10}
          onPageChange={() => {}}
        />
      );

      // Find the D/E cell (8th column: Ticker, Company, Sector, Market Cap, Price, PEG, EPS Growth, D/E)
      const deCell = container.querySelector('tbody tr:first-child td:nth-child(8)');
      expect(deCell).toHaveClass('value-good');
      expect(deCell).toHaveTextContent('0.00');
    });

    it('should apply value-good class when debt_to_equity is 0.3 (low debt)', () => {
      const mockStock: Partial<StockScreenerResult> = {
        ticker: 'MSFT',
        company_name: 'Microsoft Corp.',
        sector: 'Technology',
        debt_to_equity: 0.3,
        score: 80,
      };

      const { container } = render(
        <ScreenerResults
          response={createMockResponse([mockStock])}
          loading={false}
          currentPage={1}
          pageSize={10}
          onPageChange={() => {}}
        />
      );

      const deCell = container.querySelector('tbody tr:first-child td:nth-child(8)');
      expect(deCell).toHaveClass('value-good');
      expect(deCell).toHaveTextContent('0.30');
    });

    it('should NOT apply value-good class when debt_to_equity is 0.5 (at threshold)', () => {
      const mockStock: Partial<StockScreenerResult> = {
        ticker: 'XYZ',
        company_name: 'Threshold Corp.',
        sector: 'Technology',
        debt_to_equity: 0.5,
        score: 70,
      };

      const { container } = render(
        <ScreenerResults
          response={createMockResponse([mockStock])}
          loading={false}
          currentPage={1}
          pageSize={10}
          onPageChange={() => {}}
        />
      );

      const deCell = container.querySelector('tbody tr:first-child td:nth-child(8)');
      expect(deCell).not.toHaveClass('value-good');
      expect(deCell).toHaveTextContent('0.50');
    });

    it('should NOT apply value-good class when debt_to_equity is 0.6 (above threshold)', () => {
      const mockStock: Partial<StockScreenerResult> = {
        ticker: 'DEBT',
        company_name: 'High Debt Corp.',
        sector: 'Technology',
        debt_to_equity: 0.6,
        score: 60,
      };

      const { container } = render(
        <ScreenerResults
          response={createMockResponse([mockStock])}
          loading={false}
          currentPage={1}
          pageSize={10}
          onPageChange={() => {}}
        />
      );

      const deCell = container.querySelector('tbody tr:first-child td:nth-child(8)');
      expect(deCell).not.toHaveClass('value-good');
      expect(deCell).toHaveTextContent('0.60');
    });

    it('should NOT apply value-good class when debt_to_equity is null', () => {
      const mockStock: Partial<StockScreenerResult> = {
        ticker: 'NODATA',
        company_name: 'No Data Corp.',
        sector: 'Technology',
        debt_to_equity: undefined,
        score: 70,
      };

      const { container } = render(
        <ScreenerResults
          response={createMockResponse([mockStock])}
          loading={false}
          currentPage={1}
          pageSize={10}
          onPageChange={() => {}}
        />
      );

      const deCell = container.querySelector('tbody tr:first-child td:nth-child(8)');
      expect(deCell).not.toHaveClass('value-good');
      expect(deCell).toHaveTextContent('N/A');
    });
  });

  describe('peg_ratio highlighting', () => {
    it('should apply value-good class when peg_ratio is 0', () => {
      const mockStock: Partial<StockScreenerResult> = {
        ticker: 'ZEROPEG',
        company_name: 'Zero PEG Corp.',
        sector: 'Technology',
        peg_ratio: 0,
        score: 90,
      };

      const { container } = render(
        <ScreenerResults
          response={createMockResponse([mockStock])}
          loading={false}
          currentPage={1}
          pageSize={10}
          onPageChange={() => {}}
        />
      );

      // Find the PEG cell (6th column)
      const pegCell = container.querySelector('tbody tr:first-child td:nth-child(6)');
      expect(pegCell).toHaveClass('value-good');
      expect(pegCell).toHaveTextContent('0.00');
    });

    it('should apply value-good class when peg_ratio is 0.8 (below threshold)', () => {
      const mockStock: Partial<StockScreenerResult> = {
        ticker: 'GOODPEG',
        company_name: 'Good PEG Corp.',
        sector: 'Technology',
        peg_ratio: 0.8,
        score: 85,
      };

      const { container } = render(
        <ScreenerResults
          response={createMockResponse([mockStock])}
          loading={false}
          currentPage={1}
          pageSize={10}
          onPageChange={() => {}}
        />
      );

      const pegCell = container.querySelector('tbody tr:first-child td:nth-child(6)');
      expect(pegCell).toHaveClass('value-good');
      expect(pegCell).toHaveTextContent('0.80');
    });

    it('should NOT apply value-good class when peg_ratio is 1.0 (at threshold)', () => {
      const mockStock: Partial<StockScreenerResult> = {
        ticker: 'THRESHPEG',
        company_name: 'Threshold PEG Corp.',
        sector: 'Technology',
        peg_ratio: 1.0,
        score: 70,
      };

      const { container } = render(
        <ScreenerResults
          response={createMockResponse([mockStock])}
          loading={false}
          currentPage={1}
          pageSize={10}
          onPageChange={() => {}}
        />
      );

      const pegCell = container.querySelector('tbody tr:first-child td:nth-child(6)');
      expect(pegCell).not.toHaveClass('value-good');
      expect(pegCell).toHaveTextContent('1.00');
    });

    it('should NOT apply value-good class when peg_ratio is null', () => {
      const mockStock: Partial<StockScreenerResult> = {
        ticker: 'NOPEG',
        company_name: 'No PEG Corp.',
        sector: 'Technology',
        peg_ratio: undefined,
        score: 70,
      };

      const { container } = render(
        <ScreenerResults
          response={createMockResponse([mockStock])}
          loading={false}
          currentPage={1}
          pageSize={10}
          onPageChange={() => {}}
        />
      );

      const pegCell = container.querySelector('tbody tr:first-child td:nth-child(6)');
      expect(pegCell).not.toHaveClass('value-good');
      expect(pegCell).toHaveTextContent('N/A');
    });
  });

  describe('earnings_growth highlighting', () => {
    it('should apply value-good class when earnings_growth is 20', () => {
      const mockStock: Partial<StockScreenerResult> = {
        ticker: 'GROW',
        company_name: 'Growth Corp.',
        sector: 'Technology',
        earnings_growth: 20,
        score: 85,
      };

      const { container } = render(
        <ScreenerResults
          response={createMockResponse([mockStock])}
          loading={false}
          currentPage={1}
          pageSize={10}
          onPageChange={() => {}}
        />
      );

      // Find the EPS Growth cell (7th column)
      const egCell = container.querySelector('tbody tr:first-child td:nth-child(7)');
      expect(egCell).toHaveClass('value-good');
      expect(egCell).toHaveTextContent('20.0%');
    });

    it('should NOT apply value-good class when earnings_growth equals threshold (15)', () => {
      const mockStock: Partial<StockScreenerResult> = {
        ticker: 'THRESH',
        company_name: 'Threshold Growth Corp.',
        sector: 'Technology',
        earnings_growth: 15,
        score: 75,
      };

      const { container } = render(
        <ScreenerResults
          response={createMockResponse([mockStock])}
          loading={false}
          currentPage={1}
          pageSize={10}
          onPageChange={() => {}}
        />
      );

      const egCell = container.querySelector('tbody tr:first-child td:nth-child(7)');
      expect(egCell).not.toHaveClass('value-good'); // Uses > 15, not >= 15
      expect(egCell).toHaveTextContent('15.0%');
    });

    it('should apply value-good class when earnings_growth is 15.1 (just above threshold)', () => {
      const mockStock: Partial<StockScreenerResult> = {
        ticker: 'JUSTABOVE',
        company_name: 'Just Above Corp.',
        sector: 'Technology',
        earnings_growth: 15.1,
        score: 80,
      };

      const { container } = render(
        <ScreenerResults
          response={createMockResponse([mockStock])}
          loading={false}
          currentPage={1}
          pageSize={10}
          onPageChange={() => {}}
        />
      );

      const egCell = container.querySelector('tbody tr:first-child td:nth-child(7)');
      expect(egCell).toHaveClass('value-good');
      expect(egCell).toHaveTextContent('15.1%');
    });

    it('should NOT apply value-good class when earnings_growth is 10 (below threshold)', () => {
      const mockStock: Partial<StockScreenerResult> = {
        ticker: 'SLOW',
        company_name: 'Slow Corp.',
        sector: 'Technology',
        earnings_growth: 10,
        score: 60,
      };

      const { container } = render(
        <ScreenerResults
          response={createMockResponse([mockStock])}
          loading={false}
          currentPage={1}
          pageSize={10}
          onPageChange={() => {}}
        />
      );

      const egCell = container.querySelector('tbody tr:first-child td:nth-child(7)');
      expect(egCell).not.toHaveClass('value-good');
      expect(egCell).toHaveTextContent('10.0%');
    });

    it('should NOT apply value-good class when earnings_growth is 0', () => {
      const mockStock: Partial<StockScreenerResult> = {
        ticker: 'STAGNANT',
        company_name: 'Stagnant Corp.',
        sector: 'Technology',
        earnings_growth: 0,
        score: 50,
      };

      const { container } = render(
        <ScreenerResults
          response={createMockResponse([mockStock])}
          loading={false}
          currentPage={1}
          pageSize={10}
          onPageChange={() => {}}
        />
      );

      const egCell = container.querySelector('tbody tr:first-child td:nth-child(7)');
      expect(egCell).not.toHaveClass('value-good');
      expect(egCell).toHaveTextContent('0.0%');
    });

    it('should NOT apply value-good class when earnings_growth is null', () => {
      const mockStock: Partial<StockScreenerResult> = {
        ticker: 'NOEG',
        company_name: 'No EG Corp.',
        sector: 'Technology',
        earnings_growth: undefined,
        score: 70,
      };

      const { container } = render(
        <ScreenerResults
          response={createMockResponse([mockStock])}
          loading={false}
          currentPage={1}
          pageSize={10}
          onPageChange={() => {}}
        />
      );

      const egCell = container.querySelector('tbody tr:first-child td:nth-child(7)');
      expect(egCell).not.toHaveClass('value-good');
      expect(egCell).toHaveTextContent('N/A');
    });
  });

  describe('roe highlighting', () => {
    it('should apply value-good class when roe is 20', () => {
      const mockStock: Partial<StockScreenerResult> = {
        ticker: 'PROF',
        company_name: 'Profitable Corp.',
        sector: 'Technology',
        roe: 20,
        score: 88,
      };

      const { container } = render(
        <ScreenerResults
          response={createMockResponse([mockStock])}
          loading={false}
          currentPage={1}
          pageSize={10}
          onPageChange={() => {}}
        />
      );

      // Find the ROE cell (9th column)
      const roeCell = container.querySelector('tbody tr:first-child td:nth-child(9)');
      expect(roeCell).toHaveClass('value-good');
      expect(roeCell).toHaveTextContent('20.0%');
    });

    it('should NOT apply value-good class when roe equals threshold (15)', () => {
      const mockStock: Partial<StockScreenerResult> = {
        ticker: 'THRESH',
        company_name: 'Threshold ROE Corp.',
        sector: 'Technology',
        roe: 15,
        score: 75,
      };

      const { container } = render(
        <ScreenerResults
          response={createMockResponse([mockStock])}
          loading={false}
          currentPage={1}
          pageSize={10}
          onPageChange={() => {}}
        />
      );

      const roeCell = container.querySelector('tbody tr:first-child td:nth-child(9)');
      expect(roeCell).not.toHaveClass('value-good'); // Uses > 15, not >= 15
      expect(roeCell).toHaveTextContent('15.0%');
    });

    it('should NOT apply value-good class when roe is 0 (break-even)', () => {
      const mockStock: Partial<StockScreenerResult> = {
        ticker: 'EVEN',
        company_name: 'Break Even Corp.',
        sector: 'Technology',
        roe: 0,
        score: 50,
      };

      const { container } = render(
        <ScreenerResults
          response={createMockResponse([mockStock])}
          loading={false}
          currentPage={1}
          pageSize={10}
          onPageChange={() => {}}
        />
      );

      const roeCell = container.querySelector('tbody tr:first-child td:nth-child(9)');
      expect(roeCell).not.toHaveClass('value-good');
      expect(roeCell).toHaveTextContent('0.0%');
    });

    it('should NOT apply value-good class when roe is null', () => {
      const mockStock: Partial<StockScreenerResult> = {
        ticker: 'NOROE',
        company_name: 'No ROE Corp.',
        sector: 'Technology',
        roe: undefined,
        score: 70,
      };

      const { container } = render(
        <ScreenerResults
          response={createMockResponse([mockStock])}
          loading={false}
          currentPage={1}
          pageSize={10}
          onPageChange={() => {}}
        />
      );

      const roeCell = container.querySelector('tbody tr:first-child td:nth-child(9)');
      expect(roeCell).not.toHaveClass('value-good');
      expect(roeCell).toHaveTextContent('N/A');
    });
  });

  describe('Ticker Click Functionality', () => {
    it('should open technical analysis page in new tab when ticker is clicked', () => {
      const mockStock: Partial<StockScreenerResult> = {
        ticker: 'AAPL',
        company_name: 'Apple Inc.',
        score: 85,
      };

      // Mock window.open
      const originalOpen = window.open;
      window.open = jest.fn();

      render(
        <ScreenerResults
          response={createMockResponse([mockStock])}
          loading={false}
          currentPage={1}
          pageSize={10}
          onPageChange={() => {}}
        />
      );

      const tickerButton = screen.getByText('AAPL');
      fireEvent.click(tickerButton);

      expect(window.open).toHaveBeenCalledWith(
        '/technical?ticker=AAPL',
        '_blank',
        'noopener,noreferrer'
      );

      // Restore window.open
      window.open = originalOpen;
    });
  });

  describe('Pagination', () => {
    it('should display pagination controls when totalPages > 1', () => {
      const mockStocks: Partial<StockScreenerResult>[] = Array.from({ length: 15 }, (_, i) => ({
        ticker: `STOCK${i}`,
        company_name: `Company ${i}`,
        score: 75,
      }));

      const response = createMockResponse(mockStocks);

      const { container } = render(
        <ScreenerResults
          response={response}
          loading={false}
          currentPage={1}
          pageSize={10}
          onPageChange={() => {}}
        />
      );

      expect(screen.getByText('← Previous')).toBeInTheDocument();
      expect(screen.getByText('Next →')).toBeInTheDocument();

      // Check specifically for pagination-info element (not page-info in header)
      const paginationInfo = container.querySelector('.pagination-info');
      expect(paginationInfo).toHaveTextContent('Page 1 of 2');
    });

    it('should disable Previous button on first page', () => {
      const mockStocks: Partial<StockScreenerResult>[] = Array.from({ length: 15 }, (_, i) => ({
        ticker: `STOCK${i}`,
        company_name: `Company ${i}`,
        score: 75,
      }));

      const response = createMockResponse(mockStocks);

      render(
        <ScreenerResults
          response={response}
          loading={false}
          currentPage={1}
          pageSize={10}
          onPageChange={() => {}}
        />
      );

      const prevButton = screen.getByText('← Previous');
      expect(prevButton).toBeDisabled();
    });

    it('should call onPageChange when Next button is clicked', () => {
      const mockStocks: Partial<StockScreenerResult>[] = Array.from({ length: 15 }, (_, i) => ({
        ticker: `STOCK${i}`,
        company_name: `Company ${i}`,
        score: 75,
      }));

      const response = createMockResponse(mockStocks);
      const mockPageChange = jest.fn();

      render(
        <ScreenerResults
          response={response}
          loading={false}
          currentPage={1}
          pageSize={10}
          onPageChange={mockPageChange}
        />
      );

      const nextButton = screen.getByText('Next →');
      fireEvent.click(nextButton);

      expect(mockPageChange).toHaveBeenCalledWith(2);
    });
  });

  describe('Number Formatting', () => {
    it('should format market cap in billions', () => {
      const mockStock: Partial<StockScreenerResult> = {
        ticker: 'AAPL',
        company_name: 'Apple Inc.',
        market_cap: 2500000000000, // $2.5T
        score: 85,
      };

      const { container } = render(
        <ScreenerResults
          response={createMockResponse([mockStock])}
          loading={false}
          currentPage={1}
          pageSize={10}
          onPageChange={() => {}}
        />
      );

      // Find the Market Cap cell (4th column)
      const marketCapCell = container.querySelector('tbody tr:first-child td:nth-child(4)');
      expect(marketCapCell).toHaveTextContent('$2500.0B');
    });

    it('should format market cap in millions', () => {
      const mockStock: Partial<StockScreenerResult> = {
        ticker: 'SMALL',
        company_name: 'Small Cap Corp.',
        market_cap: 500000000, // $500M
        score: 70,
      };

      const { container } = render(
        <ScreenerResults
          response={createMockResponse([mockStock])}
          loading={false}
          currentPage={1}
          pageSize={10}
          onPageChange={() => {}}
        />
      );

      const marketCapCell = container.querySelector('tbody tr:first-child td:nth-child(4)');
      expect(marketCapCell).toHaveTextContent('$500.0M');
    });

    it('should display N/A for undefined market cap', () => {
      const mockStock: Partial<StockScreenerResult> = {
        ticker: 'NODATA',
        company_name: 'No Data Corp.',
        market_cap: undefined,
        score: 70,
      };

      const { container } = render(
        <ScreenerResults
          response={createMockResponse([mockStock])}
          loading={false}
          currentPage={1}
          pageSize={10}
          onPageChange={() => {}}
        />
      );

      const marketCapCell = container.querySelector('tbody tr:first-child td:nth-child(4)');
      expect(marketCapCell).toHaveTextContent('N/A');
    });
  });

  describe('Score Badge Styling', () => {
    it('should apply score-excellent class for score >= 80', () => {
      const mockStock: Partial<StockScreenerResult> = {
        ticker: 'EXCELLENT',
        company_name: 'Excellent Corp.',
        score: 85,
      };

      const { container } = render(
        <ScreenerResults
          response={createMockResponse([mockStock])}
          loading={false}
          currentPage={1}
          pageSize={10}
          onPageChange={() => {}}
        />
      );

      const scoreBadge = container.querySelector('.score-badge');
      expect(scoreBadge).toHaveClass('score-excellent');
    });

    it('should apply score-good class for score >= 60 and < 80', () => {
      const mockStock: Partial<StockScreenerResult> = {
        ticker: 'GOOD',
        company_name: 'Good Corp.',
        score: 70,
      };

      const { container } = render(
        <ScreenerResults
          response={createMockResponse([mockStock])}
          loading={false}
          currentPage={1}
          pageSize={10}
          onPageChange={() => {}}
        />
      );

      const scoreBadge = container.querySelector('.score-badge');
      expect(scoreBadge).toHaveClass('score-good');
    });

    it('should apply score-fair class for score >= 40 and < 60', () => {
      const mockStock: Partial<StockScreenerResult> = {
        ticker: 'FAIR',
        company_name: 'Fair Corp.',
        score: 50,
      };

      const { container } = render(
        <ScreenerResults
          response={createMockResponse([mockStock])}
          loading={false}
          currentPage={1}
          pageSize={10}
          onPageChange={() => {}}
        />
      );

      const scoreBadge = container.querySelector('.score-badge');
      expect(scoreBadge).toHaveClass('score-fair');
    });

    it('should apply score-poor class for score < 40', () => {
      const mockStock: Partial<StockScreenerResult> = {
        ticker: 'POOR',
        company_name: 'Poor Corp.',
        score: 30,
      };

      const { container } = render(
        <ScreenerResults
          response={createMockResponse([mockStock])}
          loading={false}
          currentPage={1}
          pageSize={10}
          onPageChange={() => {}}
        />
      );

      const scoreBadge = container.querySelector('.score-badge');
      expect(scoreBadge).toHaveClass('score-poor');
    });
  });
});
