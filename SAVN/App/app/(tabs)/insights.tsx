import { useCallback, useMemo, useState } from "react"
import {
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native"
import { useFocusEffect } from "expo-router"

import { getProducts, Product } from "../../store/products"
import { getTransactions, Transaction } from "../../store/transactions"
import { useCurrency } from "../../hooks/use-currency"
import { useLanguage } from "../../hooks/use-language"
import { InsightsSwitcher } from "../../components/insights-switcher"
import { BrandColors } from "../../constants/brand"

type RangeKey =
  | "hourly"
  | "daily"
  | "weekly"
  | "monthly"
  | "yearly"
  | "allTime"

type Bucket = {
  label: string
  start: number
  end: number
  revenue: number
  restockSpend: number
  salesCount: number
}

const monthLabels = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
]

const buildBuckets = (
  range: RangeKey,
  now: Date,
  transactions: Transaction[],
  allTimeLabel: string
): Bucket[] => {
  const buckets: Bucket[] = []
  const nowTime = now.getTime()

  if (range === "hourly") {
    const startOfHour = new Date(now)
    startOfHour.setMinutes(0, 0, 0)
    for (let i = 7; i >= 0; i -= 1) {
      const start = new Date(startOfHour)
      start.setHours(start.getHours() - i)
      const end = new Date(start)
      end.setHours(end.getHours() + 1)
      buckets.push({
        label: `${start.getHours()}h`,
        start: start.getTime(),
        end: Math.min(end.getTime(), nowTime),
        revenue: 0,
        restockSpend: 0,
        salesCount: 0,
      })
    }
  } else if (range === "daily") {
    const startOfDay = new Date(
      now.getFullYear(),
      now.getMonth(),
      now.getDate()
    )
    for (let i = 6; i >= 0; i -= 1) {
      const start = new Date(startOfDay)
      start.setDate(start.getDate() - i)
      const end = new Date(start)
      end.setDate(end.getDate() + 1)
      buckets.push({
        label: `${start.getMonth() + 1}/${start.getDate()}`,
        start: start.getTime(),
        end: Math.min(end.getTime(), nowTime),
        revenue: 0,
        restockSpend: 0,
        salesCount: 0,
      })
    }
  } else if (range === "weekly") {
    const startOfWeek = new Date(now)
    startOfWeek.setDate(now.getDate() - now.getDay())
    startOfWeek.setHours(0, 0, 0, 0)
    for (let i = 5; i >= 0; i -= 1) {
      const start = new Date(startOfWeek)
      start.setDate(start.getDate() - 7 * i)
      const end = new Date(start)
      end.setDate(end.getDate() + 7)
      buckets.push({
        label: `${start.getMonth() + 1}/${start.getDate()}`,
        start: start.getTime(),
        end: Math.min(end.getTime(), nowTime),
        revenue: 0,
        restockSpend: 0,
        salesCount: 0,
      })
    }
  } else if (range === "monthly") {
    for (let i = 5; i >= 0; i -= 1) {
      const start = new Date(now.getFullYear(), now.getMonth() - i, 1)
      const end = new Date(now.getFullYear(), now.getMonth() - i + 1, 1)
      buckets.push({
        label: monthLabels[start.getMonth()],
        start: start.getTime(),
        end: Math.min(end.getTime(), nowTime),
        revenue: 0,
        restockSpend: 0,
        salesCount: 0,
      })
    }
  } else if (range === "yearly") {
    for (let i = 11; i >= 0; i -= 1) {
      const start = new Date(now.getFullYear(), now.getMonth() - i, 1)
      const end = new Date(now.getFullYear(), now.getMonth() - i + 1, 1)
      buckets.push({
        label: `${monthLabels[start.getMonth()]} ${String(
          start.getFullYear()
        ).slice(-2)}`,
        start: start.getTime(),
        end: Math.min(end.getTime(), nowTime),
        revenue: 0,
        restockSpend: 0,
        salesCount: 0,
      })
    }
  } else {
    const earliest =
      transactions.length > 0
        ? Math.min(...transactions.map(tx => tx.timestamp))
        : nowTime
    buckets.push({
      label: allTimeLabel,
      start: earliest,
      end: nowTime,
      revenue: 0,
      restockSpend: 0,
      salesCount: 0,
    })
  }

  return buckets
}

