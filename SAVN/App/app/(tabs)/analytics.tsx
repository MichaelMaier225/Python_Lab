import {
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  ScrollView,
} from "react-native"
import { useCallback, useMemo, useState } from "react"
import { useFocusEffect } from "expo-router"

import { getProducts, Product } from "../../store/products"
import {
  getTransactions,
  Transaction,
} from "../../store/transactions"
import { useLanguage } from "../../hooks/use-language"
import { useCurrency } from "../../hooks/use-currency"
import { InsightsSwitcher } from "../../components/insights-switcher"
import { BrandColors } from "../../constants/brand"

export default function AnalyticsScreen() {
  const [products, setProducts] = useState<Product[]>([])
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const { t } = useLanguage()
  const { formatMoney } = useCurrency()

  useFocusEffect(
    useCallback(() => {
      setProducts([...getProducts()])
      setTransactions([...getTransactions()])
    }, [])
  )

  const {
    periodSummaries,
    totals,
    productInsights,
    inventoryInsights,
  } = useMemo(() => {
    const now = new Date()
    const nowTs = now.getTime()
    const dayMs = 24 * 60 * 60 * 1000

    const startOfDay = new Date(
      now.getFullYear(),
      now.getMonth(),
      now.getDate()
    ).getTime()

    const startOfWeekDate = new Date(now)
    startOfWeekDate.setDate(now.getDate() - now.getDay())
    startOfWeekDate.setHours(0, 0, 0, 0)

    const startOfMonth = new Date(
      now.getFullYear(),
      now.getMonth(),
      1
    ).getTime()

    const startOfYear = new Date(
      now.getFullYear(),
      0,
      1
    ).getTime()

    const byType = (type: Transaction["type"]) =>
      transactions.filter(tx => tx.type === type)

    const sumAmount = (items: Transaction[]) =>
      items.reduce((sum, tx) => sum + tx.amount, 0)

    const inRange = (start: number, end: number) =>
      transactions.filter(
        tx => tx.timestamp >= start && tx.timestamp <= end
      )

    const summarizePeriod = (label: string, start: number, end: number) => {
      const periodTx = inRange(start, end)
      const sales = periodTx.filter(tx => tx.type === "sale")
      const restocks = periodTx.filter(
        tx => tx.type === "restock"
      )
      const revenue = sumAmount(sales)
      const restockSpend = sumAmount(restocks)
      const salesCount = sales.length
      return {
        label,
        revenue,
        restockSpend,
        salesCount,
        avgSale: salesCount > 0 ? revenue / salesCount : 0,
        profit: revenue - restockSpend,
      }
    }

    const periodSummaries = [
      summarizePeriod(t("periodToday"), startOfDay, nowTs),
      summarizePeriod(
        t("periodWeek"),
        startOfWeekDate.getTime(),
        nowTs
      ),
      summarizePeriod(t("periodMonth"), startOfMonth, nowTs),
      summarizePeriod(t("periodYear"), startOfYear, nowTs),
    ]

    const totalSales = byType("sale")
    const totalRestocks = byType("restock")
    const totalRevenue = sumAmount(totalSales)
    const totalRestockSpend = sumAmount(totalRestocks)
    const grossProfit = totalRevenue - totalRestockSpend
    const grossMargin =
      totalRevenue > 0 ? (grossProfit / totalRevenue) * 100 : 0

    const saleByProduct = totalSales.reduce(
      (acc, tx) => {
        const current = acc[tx.productId] ?? {
          name: tx.productName,
          revenue: 0,
          quantity: 0,
        }
        current.revenue += tx.amount
        current.quantity += tx.quantity
        acc[tx.productId] = current
        return acc
      },
      {} as Record<
        number,
        { name: string; revenue: number; quantity: number }
      >
    )

    const salesList = Object.values(saleByProduct)
    const topRevenueProduct =
      salesList.length > 0
        ? [...salesList].sort((a, b) => b.revenue - a.revenue)[0]
        : null
    const topVolumeProduct =
      salesList.length > 0
        ? [...salesList].sort((a, b) => b.quantity - a.quantity)[0]
        : null
    const slowMoverProduct =
      salesList.length > 0
        ? [...salesList].sort((a, b) => a.quantity - b.quantity)[0]
        : null

    const restockByProduct = totalRestocks.reduce(
      (acc, tx) => {
        const current = acc[tx.productId] ?? {
          name: tx.productName,
          quantity: 0,
        }
        current.quantity += tx.quantity
        acc[tx.productId] = current
        return acc
      },
      {} as Record<number, { name: string; quantity: number }>
    )
    const restockList = Object.values(restockByProduct)
    const mostRestocked =
      restockList.length > 0
        ? [...restockList].sort((a, b) => b.quantity - a.quantity)[0]
        : null

    const marginCandidates = products.map(product => {
      const unitMargin = product.price - product.cost
      const marginPercent =
        product.price > 0 ? (unitMargin / product.price) * 100 : 0
      return { name: product.name, marginPercent }
    })
    const bestMarginProduct =
      marginCandidates.length > 0
        ? [...marginCandidates].sort(
            (a, b) => b.marginPercent - a.marginPercent
          )[0]
        : null

    const activeProducts = products.filter(
      product => !product.isArchived
    )
    const lowStock = activeProducts.filter(
      product => product.qty <= 5
    )
    const inventoryValue = activeProducts.reduce(
      (sum, product) => sum + product.qty * product.cost,
      0
    )
    const potentialRevenue = activeProducts.reduce(
      (sum, product) => sum + product.qty * product.price,
      0
    )

    return {
      periodSummaries,
      totals: {
        totalRevenue,
        totalRestockSpend,
        grossProfit,
        grossMargin,
        salesCount: totalSales.length,
      },
      productInsights: {
        topRevenueProduct,
        topVolumeProduct,
        slowMoverProduct,
        mostRestocked,
        bestMarginProduct,
      },
      inventoryInsights: {
        activeCount: activeProducts.length,
        lowStock,
        inventoryValue,
        potentialRevenue,
        daysTracked: Math.max(
          1,
          Math.ceil((nowTs - startOfYear) / dayMs)
        ),
      },
    }
  }, [products, t, transactions])

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.container}>
        <Text style={styles.title}>{t("analyticsTitle")}</Text>
        <InsightsSwitcher />
        <Text style={styles.subtitle}>{t("salesOverview")}</Text>

        <View style={styles.grid}>
          {periodSummaries.map(period => (
            <View key={period.label} style={styles.card}>
              <Text style={styles.cardTitle}>{period.label}</Text>
              <Text style={styles.metric}>
                {formatMoney(period.revenue)}
              </Text>
              <Text style={styles.detail}>
                {t("sales")}: {period.salesCount}
              </Text>
              <Text style={styles.detail}>
                {t("avgSale")}: {formatMoney(period.avgSale)}
              </Text>
              <Text style={styles.detail}>
                {t("restock")}: {formatMoney(period.restockSpend)}
              </Text>
              <Text style={styles.detailBold}>
                {t("profit")}: {formatMoney(period.profit)}
              </Text>
            </View>
          ))}
        </View>

        <Text style={styles.subtitle}>{t("businessHealth")}</Text>
        <View style={styles.cardWide}>
          <View style={styles.row}>
            <View style={styles.rowItem}>
              <Text style={styles.label}>{t("lifetimeRevenue")}</Text>
              <Text style={styles.value}>
                {formatMoney(totals.totalRevenue)}
              </Text>
            </View>
            <View style={styles.rowItem}>
              <Text style={styles.label}>{t("restockSpend")}</Text>
              <Text style={styles.value}>
                {formatMoney(totals.totalRestockSpend)}
              </Text>
            </View>
          </View>
          <View style={styles.row}>
            <View style={styles.rowItem}>
              <Text style={styles.label}>{t("grossProfit")}</Text>
              <Text style={styles.value}>
                {formatMoney(totals.grossProfit)}
              </Text>
            </View>
            <View style={styles.rowItem}>
              <Text style={styles.label}>{t("grossMargin")}</Text>
              <Text style={styles.value}>
                {totals.grossMargin.toFixed(1)}%
              </Text>
            </View>
          </View>
          <Text style={styles.helper}>
            {totals.salesCount} {t("salesLogged")}
          </Text>
        </View>

        <Text style={styles.subtitle}>{t("productInsights")}</Text>
        <View style={styles.cardWide}>
          <Text style={styles.label}>{t("topRevenueItem")}</Text>
          <Text style={styles.value}>
            {productInsights.topRevenueProduct
              ? `${productInsights.topRevenueProduct.name} · ${formatMoney(
                  productInsights.topRevenueProduct.revenue
                )}`
              : t("noSales")}
          </Text>
          <Text style={styles.label}>{t("mostSoldItem")}</Text>
          <Text style={styles.value}>
            {productInsights.topVolumeProduct
              ? `${productInsights.topVolumeProduct.name} · ${productInsights.topVolumeProduct.quantity} ${t("sold")}`
              : t("noSales")}
          </Text>
          <Text style={styles.label}>{t("slowMover")}</Text>
          <Text style={styles.value}>
            {productInsights.slowMoverProduct
              ? `${productInsights.slowMoverProduct.name} · ${productInsights.slowMoverProduct.quantity} ${t("sold")}`
              : t("noSales")}
          </Text>
          <Text style={styles.label}>{t("mostRestockedItem")}</Text>
          <Text style={styles.value}>
            {productInsights.mostRestocked
              ? `${productInsights.mostRestocked.name} · ${productInsights.mostRestocked.quantity} ${t("restocked")}`
              : t("noRestocks")}
          </Text>
          <Text style={styles.label}>{t("bestMarginItem")}</Text>
          <Text style={styles.value}>
            {productInsights.bestMarginProduct
              ? `${productInsights.bestMarginProduct.name} · ${productInsights.bestMarginProduct.marginPercent.toFixed(1)}%`
              : t("noSales")}
          </Text>
        </View>

        <Text style={styles.subtitle}>{t("inventoryWatch")}</Text>
        <View style={styles.cardWide}>
          <View style={styles.row}>
            <View style={styles.rowItem}>
              <Text style={styles.label}>{t("activeItems")}</Text>
              <Text style={styles.value}>
                {inventoryInsights.activeCount}
              </Text>
            </View>
            <View style={styles.rowItem}>
              <Text style={styles.label}>{t("inventoryValue")}</Text>
              <Text style={styles.value}>
                {formatMoney(inventoryInsights.inventoryValue)}
              </Text>
            </View>
          </View>
          <View style={styles.row}>
            <View style={styles.rowItem}>
              <Text style={styles.label}>{t("potentialRevenue")}</Text>
              <Text style={styles.value}>
                {formatMoney(inventoryInsights.potentialRevenue)}
              </Text>
            </View>
            <View style={styles.rowItem}>
              <Text style={styles.label}>{t("lowStock")}</Text>
              <Text style={styles.value}>
                {inventoryInsights.lowStock.length}
              </Text>
            </View>
          </View>
          <View style={styles.lowStockList}>
            {inventoryInsights.lowStock.length === 0 ? (
              <Text style={styles.helper}>
                {t("stockHealthy")}
              </Text>
            ) : (
              inventoryInsights.lowStock.slice(0, 4).map(product => (
                <Text key={product.id} style={styles.helper}>
                  {product.name} · {product.qty} {t("left")}
                </Text>
              ))
            )}
          </View>
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
  title: {
    fontSize: 28,
    fontWeight: "bold",
    marginBottom: 10,
    color: BrandColors.headerBackground,
  },
  subtitle: {
    fontSize: 18,
    fontWeight: "600",
    marginTop: 10,
    marginBottom: 10,
    color: BrandColors.headerBackground,
  },
  grid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 12,
  },
  card: {
    padding: 14,
    borderWidth: 1,
    borderColor: BrandColors.cardBorder,
    borderRadius: 14,
    backgroundColor: BrandColors.card,
    width: "48%",
    marginBottom: 12,
  },
  cardWide: {
    padding: 16,
    borderWidth: 1,
    borderColor: BrandColors.cardBorder,
    borderRadius: 16,
    backgroundColor: BrandColors.card,
    marginBottom: 16,
  },
  cardTitle: {
    fontSize: 14,
    fontWeight: "600",
    color: BrandColors.textSecondary,
    marginBottom: 6,
  },
  metric: {
    fontSize: 20,
    fontWeight: "700",
    marginBottom: 6,
    color: BrandColors.textPrimary,
  },
  detail: {
    fontSize: 13,
    color: BrandColors.textSecondary,
    marginBottom: 2,
  },
  detailBold: {
    fontSize: 13,
    fontWeight: "600",
    color: BrandColors.textPrimary,
    marginTop: 4,
  },
  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 12,
  },
  rowItem: {
    flex: 1,
    marginRight: 12,
  },
  label: {
    fontSize: 12,
    color: BrandColors.textSecondary,
    marginBottom: 4,
  },
  value: {
    fontSize: 16,
    fontWeight: "600",
    color: BrandColors.textPrimary,
  },
  helper: {
    fontSize: 13,
    color: BrandColors.textSecondary,
    marginTop: 4,
  },
  lowStockList: {
    marginTop: 6,
  },
})
