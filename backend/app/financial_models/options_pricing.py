"""
Options Pricing Module.

This module implements the Black-Scholes-Merton (BSM) options pricing model
and calculates the Greeks for risk management and analysis.

The Black-Scholes-Merton model is a mathematical model for pricing European-style
options, which provides theoretical values for call and put options.
"""

import math
from typing import Literal
from scipy.stats import norm


# Type alias for option types
OptionType = Literal["call", "put"]


class OptionsPricingError(Exception):
    """Base exception for options pricing calculations."""
    pass


class InvalidParameterError(OptionsPricingError):
    """Raised when invalid parameters are provided."""
    pass


def _validate_bsm_parameters(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: str,
) -> None:
    """
    Validate Black-Scholes-Merton parameters.

    Args:
        S: Current stock price
        K: Strike price
        T: Time to expiration
        r: Risk-free rate
        sigma: Volatility
        option_type: Type of option

    Raises:
        InvalidParameterError: If any parameter is invalid.
    """
    if S <= 0:
        raise InvalidParameterError(f"Stock price must be positive, got {S}")
    if K <= 0:
        raise InvalidParameterError(f"Strike price must be positive, got {K}")
    if T < 0:
        raise InvalidParameterError(f"Time to expiration cannot be negative, got {T}")
    if sigma < 0:
        raise InvalidParameterError(f"Volatility cannot be negative, got {sigma}")
    if option_type.lower() not in ["call", "put"]:
        raise InvalidParameterError(
            f"Option type must be 'call' or 'put', got '{option_type}'"
        )


def _calculate_d1(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """
    Calculate d1 parameter for Black-Scholes-Merton formula.

    Args:
        S: Current stock price
        K: Strike price
        T: Time to expiration in years
        r: Risk-free interest rate (annualized)
        sigma: Volatility (annualized standard deviation)

    Returns:
        float: The d1 value
    """
    if T == 0:
        # At expiration, use intrinsic value logic
        return float('inf') if S > K else float('-inf')

    return (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))


def _calculate_d2(d1: float, sigma: float, T: float) -> float:
    """
    Calculate d2 parameter for Black-Scholes-Merton formula.

    Args:
        d1: The d1 value from _calculate_d1
        sigma: Volatility (annualized standard deviation)
        T: Time to expiration in years

    Returns:
        float: The d2 value
    """
    if T == 0:
        return d1

    return d1 - sigma * math.sqrt(T)


def calculate_bsm_price(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: OptionType,
) -> float:
    """
    Calculate the Black-Scholes-Merton price for a European option.

    The Black-Scholes-Merton model provides a theoretical estimate of the price
    of European-style options. It assumes that the market is efficient, the
    stock follows a geometric Brownian motion, and there are no dividends.

    Args:
        S: Current stock price (spot price). Must be positive.
        K: Strike price (exercise price). Must be positive.
        T: Time to expiration in years. For example:
            - 0.25 = 3 months
            - 0.5 = 6 months
            - 1.0 = 1 year
        r: Risk-free interest rate (annualized), expressed as a decimal.
           For example, 0.05 = 5% annual interest rate.
        sigma: Volatility (annualized standard deviation of returns),
               expressed as a decimal. For example, 0.20 = 20% annual volatility.
        option_type: Type of option, either "call" or "put".

    Returns:
        float: The calculated option price.

    Raises:
        InvalidParameterError: If any parameter is invalid.

    Example:
        >>> # Calculate price of a call option
        >>> price = calculate_bsm_price(
        ...     S=100,      # Stock trading at $100
        ...     K=105,      # Strike price of $105
        ...     T=0.25,     # 3 months to expiration
        ...     r=0.05,     # 5% risk-free rate
        ...     sigma=0.20, # 20% volatility
        ...     option_type="call"
        ... )
        >>> print(f"Call option price: ${price:.2f}")

    Notes:
        - This implementation assumes no dividends. For dividend-paying stocks,
          use the adjusted BSM model.
        - The model is most accurate for European options (can only be exercised
          at expiration).
        - Volatility (sigma) is typically estimated from historical data or
          implied from market prices.
    """
    # Validate inputs
    _validate_bsm_parameters(S, K, T, r, sigma, option_type)

    # Handle edge case: at expiration (T=0)
    if T == 0:
        if option_type.lower() == "call":
            return max(S - K, 0)
        else:
            return max(K - S, 0)

    # Calculate d1 and d2
    d1 = _calculate_d1(S, K, T, r, sigma)
    d2 = _calculate_d2(d1, sigma, T)

    # Calculate option price based on type
    if option_type.lower() == "call":
        price = S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
    else:  # put
        price = K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)

    return round(price, 4)