export default function InsightsScreen() {
  const [products, setProducts] = useState<Product[]>([])
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [range, setRange] = useState<RangeKey>("daily")
  const [showMenu, setShowMenu] = useState(false)
  const { formatMoney } = useCurrency()
  const { t } = useLanguage()

  useFocusEffect(
    useCallback(() => {
      setProducts([...getProducts()])
      setTransactions([...getTransactions()])
    }, [])
  )

  const { buckets, summary, productSummaries } = useMemo(() => {
    const now = new Date()
    const buckets = buildBuckets(range, now, transactions, t("allTime"))
    const currentStart = buckets[buckets.length - 1]?.start ?? now.getTime()
    const rangeStart = buckets[0]?.start ?? now.getTime()

    const inRange = (start: number, end: number) =>
      transactions.filter(
        tx => tx.timestamp >= start && tx.timestamp <= end
      )

    const fillBuckets = buckets.map(bucket => {
      const bucketTx = inRange(bucket.start, bucket.end)
      const sales = bucketTx.filter(tx => tx.type === "sale")
      const restocks = bucketTx.filter(tx => tx.type === "restock")
      return {
        ...bucket,
        revenue: sales.reduce((sum, tx) => sum + tx.amount, 0),
        restockSpend: restocks.reduce((sum, tx) => sum + tx.amount, 0),
        salesCount: sales.reduce((sum, tx) => sum + tx.quantity, 0),
      }
    })

    const summaryTx = inRange(currentStart, now.getTime())
    const summarySales = summaryTx.filter(tx => tx.type === "sale")
    const summaryRestocks = summaryTx.filter(
      tx => tx.type === "restock"
    )
    const totalRevenue = summarySales.reduce(
      (sum, tx) => sum + tx.amount,
      0
    )
    const totalExpenses = summaryRestocks.reduce(
      (sum, tx) => sum + tx.amount,
      0
    )

    const rangeTx = inRange(rangeStart, now.getTime())
    const productSummaries = rangeTx.reduce(
      (acc, tx) => {
        const current = acc[tx.productId] ?? {
          id: tx.productId,
          name: tx.productName,
          revenue: 0,
          expenses: 0,
        }
        if (tx.type === "sale") {
          current.revenue += tx.amount
        }
        if (tx.type === "restock") {
          current.expenses += tx.amount
        }
        acc[tx.productId] = current
        return acc
      },
      {} as Record<
        number,
        { id: number; name: string; revenue: number; expenses: number }
      >
    )

    return {
      buckets: fillBuckets,
      summary: {
        totalRevenue,
        totalExpenses,
        profit: totalRevenue - totalExpenses,
        salesCount: summarySales.reduce(
          (sum, tx) => sum + tx.quantity,
          0
        ),
      },
      productSummaries: Object.values(productSummaries).sort(
        (a, b) => b.revenue - a.revenue
      ),
    }
  }, [range, t, transactions])

  const maxRevenue = Math.max(
    1,
    ...buckets.map(bucket => bucket.revenue)
  )
  const maxSales = Math.max(
    1,
    ...buckets.map(bucket => bucket.salesCount)
  )

  const rangeOptions: { key: RangeKey; label: string }[] = [
    { key: "hourly", label: t("hourly") },
    { key: "daily", label: t("daily") },
    { key: "weekly", label: t("weekly") },
    { key: "monthly", label: t("monthly") },
    { key: "yearly", label: t("yearly") },
    { key: "allTime", label: t("allTime") },
  ]

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.container}>
        <View style={styles.headerRow}>
          <View>
            <Text style={styles.title}>{t("insightsTitle")}</Text>
            <Text style={styles.subtitle}>{t("reportRange")}</Text>
          </View>
          <View style={styles.dropdownWrapper}>
            <Pressable
              style={styles.dropdownButton}
              onPress={() => setShowMenu(current => !current)}
            >
              <Text style={styles.dropdownLabel}>
                {rangeOptions.find(option => option.key === range)
                  ?.label ?? t("daily")}
              </Text>
              <Text style={styles.dropdownCaret}>▾</Text>
            </Pressable>
            {showMenu ? (
              <View style={styles.dropdownMenu}>
                {rangeOptions.map(option => (
                  <Pressable
                    key={option.key}
                    style={styles.dropdownItem}
                    onPress={() => {
                      setRange(option.key)
                      setShowMenu(false)
                    }}
                  >
                    <Text
                      style={
                        option.key === range
                          ? styles.dropdownItemActive
                          : styles.dropdownItemText
                      }
                    >
                      {option.label}
                    </Text>
                  </Pressable>
                ))}
              </View>
            ) : null}
          </View>
        </View>

        <InsightsSwitcher />

        <View style={styles.summaryRow}>
          <View style={styles.summaryCard}>
            <Text style={styles.summaryLabel}>{t("revenue")}</Text>
            <Text style={styles.summaryValue}>
              {formatMoney(summary.totalRevenue)}
            </Text>
          </View>
          <View style={styles.summaryCard}>
            <Text style={styles.summaryLabel}>{t("expenses")}</Text>
            <Text style={styles.summaryValue}>
              {formatMoney(summary.totalExpenses)}
            </Text>
          </View>
          <View style={styles.summaryCard}>
            <Text style={styles.summaryLabel}>{t("profit")}</Text>
            <Text style={styles.summaryValue}>
              {formatMoney(summary.profit)}
            </Text>
          </View>
          <View style={styles.summaryCard}>
            <Text style={styles.summaryLabel}>{t("totalSales")}</Text>
            <Text style={styles.summaryValue}>{summary.salesCount}</Text>
          </View>
          <View style={styles.summaryCard}>
            <Text style={styles.summaryLabel}>{t("totalProducts")}</Text>
            <Text style={styles.summaryValue}>{products.length}</Text>
          </View>
        </View>

        <Text style={styles.sectionTitle}>{t("productBreakdown")}</Text>
        <View style={styles.productCard}>
          <View style={styles.productHeaderRow}>
            <Text style={styles.productHeader}>{t("productName")}</Text>
            <View style={styles.productHeaderTotals}>
              <Text style={styles.productHeader}>{t("revenue")}</Text>
              <Text style={styles.productHeader}>{t("expenses")}</Text>
            </View>
          </View>
          {productSummaries.length ? (
            productSummaries.map(product => (
              <View key={product.id} style={styles.productRow}>
                <Text style={styles.productName}>{product.name}</Text>
                <View style={styles.productTotals}>
                  <Text style={styles.productValue}>
                    {formatMoney(product.revenue)}
                  </Text>
                  <Text style={styles.productValueAlt}>
                    {formatMoney(product.expenses)}
                  </Text>
                </View>
              </View>
            ))
          ) : (
            <Text style={styles.productEmpty}>{t("historyEmpty")}</Text>
          )}
          <Text style={styles.productNote}>
            {t("reportRange")}:{" "}
            {rangeOptions.find(option => option.key === range)?.label ??
              t("daily")}
          </Text>
        </View>

        <Text style={styles.sectionTitle}>{t("salesTrend")}</Text>
        <View style={styles.chartCard}>
          <View style={styles.chartBars}>
            {buckets.map(bucket => (
              <View key={bucket.label} style={styles.chartBarItem}>
                <View
                  style={[
                    styles.chartBar,
                    {
                      height: (bucket.revenue / maxRevenue) * 120,
                    },
                  ]}
                />
                <Text style={styles.chartLabel}>{bucket.label}</Text>
              </View>
            ))}
          </View>
          <Text style={styles.chartNote}>{t("revenue")}</Text>
        </View>

        <Text style={styles.sectionTitle}>{t("revenueVsRestock")}</Text>
        <View style={styles.chartCard}>
          <View style={styles.compareRow}>
            <View style={styles.compareItem}>
              <Text style={styles.compareLabel}>{t("revenue")}</Text>
              <View style={styles.compareBarTrack}>
                <View
                  style={[
                    styles.compareBarFill,
                    {
                      width: `${Math.min(
                        100,
                        (summary.totalRevenue /
                          Math.max(summary.totalExpenses, 1)) *
                          100
                      )}%`,
                    },
                  ]}
                />
              </View>
              <Text style={styles.compareValue}>
                {formatMoney(summary.totalRevenue)}
              </Text>
            </View>
            <View style={styles.compareItem}>
              <Text style={styles.compareLabel}>{t("expenses")}</Text>
              <View style={styles.compareBarTrack}>
                <View
                  style={[
                    styles.compareBarFillAlt,
                    {
                      width: `${Math.min(
                        100,
                        (summary.totalExpenses /
                          Math.max(summary.totalRevenue, 1)) *
                          100
                      )}%`,
                    },
                  ]}
                />
              </View>
              <Text style={styles.compareValue}>
                {formatMoney(summary.totalExpenses)}
              </Text>
            </View>
          </View>
          <View style={styles.salesCountRow}>
            {buckets.map(bucket => (
              <View key={`${bucket.label}-count`} style={styles.countItem}>
                <Text style={styles.countValue}>{bucket.salesCount}</Text>
                <View style={styles.countBarTrack}>
                  <View
                    style={[
                      styles.countBarFill,
                      {
                        width: `${Math.min(
                          100,
                          (bucket.salesCount / maxSales) * 100
                        )}%`,
                      },
                    ]}
                  />
                </View>
                <Text style={styles.countLabel}>{bucket.label}</Text>
              </View>
            ))}
          </View>
          <Text style={styles.chartNote}>{t("totalSales")}</Text>
        </View>
      </ScrollView>
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
    paddingBottom: 40,
  },
  headerRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginBottom: 12,
  },
  title: {
    fontSize: 28,
    fontWeight: "700",
    color: BrandColors.headerBackground,
  },
  subtitle: {
    fontSize: 14,
    color: BrandColors.textSecondary,
    marginTop: 4,
  },
  dropdownWrapper: {
    alignItems: "flex-end",
  },
  dropdownButton: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: BrandColors.cardBorder,
    backgroundColor: BrandColors.card,
    gap: 6,
  },
  dropdownLabel: {
    fontSize: 14,
    fontWeight: "600",
    color: BrandColors.textPrimary,
  },
  dropdownCaret: {
    fontSize: 12,
    color: BrandColors.textSecondary,
  },
  dropdownMenu: {
    marginTop: 8,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: BrandColors.cardBorder,
    backgroundColor: BrandColors.card,
    width: 150,
    paddingVertical: 6,
  },
  dropdownItem: {
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  dropdownItemText: {
    fontSize: 14,
    color: BrandColors.textPrimary,
  },
  dropdownItemActive: {
    fontSize: 14,
    fontWeight: "700",
    color: BrandColors.accent,
  },
  summaryRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 12,
    marginBottom: 10,
  },
  summaryCard: {
    width: "48%",
    padding: 14,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: BrandColors.cardBorder,
    backgroundColor: BrandColors.card,
  },
  summaryLabel: {
    fontSize: 12,
    color: BrandColors.textSecondary,
    marginBottom: 6,
  },
  summaryValue: {
    fontSize: 16,
    fontWeight: "700",
    color: BrandColors.textPrimary,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: "600",
    marginTop: 10,
    marginBottom: 10,
    color: BrandColors.headerBackground,
  },
  productCard: {
    borderRadius: 16,
    borderWidth: 1,
    borderColor: BrandColors.cardBorder,
    backgroundColor: BrandColors.card,
    padding: 14,
    marginBottom: 16,
  },
  productHeaderRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 10,
  },
  productHeaderTotals: {
    flexDirection: "row",
    gap: 16,
  },
  productHeader: {
    fontSize: 12,
    fontWeight: "600",
    color: BrandColors.textSecondary,
  },
  productRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: BrandColors.cardBorder,
  },
  productName: {
    flex: 1,
    fontSize: 14,
    fontWeight: "600",
    color: BrandColors.textPrimary,
    marginRight: 12,
  },
  productTotals: {
    flexDirection: "row",
    gap: 16,
  },
  productValue: {
    fontSize: 13,
    fontWeight: "600",
    color: BrandColors.accent,
  },
  productValueAlt: {
    fontSize: 13,
    fontWeight: "600",
    color: BrandColors.accentDark,
  },
  productEmpty: {
    fontSize: 12,
    color: BrandColors.textSecondary,
    textAlign: "center",
    paddingVertical: 12,
  },
  productNote: {
    fontSize: 12,
    color: BrandColors.textSecondary,
    marginTop: 10,
  },
  chartCard: {
    borderRadius: 16,
    borderWidth: 1,
    borderColor: BrandColors.cardBorder,
    backgroundColor: BrandColors.card,
    padding: 14,
    marginBottom: 16,
  },
  chartBars: {
    flexDirection: "row",
    alignItems: "flex-end",
    justifyContent: "space-between",
    height: 150,
  },
  chartBarItem: {
    alignItems: "center",
    flex: 1,
  },
  chartBar: {
    width: 18,
    borderRadius: 6,
    backgroundColor: BrandColors.accent,
  },
  chartLabel: {
    fontSize: 10,
    color: BrandColors.textSecondary,
    marginTop: 6,
  },
  chartNote: {
    fontSize: 12,
    color: BrandColors.textSecondary,
    marginTop: 8,
  },
  compareRow: {
    gap: 12,
  },
  compareItem: {
    marginBottom: 10,
  },
  compareLabel: {
    fontSize: 12,
    color: BrandColors.textSecondary,
    marginBottom: 4,
  },
  compareBarTrack: {
    height: 8,
    borderRadius: 999,
    backgroundColor: BrandColors.cardAlt,
    overflow: "hidden",
  },
  compareBarFill: {
    height: 8,
    borderRadius: 999,
    backgroundColor: BrandColors.accent,
  },
  compareBarFillAlt: {
    height: 8,
    borderRadius: 999,
    backgroundColor: BrandColors.accentDark,
  },
  compareValue: {
    fontSize: 13,
    fontWeight: "600",
    marginTop: 6,
    color: BrandColors.textPrimary,
  },
  salesCountRow: {
    marginTop: 10,
    gap: 8,
  },
  countItem: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  countValue: {
    width: 28,
    textAlign: "right",
    fontSize: 12,
    fontWeight: "600",
    color: BrandColors.textPrimary,
  },
  countBarTrack: {
    flex: 1,
    height: 6,
    borderRadius: 999,
    backgroundColor: BrandColors.cardAlt,
    overflow: "hidden",
  },
  countBarFill: {
    height: 6,
    borderRadius: 999,
    backgroundColor: BrandColors.success,
  },
  countLabel: {
    width: 52,
    fontSize: 10,
    color: BrandColors.textSecondary,
    textAlign: "right",
  },
})
