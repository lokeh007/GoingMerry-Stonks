/**
 * Technical Analysis Page Component
 *
 * Displays technical analysis charts and indicators for stock analysis.
 */

import React, { useState, useEffect } from 'react';
import { apiClient } from '../config/api';
import './TechnicalAnalysisPage.css';
import { PriceChart } from '../components/TechnicalAnalysis/PriceChart';
import { CandlestickChart } from '../components/TechnicalAnalysis/CandlestickChart';
import { VolumeChart } from '../components/TechnicalAnalysis/VolumeChart';
import { RSIChart } from '../components/TechnicalAnalysis/RSIChart';
import { MACDChart } from '../components/TechnicalAnalysis/MACDChart';

interface TechnicalData {
  ticker: string;
  period: string;
  interval: string;
  data_points: number;
  price_data: {
    dates: string[];
    open: number[];
    high: number[];
    low: number[];
    close: number[];
    volume: number[];
  };
  indicators: {
    rsi?: number[];
    rsi_current?: number;
    macd?: {
      macd_line: number[];
      signal_line: number[];
      histogram: number[];
    };
    ema12?: number[];
    ema26?: number[];
    ema50?: number[];
    ema200?: number[];
    sma20?: number[];
    sma50?: number[];
    sma200?: number[];
    bollinger?: {
      upper: number[];
      middle: number[];
      lower: number[];
    };
  };
}

type ChartType = 'line' | 'candlestick';