def calculate_delta(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: OptionType,
) -> float:
    """
    Calculate the Delta of an option.

    Delta measures the rate of change of the option price with respect to
    changes in the underlying asset's price. It represents the hedge ratio
    and indicates how much the option price will change for a $1 change in
    the stock price.

    Args:
        S: Current stock price (spot price). Must be positive.
        K: Strike price (exercise price). Must be positive.
        T: Time to expiration in years.
        r: Risk-free interest rate (annualized), expressed as a decimal.
        sigma: Volatility (annualized standard deviation), expressed as a decimal.
        option_type: Type of option, either "call" or "put".

    Returns:
        float: Delta value.
            - Call options: Delta ranges from 0 to 1
            - Put options: Delta ranges from -1 to 0
            - At-the-money options typically have Delta around 0.5 (call) or -0.5 (put)

    Raises:
        InvalidParameterError: If any parameter is invalid.

    Example:
        >>> delta = calculate_delta(
        ...     S=100,
        ...     K=100,
        ...     T=0.25,
        ...     r=0.05,
        ...     sigma=0.20,
        ...     option_type="call"
        ... )
        >>> print(f"Delta: {delta:.4f}")
        >>> # Delta of 0.6 means if stock increases by $1, option increases by $0.60

    Notes:
        - Delta is used for hedging: sell delta shares for each option to create
          a delta-neutral position.
        - Call deltas are positive (option value increases as stock increases).
        - Put deltas are negative (option value decreases as stock increases).
        - Deep in-the-money options have Delta approaching 1 (call) or -1 (put).
        - Deep out-of-the-money options have Delta approaching 0.
    """
    # Validate inputs
    _validate_bsm_parameters(S, K, T, r, sigma, option_type)

    # Handle edge case: at expiration (T=0)
    if T == 0:
        if option_type.lower() == "call":
            return 1.0 if S > K else 0.0
        else:
            return -1.0 if S < K else 0.0

    # Calculate d1
    d1 = _calculate_d1(S, K, T, r, sigma)

    # Calculate delta based on option type
    if option_type.lower() == "call":
        delta = norm.cdf(d1)
    else:  # put
        delta = norm.cdf(d1) - 1

    return round(delta, 4)


def calculate_theta(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: OptionType,
) -> float:
    """
    Calculate the Theta of an option.

    Theta measures the rate of change of the option price with respect to
    the passage of time (time decay). It represents how much value the option
    loses each day, all else being equal.

    Args:
        S: Current stock price (spot price). Must be positive.
        K: Strike price (exercise price). Must be positive.
        T: Time to expiration in years.
        r: Risk-free interest rate (annualized), expressed as a decimal.
        sigma: Volatility (annualized standard deviation), expressed as a decimal.
        option_type: Type of option, either "call" or "put".

    Returns:
        float: Theta value (per year). To get daily theta, divide by 365.
            - Theta is typically negative for long options (time decay)
            - Represents the dollar amount the option loses per year

    Raises:
        InvalidParameterError: If any parameter is invalid.

    Example:
        >>> theta_annual = calculate_theta(
        ...     S=100,
        ...     K=100,
        ...     T=0.25,
        ...     r=0.05,
        ...     sigma=0.20,
        ...     option_type="call"
        ... )
        >>> theta_daily = theta_annual / 365
        >>> print(f"Daily Theta: ${theta_daily:.4f}")
        >>> # Theta of -0.05 means option loses $0.05 in value each day

    Notes:
        - Theta is generally negative for long options (you lose value over time).
        - Time decay accelerates as expiration approaches.
        - At-the-money options have the highest theta.
        - Deep in/out-of-the-money options have lower theta.
        - Theta is particularly important for option sellers who profit from
          time decay.
    """
    # Validate inputs
    _validate_bsm_parameters(S, K, T, r, sigma, option_type)

    # Handle edge case: at expiration (T=0)
    if T == 0:
        return 0.0

    # Calculate d1 and d2
    d1 = _calculate_d1(S, K, T, r, sigma)
    d2 = _calculate_d2(d1, sigma, T)

    # Common term for both call and put
    term1 = -(S * norm.pdf(d1) * sigma) / (2 * math.sqrt(T))

    # Calculate theta based on option type
    if option_type.lower() == "call":
        term2 = -r * K * math.exp(-r * T) * norm.cdf(d2)
        theta = term1 + term2
    else:  # put
        term2 = r * K * math.exp(-r * T) * norm.cdf(-d2)
        theta = term1 + term2

    return round(theta, 4)


