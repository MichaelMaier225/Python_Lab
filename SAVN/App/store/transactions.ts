import AsyncStorage from "@react-native-async-storage/async-storage"

export type TransactionType =
  | "sale"
  | "restock"
  | "adjustment"

export type Transaction = {
  id: number
  productId: number
  productName: string
  type: TransactionType
  quantity: number
  amount: number
  inventoryDelta?: number
  timestamp: number
}

const STORAGE_KEY = "SAVN_TRANSACTIONS"

let transactions: Transaction[] = []

const save = async () => {
  await AsyncStorage.setItem(
    STORAGE_KEY,
    JSON.stringify(transactions)
  )
}

const load = async () => {
  const raw = await AsyncStorage.getItem(STORAGE_KEY)
  if (raw) transactions = JSON.parse(raw)
}

load()

export const getTransactions = () => transactions

export const setTransactions = (next: Transaction[]) => {
  transactions = next
  save()
}

export const recordTransaction = (
  tx: Omit<Transaction, "id" | "timestamp">
) => {
  transactions.push({
    id: Date.now(),
    timestamp: Date.now(),
    ...tx,
  })

  save()
}