const TechnicalAnalysisPage: React.FC = () => {
  const [technicalData, setTechnicalData] = useState<TechnicalData | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [ticker, setTicker] = useState<string>('AAPL');
  const [inputTicker, setInputTicker] = useState<string>('AAPL');
  const [period, setPeriod] = useState<string>('6mo');
  const [chartType, setChartType] = useState<ChartType>('line');
  const [selectedIndicators, setSelectedIndicators] = useState<string[]>([
    'rsi', 'macd', 'ema12', 'ema26', 'ema50', 'ema200', 'sma20', 'sma50', 'sma200', 'bollinger'
  ]);

  /**
   * Fetch technical analysis data from API
   */
  const fetchTechnicalData = async (
    symbol: string,
    timeperiod: string,
    indicators: string[]
  ) => {
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams();
      params.append('period', timeperiod);
      params.append('indicators', indicators.join(','));

      const response = await apiClient.get<TechnicalData>(
        `/technical/${symbol.toUpperCase()}?${params.toString()}`
      );

      setTechnicalData(response.data);
      setTicker(symbol.toUpperCase());
    } catch (err: any) {
      if (err.response) {
        setError(
          err.response.data.detail ||
          `Error ${err.response.status}: Failed to fetch technical analysis`
        );
      } else if (err.request) {
        setError('Unable to connect to API. Please ensure the backend is running.');
      } else {
        setError('An unexpected error occurred');
      }
      console.error('Error fetching technical data:', err);
    } finally {
      setLoading(false);
    }
  };

  /**
   * Handle form submission
   */
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputTicker.trim()) {
      fetchTechnicalData(inputTicker.trim(), period, selectedIndicators);
    }
  };

  /**
   * Handle indicator checkbox toggle
   */
  const handleIndicatorToggle = (indicator: string) => {
    setSelectedIndicators(prev =>
      prev.includes(indicator)
        ? prev.filter(i => i !== indicator)
        : [...prev, indicator]
    );
  };

  /**
   * Load default data on mount
   */
  useEffect(() => {
    fetchTechnicalData('AAPL', period, selectedIndicators);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="technical-analysis-page">
      <div className="ta-main">
        {/* Search Form */}
        <div className="ta-search-section">
          <form onSubmit={handleSubmit} className="ta-search-form">
            <div className="ta-input-group">
              <input
                type="text"
                value={inputTicker}
                onChange={(e) => setInputTicker(e.target.value.toUpperCase())}
                placeholder="Enter ticker (e.g., AAPL)"
                className="ta-ticker-input"
                disabled={loading}
                maxLength={10}
              />

              <select
                value={period}
                onChange={(e) => setPeriod(e.target.value)}
                className="ta-period-select"
                disabled={loading}
              >
                <option value="1mo">1 Month</option>
                <option value="3mo">3 Months</option>
                <option value="6mo">6 Months</option>
                <option value="1y">1 Year</option>
                <option value="2y">2 Years</option>
                <option value="5y">5 Years</option>
              </select>

              <button
                type="submit"
                className="ta-search-button"
                disabled={loading || !inputTicker.trim()}
              >
                {loading ? 'Loading...' : 'Analyze'}
              </button>
            </div>
          </form>

          {/* Indicator Toggles */}
          <div className="ta-indicators-section">
            <label className="ta-indicator-toggle">
              <input
                type="checkbox"
                checked={selectedIndicators.includes('rsi')}
                onChange={() => handleIndicatorToggle('rsi')}
              />
              <span>RSI</span>
            </label>
            <label className="ta-indicator-toggle">
              <input
                type="checkbox"
                checked={selectedIndicators.includes('macd')}
                onChange={() => handleIndicatorToggle('macd')}
              />
              <span>MACD</span>
            </label>
            <label className="ta-indicator-toggle">
              <input
                type="checkbox"
                checked={selectedIndicators.includes('bollinger')}
                onChange={() => handleIndicatorToggle('bollinger')}
              />
              <span>Bollinger Bands</span>
            </label>
            <label className="ta-indicator-toggle">
              <input
                type="checkbox"
                checked={selectedIndicators.includes('ema12')}
                onChange={() => handleIndicatorToggle('ema12')}
              />
              <span>EMA 12</span>
            </label>
            <label className="ta-indicator-toggle">
              <input
                type="checkbox"
                checked={selectedIndicators.includes('ema26')}
                onChange={() => handleIndicatorToggle('ema26')}
              />
              <span>EMA 26</span>
            </label>
            <label className="ta-indicator-toggle">
              <input
                type="checkbox"
                checked={selectedIndicators.includes('ema50')}
                onChange={() => handleIndicatorToggle('ema50')}
              />
              <span>EMA 50</span>
            </label>
            <label className="ta-indicator-toggle">
              <input
                type="checkbox"
                checked={selectedIndicators.includes('ema200')}
                onChange={() => handleIndicatorToggle('ema200')}
              />
              <span>EMA 200</span>
            </label>
            <label className="ta-indicator-toggle">
              <input
                type="checkbox"
                checked={selectedIndicators.includes('sma20')}
                onChange={() => handleIndicatorToggle('sma20')}
              />
              <span>SMA 20</span>
            </label>
            <label className="ta-indicator-toggle">
              <input
                type="checkbox"
                checked={selectedIndicators.includes('sma50')}
                onChange={() => handleIndicatorToggle('sma50')}
              />
              <span>SMA 50</span>
            </label>
            <label className="ta-indicator-toggle">
              <input
                type="checkbox"
                checked={selectedIndicators.includes('sma200')}
                onChange={() => handleIndicatorToggle('sma200')}
              />
              <span>SMA 200</span>
            </label>
          </div>

          {/* Chart Type Toggle */}
          <div className="ta-chart-type-section">
            <button
              className={`ta-chart-type-button ${chartType === 'line' ? 'active' : ''}`}
              onClick={() => setChartType('line')}
              disabled={loading}
            >
              Line Chart
            </button>
            <button
              className={`ta-chart-type-button ${chartType === 'candlestick' ? 'active' : ''}`}
              onClick={() => setChartType('candlestick')}
              disabled={loading}
            >
              Candlestick
            </button>
          </div>
        </div>

        {/* Loading State */}
        {loading && (
          <div className="ta-loading-container">
            <div className="ta-spinner"></div>
            <p className="ta-loading-text">Loading technical analysis...</p>
          </div>
        )}

        {/* Error State */}
        {error && !loading && (
          <div className="ta-error-container">
            <div className="ta-error-icon">⚠️</div>
            <h3 className="ta-error-title">Error Loading Data</h3>
            <p className="ta-error-message">{error}</p>
            <button onClick={() => fetchTechnicalData(ticker, period, selectedIndicators)} className="ta-retry-button">
              Retry
            </button>
          </div>
        )}

        {/* Charts */}
        {technicalData && !loading && !error && (
          <div className="ta-charts-container">
            {/* Price Chart (Line or Candlestick) */}
            {chartType === 'line' ? (
              <PriceChart
                dates={technicalData.price_data.dates}
                prices={technicalData.price_data.close}
                ema12={technicalData.indicators.ema12}
                ema26={technicalData.indicators.ema26}
                ema50={technicalData.indicators.ema50}
                ema200={technicalData.indicators.ema200}
                sma20={technicalData.indicators.sma20}
                sma50={technicalData.indicators.sma50}
                sma200={technicalData.indicators.sma200}
                bollingerBands={technicalData.indicators.bollinger}
                ticker={technicalData.ticker}
              />
            ) : (
              <CandlestickChart
                dates={technicalData.price_data.dates}
                open={technicalData.price_data.open}
                high={technicalData.price_data.high}
                low={technicalData.price_data.low}
                close={technicalData.price_data.close}
                ema12={technicalData.indicators.ema12}
                ema26={technicalData.indicators.ema26}
                ema50={technicalData.indicators.ema50}
                ema200={technicalData.indicators.ema200}
                sma20={technicalData.indicators.sma20}
                sma50={technicalData.indicators.sma50}
                sma200={technicalData.indicators.sma200}
                bollingerBands={technicalData.indicators.bollinger}
                ticker={technicalData.ticker}
              />
            )}

            {/* Volume Chart */}
            <VolumeChart
              dates={technicalData.price_data.dates}
              volume={technicalData.price_data.volume}
              open={technicalData.price_data.open}
              close={technicalData.price_data.close}
              ticker={technicalData.ticker}
            />

            {/* RSI Chart */}
            {technicalData.indicators.rsi && (
              <RSIChart
                dates={technicalData.price_data.dates}
                rsi={technicalData.indicators.rsi}
                currentRSI={technicalData.indicators.rsi_current}
              />
            )}

            {/* MACD Chart */}
            {technicalData.indicators.macd && (
              <MACDChart
                dates={technicalData.price_data.dates}
                macd={technicalData.indicators.macd}
              />
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default TechnicalAnalysisPage;