def calculate_gamma(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
) -> float:
    """
    Calculate the Gamma of an option.

    Gamma measures the rate of change of Delta with respect to changes in
    the underlying asset's price. It represents the curvature of the option's
    value relative to the stock price.

    Args:
        S: Current stock price (spot price). Must be positive.
        K: Strike price (exercise price). Must be positive.
        T: Time to expiration in years.
        r: Risk-free interest rate (annualized), expressed as a decimal.
        sigma: Volatility (annualized standard deviation), expressed as a decimal.

    Returns:
        float: Gamma value (same for calls and puts).
            - Higher gamma means delta changes more rapidly
            - Gamma is highest for at-the-money options
            - Gamma approaches 0 for deep in/out-of-the-money options

    Raises:
        InvalidParameterError: If any parameter is invalid.

    Example:
        >>> gamma = calculate_gamma(
        ...     S=100,
        ...     K=100,
        ...     T=0.25,
        ...     r=0.05,
        ...     sigma=0.20
        ... )
        >>> print(f"Gamma: {gamma:.4f}")

    Notes:
        - Gamma is the same for call and put options with the same parameters.
        - High gamma means the option's delta is very sensitive to price changes.
        - Gamma is highest for at-the-money options near expiration.
        - Important for maintaining delta-neutral hedges.
    """
    # Validate inputs (use "call" as dummy option_type for validation)
    _validate_bsm_parameters(S, K, T, r, sigma, "call")

    # Handle edge case: at expiration (T=0)
    if T == 0:
        return 0.0

    # Calculate d1
    d1 = _calculate_d1(S, K, T, r, sigma)

    # Calculate gamma
    gamma = norm.pdf(d1) / (S * sigma * math.sqrt(T))

    return round(gamma, 6)


def calculate_vega(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
) -> float:
    """
    Calculate the Vega of an option.

    Vega measures the rate of change of the option price with respect to
    changes in the underlying asset's volatility. It represents sensitivity
    to implied volatility changes.

    Args:
        S: Current stock price (spot price). Must be positive.
        K: Strike price (exercise price). Must be positive.
        T: Time to expiration in years.
        r: Risk-free interest rate (annualized), expressed as a decimal.
        sigma: Volatility (annualized standard deviation), expressed as a decimal.

    Returns:
        float: Vega value (same for calls and puts).
            - Represents the change in option price for a 1% change in volatility
            - Vega is highest for at-the-money options
            - Vega increases with time to expiration

    Raises:
        InvalidParameterError: If any parameter is invalid.

    Example:
        >>> vega = calculate_vega(
        ...     S=100,
        ...     K=100,
        ...     T=0.25,
        ...     r=0.05,
        ...     sigma=0.20
        ... )
        >>> print(f"Vega: {vega:.4f}")
        >>> # Vega of 0.15 means if volatility increases by 1%, option value
        >>> # increases by $0.15

    Notes:
        - Vega is the same for call and put options with the same parameters.
        - Vega is positive for long options (higher volatility = higher value).
        - At-the-money options have the highest vega.
        - Vega decreases as expiration approaches.
    """
    # Validate inputs (use "call" as dummy option_type for validation)
    _validate_bsm_parameters(S, K, T, r, sigma, "call")

    # Handle edge case: at expiration (T=0)
    if T == 0:
        return 0.0

    # Calculate d1
    d1 = _calculate_d1(S, K, T, r, sigma)

    # Calculate vega (divide by 100 to get change per 1% volatility change)
    vega = S * norm.pdf(d1) * math.sqrt(T) / 100

    return round(vega, 4)


def calculate_rho(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: OptionType,
) -> float:
    """
    Calculate the Rho of an option.

    Rho measures the rate of change of the option price with respect to
    changes in the risk-free interest rate. It represents sensitivity to
    interest rate changes.

    Args:
        S: Current stock price (spot price). Must be positive.
        K: Strike price (exercise price). Must be positive.
        T: Time to expiration in years.
        r: Risk-free interest rate (annualized), expressed as a decimal.
        sigma: Volatility (annualized standard deviation), expressed as a decimal.
        option_type: Type of option, either "call" or "put".

    Returns:
        float: Rho value (per 1% change in interest rate).
            - Call options have positive rho
            - Put options have negative rho
            - Rho is larger for longer-dated options

    Raises:
        InvalidParameterError: If any parameter is invalid.

    Example:
        >>> rho = calculate_rho(
        ...     S=100,
        ...     K=100,
        ...     T=0.25,
        ...     r=0.05,
        ...     sigma=0.20,
        ...     option_type="call"
        ... )
        >>> print(f"Rho: {rho:.4f}")

    Notes:
        - Rho is typically less important than other Greeks for short-term options.
        - Becomes more significant for long-term options (LEAPS).
        - Call options benefit from higher interest rates (positive rho).
        - Put options lose value with higher interest rates (negative rho).
    """
    # Validate inputs
    _validate_bsm_parameters(S, K, T, r, sigma, option_type)

    # Handle edge case: at expiration (T=0)
    if T == 0:
        return 0.0

    # Calculate d1 and d2
    d1 = _calculate_d1(S, K, T, r, sigma)
    d2 = _calculate_d2(d1, sigma, T)

    # Calculate rho based on option type (divide by 100 for 1% change)
    if option_type.lower() == "call":
        rho = K * T * math.exp(-r * T) * norm.cdf(d2) / 100
    else:  # put
        rho = -K * T * math.exp(-r * T) * norm.cdf(-d2) / 100

    return round(rho, 4)
