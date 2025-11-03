/**
 * Tests for metrics calculator utility functions.
 *
 * Tests financial calculations for options strategies.
 */

import { calculateMetrics } from '../metricsCalculator';

describe('metricsCalculator', () => {
  describe('calculateMetrics', () => {
    it('should calculate metrics for short put strategy', () => {
      const params = {
        strategyType: 'short_put' as const,
        strike: 150,
        premium: 5.25,
        quantity: 1,
        currentStockPrice: 155
      };

      const metrics = calculateMetrics(params);

      expect(metrics).toBeDefined();
      expect(metrics.netCredit).toBeCloseTo(525, 0); // 5.25 * 100
      expect(metrics.maxProfit).toBeCloseTo(525, 0);
      expect(metrics.maxLoss).toBeLessThan(0); // Should be negative
      expect(metrics.breakeven).toBeCloseTo(144.75, 2); // 150 - 5.25
      expect(metrics.collateral).toBeGreaterThan(0);
      expect(metrics.returnOnCapital).toBeGreaterThan(0);
    });

    it('should calculate metrics for long call strategy', () => {
      const params = {
        strategyType: 'long_call' as const,
        strike: 150,
        premium: 5.25,
        quantity: 1,
        currentStockPrice: 155
      };

      const metrics = calculateMetrics(params);

      expect(metrics.netDebit).toBeCloseTo(525, 0);
      expect(metrics.maxLoss).toBeCloseTo(-525, 0);
      expect(metrics.maxProfit).toBeNull(); // Unlimited upside
      expect(metrics.breakeven).toBeCloseTo(155.25, 2); // 150 + 5.25
    });

    it('should handle zero premium gracefully', () => {
      const params = {
        strategyType: 'short_put' as const,
        strike: 150,
        premium: 0,
        quantity: 1,
        currentStockPrice: 155
      };

      const metrics = calculateMetrics(params);

      expect(metrics.netCredit).toBe(0);
      expect(metrics.maxProfit).toBe(0);
    });

    it('should calculate metrics for multiple contracts', () => {
      const params = {
        strategyType: 'short_put' as const,
        strike: 150,
        premium: 5.25,
        quantity: 10,
        currentStockPrice: 155
      };

      const metrics = calculateMetrics(params);

      expect(metrics.netCredit).toBeCloseTo(5250, 0); // 5.25 * 100 * 10
      expect(metrics.maxProfit).toBeCloseTo(5250, 0);
      expect(metrics.collateral).toBeGreaterThan(0);
    });

    it('should throw error for invalid strategy type', () => {
      const params = {
        strategyType: 'invalid' as any,
        strike: 150,
        premium: 5.25,
        quantity: 1,
        currentStockPrice: 155
      };

      expect(() => calculateMetrics(params)).toThrow();
    });

    it('should throw error for negative strike price', () => {
      const params = {
        strategyType: 'short_put' as const,
        strike: -150,
        premium: 5.25,
        quantity: 1,
        currentStockPrice: 155
      };

      expect(() => calculateMetrics(params)).toThrow();
    });

    it('should throw error for negative premium', () => {
      const params = {
        strategyType: 'short_put' as const,
        strike: 150,
        premium: -5.25,
        quantity: 1,
        currentStockPrice: 155
      };

      expect(() => calculateMetrics(params)).toThrow();
    });
  });

  describe('Risk/Reward Calculations', () => {
    it('should calculate risk/reward ratio correctly', () => {
      const params = {
        strategyType: 'short_put' as const,
        strike: 150,
        premium: 5.25,
        quantity: 1,
        currentStockPrice: 155
      };

      const metrics = calculateMetrics(params);

      expect(metrics.riskRewardRatio).toBeDefined();
      expect(metrics.riskRewardRatio).toBeGreaterThan(0);
    });

    it('should calculate return on capital correctly', () => {
      const params = {
        strategyType: 'short_put' as const,
        strike: 150,
        premium: 5.25,
        quantity: 1,
        currentStockPrice: 155
      };

      const metrics = calculateMetrics(params);

      expect(metrics.returnOnCapital).toBeDefined();
      expect(metrics.returnOnCapital).toBeGreaterThan(0);
      expect(metrics.returnOnCapital).toBeLessThan(100); // ROC should be reasonable
    });
  });

  describe('Edge Cases', () => {
    it('should handle very small premiums', () => {
      const params = {
        strategyType: 'short_put' as const,
        strike: 150,
        premium: 0.01,
        quantity: 1,
        currentStockPrice: 155
      };

      const metrics = calculateMetrics(params);

      expect(metrics.netCredit).toBeCloseTo(1, 0);
      expect(metrics.breakeven).toBeCloseTo(149.99, 2);
    });

    it('should handle very large strike prices', () => {
      const params = {
        strategyType: 'short_put' as const,
        strike: 10000,
        premium: 500,
        quantity: 1,
        currentStockPrice: 10500
      };

      const metrics = calculateMetrics(params);

      expect(metrics).toBeDefined();
      expect(metrics.strike).toBe(10000);
    });
  });
});
