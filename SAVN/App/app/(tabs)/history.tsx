import { useCallback, useMemo, useState } from "react"
import {
  Alert,
  View,
  Text,
  FlatList,
  StyleSheet,
  SafeAreaView,
  Pressable,
} from "react-native"
import { useFocusEffect } from "expo-router"

import { getTransactions, Transaction } from "../../store/transactions"
import { undoTransaction } from "../../store/products"
import { useLanguage } from "../../hooks/use-language"
import { useCurrency } from "../../hooks/use-currency"
import { BrandColors } from "../../constants/brand"

const formatTime = (timestamp: number) => {
  const date = new Date(timestamp)
  return date.toLocaleString()
}

const applyTemplate = (
  template: string,
  data: Record<string, string>
) =>
  Object.entries(data).reduce(
    (acc, [key, value]) => acc.replace(`{${key}}`, value),
    template
  )

export default function HistoryScreen() {
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const { t } = useLanguage()
  const { formatMoney } = useCurrency()

  const refreshTransactions = useCallback(() => {
    const data = [...getTransactions()].reverse()
    setTransactions(data)
  }, [])

  useFocusEffect(
    useCallback(() => {
      refreshTransactions()
    }, [refreshTransactions])
  )

  const templateByType = useMemo(
    () => ({
      sale: t("historySale"),
      restock: t("historyRestock"),
      adjustment: t("historyAdjustment"),
    }),
    [t]
  )

  const formatRow = (transaction: Transaction) => {
    const template = templateByType[transaction.type]
    return applyTemplate(template, {
      quantity: String(transaction.quantity),
      product: transaction.productName,
      amount: formatMoney(transaction.amount),
    })
  }

  const handleUndo = useCallback(
    (transaction: Transaction) => {
      Alert.alert(
        t("undoTransactionTitle"),
        t("undoTransactionBody"),
        [
          { text: t("cancel"), style: "cancel" },
          {
            text: t("undo"),
            style: "destructive",
            onPress: () => {
              undoTransaction(transaction.id)
              refreshTransactions()
            },
          },
        ],
        { cancelable: true }
      )
    },
    [refreshTransactions, t]
  )

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.container}>
        <Text style={styles.title}>{t("historyTitle")}</Text>

        <FlatList
          data={transactions}
          keyExtractor={item => String(item.id)}
          contentContainerStyle={styles.list}
          ItemSeparatorComponent={() => (
            <View style={styles.separator} />
          )}
          renderItem={({ item }) => (
            <View style={styles.row}>
              <View style={styles.rowHeader}>
                <Text style={styles.text}>{formatRow(item)}</Text>
                <Pressable
                  onPress={() => handleUndo(item)}
                  accessibilityRole="button"
                  accessibilityLabel={t("undo")}
                >
                  <Text style={styles.undo}>{t("undo")}</Text>
                </Pressable>
              </View>
              <Text style={styles.time}>
                {formatTime(item.timestamp)}
              </Text>
            </View>
          )}
          ListEmptyComponent={
            <Text style={styles.empty}>{t("historyEmpty")}</Text>
          }
        />
      </View>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: BrandColors.pageBackground,
  },
  container: {
    padding: 20,
    flex: 1,
  },
  list: {
    paddingBottom: 12,
  },
  title: {
    fontSize: 28,
    fontWeight: "bold",
    marginBottom: 20,
    color: BrandColors.headerBackground,
  },
  row: {
    padding: 14,
    borderRadius: 16,
    backgroundColor: BrandColors.card,
    shadowColor: "#000",
    shadowOpacity: 0.08,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 6 },
    elevation: 2,
  },
  rowHeader: {
    flexDirection: "row",
    alignItems: "flex-start",
    justifyContent: "space-between",
    gap: 12,
  },
  text: {
    fontSize: 15,
    flex: 1,
    color: BrandColors.textPrimary,
  },
  time: {
    fontSize: 12,
    color: BrandColors.textSecondary,
    marginTop: 2,
  },
  undo: {
    fontSize: 13,
    color: BrandColors.accentDark,
  },
  separator: {
    height: 12,
  },
  empty: {
    textAlign: "center",
    marginTop: 40,
    color: BrandColors.textSecondary,
    lineHeight: 20,
  },
})
