import AsyncStorage from "@react-native-async-storage/async-storage"

export type Language = "en" | "vi"
export type Currency = "USD" | "VND"

const STORAGE_KEY = "SAVN_LANGUAGE"
const CURRENCY_KEY = "SAVN_CURRENCY"
const DEFAULT_LANGUAGE: Language = "vi"
const DEFAULT_CURRENCY: Currency = "USD"

let language: Language = DEFAULT_LANGUAGE
let currency: Currency = DEFAULT_CURRENCY
const listeners = new Set<(value: Language) => void>()
const currencyListeners = new Set<(value: Currency) => void>()

const notify = () => {
  listeners.forEach(listener => listener(language))
}

const notifyCurrency = () => {
  currencyListeners.forEach(listener => listener(currency))
}

const loadState = async () => {
  const storedLanguage = await AsyncStorage.getItem(STORAGE_KEY)
  if (storedLanguage === "en" || storedLanguage === "vi") {
    language = storedLanguage
    notify()
  }

  const storedCurrency = await AsyncStorage.getItem(CURRENCY_KEY)
  if (storedCurrency === "USD" || storedCurrency === "VND") {
    currency = storedCurrency
    notifyCurrency()
  }
}

loadState()

export const getLanguage = () => language
export const getCurrency = () => currency

export const setLanguage = async (nextLanguage: Language) => {
  if (language === nextLanguage) return
  language = nextLanguage
  await AsyncStorage.setItem(STORAGE_KEY, nextLanguage)
  notify()
}

export const setCurrency = async (nextCurrency: Currency) => {
  if (currency === nextCurrency) return
  currency = nextCurrency
  await AsyncStorage.setItem(CURRENCY_KEY, nextCurrency)
  notifyCurrency()
}

export const subscribeToLanguage = (
  listener: (value: Language) => void
) => {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

export const subscribeToCurrency = (
  listener: (value: Currency) => void
) => {
  currencyListeners.add(listener)
  return () => {
    currencyListeners.delete(listener)
  }
}
