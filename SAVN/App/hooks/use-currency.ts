import { useCallback, useEffect, useMemo, useState } from "react"

import {
  Currency,
  getCurrency,
  setCurrency,
  subscribeToCurrency,
} from "../store/settings"

type MoneyFormatter = (value: number) => string

const createFormatter = (
  currency: Currency
): MoneyFormatter => {
  const locale = currency === "VND" ? "vi-VN" : "en-US"
  const format = new Intl.NumberFormat(locale, {
    style: "currency",
    currency,
    maximumFractionDigits: currency === "VND" ? 0 : 2,
  })

  return (value: number) => {
    return format.format(value)
  }
}

export const useCurrency = () => {
  const [currency, setCurrencyState] = useState<Currency>(
    getCurrency()
  )

  useEffect(() => {
    const unsubscribeCurrency = subscribeToCurrency(next => {
      setCurrencyState(next)
    })
    return () => {
      unsubscribeCurrency()
    }
  }, [])

  const formatter = useMemo(
    () => createFormatter(currency),
    [currency]
  )

  const formatMoney = useCallback(
    (value: number) => formatter(value),
    [formatter]
  )

  const toDisplayValue = useCallback(
    (value: number) => value,
    []
  )

  const fromDisplayValue = useCallback(
    (value: number) => value,
    []
  )

  const updateCurrency = useCallback(
    (next: Currency) => {
      setCurrency(next)
    },
    []
  )

  return useMemo(
    () => ({
      currency,
      formatMoney,
      toDisplayValue,
      fromDisplayValue,
      setCurrency: updateCurrency,
    }),
    [
      currency,
      formatMoney,
      toDisplayValue,
      fromDisplayValue,
      updateCurrency,
    ]
  )
}
