import { useCallback, useState } from "react"
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  SafeAreaView,
  Alert,
  Modal,
  TextInput,
} from "react-native"
import { useFocusEffect, useRouter } from "expo-router"

import {
  getProducts,
  getActiveProducts,
  sellProduct,
  restockProduct,
  restockProductBulk,
  sellProductBulk,
  undoLastAction,
  Product,
} from "../../store/products"
import { useLanguage } from "../../hooks/use-language"
import { useCurrency } from "../../hooks/use-currency"
import { BrandColors } from "../../constants/brand"

export default function HomeScreen() {
  const [products, setProducts] = useState<Product[]>([])
  const [activeProducts, setActiveProducts] = useState<Product[]>([])
  const [canUndo, setCanUndo] = useState(false)
  const [bulkProduct, setBulkProduct] = useState<Product | null>(null)
  const [bulkQty, setBulkQty] = useState("1")
  const [bulkTotal, setBulkTotal] = useState("")
  const [bulkTotalTouched, setBulkTotalTouched] = useState(false)
  const [bulkSaleProduct, setBulkSaleProduct] =
    useState<Product | null>(null)
  const [bulkSaleQty, setBulkSaleQty] = useState("1")
  const [bulkSaleTotal, setBulkSaleTotal] = useState("")
  const [bulkSaleTotalTouched, setBulkSaleTotalTouched] =
    useState(false)
  const { t } = useLanguage()
  const router = useRouter()
  const { currency, formatMoney, toDisplayValue, fromDisplayValue } =
    useCurrency()
  const displayDecimals = currency === "VND" ? 0 : 2

  const refresh = () => {
    setProducts([...getProducts()])
    setActiveProducts([...getActiveProducts()])
  }

  useFocusEffect(
    useCallback(() => {
      refresh()
    }, [])
  )

  const openBulkRestock = (product: Product) => {
    setBulkProduct(product)
    setBulkQty("1")
    setBulkTotal(
      toDisplayValue(product.cost).toFixed(displayDecimals)
    )
    setBulkTotalTouched(false)
  }

  const closeBulkRestock = () => {
    setBulkProduct(null)
  }

  const openBulkSale = (product: Product) => {
    setBulkSaleProduct(product)
    setBulkSaleQty("1")
    setBulkSaleTotal(
      toDisplayValue(product.price).toFixed(displayDecimals)
    )
    setBulkSaleTotalTouched(false)
  }

  const closeBulkSale = () => {
    setBulkSaleProduct(null)
  }

  const applyBulkRestock = () => {
    if (!bulkProduct) return
    const qtyValue = Number.parseInt(bulkQty, 10)
    const totalValue = Number.parseFloat(bulkTotal)
    const totalUsd = fromDisplayValue(totalValue)

    if (Number.isNaN(qtyValue) || qtyValue <= 0) {
      Alert.alert(
        t("enterValidQuantityTitle"),
        t("enterValidQuantityBody")
      )
      return
    }

    if (Number.isNaN(totalValue) || totalValue < 0) {
      Alert.alert(
        t("enterValidTotalTitle"),
        t("enterValidTotalBody")
      )
      return
    }

    restockProductBulk(bulkProduct.id, qtyValue, totalUsd)
    setCanUndo(true)
    refresh()
    closeBulkRestock()
  }

  const applyBulkSale = () => {
    if (!bulkSaleProduct) return
    const qtyValue = Number.parseInt(bulkSaleQty, 10)
    const totalValue = Number.parseFloat(bulkSaleTotal)
    const totalUsd = fromDisplayValue(totalValue)

    if (Number.isNaN(qtyValue) || qtyValue <= 0) {
      Alert.alert(
        t("enterValidQuantityTitle"),
        t("enterValidQuantityBody")
      )
      return
    }

    if (qtyValue > bulkSaleProduct.qty) {
      Alert.alert(
        t("insufficientStockTitle"),
        t("insufficientStockBody")
      )
      return
    }

    if (Number.isNaN(totalValue) || totalValue < 0) {
      Alert.alert(
        t("enterValidTotalTitle"),
        t("enterValidTotalBody")
      )
      return
    }

    sellProductBulk(bulkSaleProduct.id, qtyValue, totalUsd)
    setCanUndo(true)
    refresh()
    closeBulkSale()
  }

  const updateBulkQty = (value: string) => {
    setBulkQty(value)
    const parsedQty = Number.parseInt(value, 10)
    if (
      bulkProduct &&
      !bulkTotalTouched &&
      !Number.isNaN(parsedQty) &&
      parsedQty > 0
    ) {
      setBulkTotal(
        toDisplayValue(parsedQty * bulkProduct.cost).toFixed(
          displayDecimals
        )
      )
    }
  }

  const updateBulkSaleQty = (value: string) => {
    setBulkSaleQty(value)
    const parsedQty = Number.parseInt(value, 10)
    if (
      bulkSaleProduct &&
      !bulkSaleTotalTouched &&
      !Number.isNaN(parsedQty) &&
      parsedQty > 0
    ) {
      setBulkSaleTotal(
        toDisplayValue(parsedQty * bulkSaleProduct.price).toFixed(
          displayDecimals
        )
      )
    }
  }

  const updateBulkTotal = (value: string) => {
    setBulkTotal(value)
    setBulkTotalTouched(true)
  }

  const updateBulkSaleTotal = (value: string) => {
    setBulkSaleTotal(value)
    setBulkSaleTotalTouched(true)
  }

  const parsedBulkQty = Number.parseInt(bulkQty, 10)
  const estimatedTotalUsd =
    bulkProduct && !Number.isNaN(parsedBulkQty) && parsedBulkQty > 0
      ? parsedBulkQty * bulkProduct.cost
      : 0
  const parsedBulkSaleQty = Number.parseInt(bulkSaleQty, 10)
  const estimatedSaleTotalUsd =
    bulkSaleProduct &&
    !Number.isNaN(parsedBulkSaleQty) &&
    parsedBulkSaleQty > 0
      ? parsedBulkSaleQty * bulkSaleProduct.price
      : 0

  const revenue = products.reduce((sum, p) => sum + p.revenue, 0)
  const expenses = products.reduce((sum, p) => sum + p.expenses, 0)
  const hasActiveProducts = activeProducts.length > 0

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.container}>
        <Text style={styles.title}>SAVN</Text>

        <Text style={styles.summaryText}>
          {t("revenue")}: {formatMoney(revenue)}
        </Text>
        <Text style={styles.summaryText}>
          {t("expenses")}: {formatMoney(expenses)}
        </Text>
        <Text style={styles.profit}>
          {t("profit")}: {formatMoney(revenue - expenses)}
        </Text>

        {hasActiveProducts ? (
          <>
            {activeProducts.map(p => (
              <View key={p.id} style={styles.row}>
                <View style={styles.nameWrap}>
                  <Text style={styles.name}>{p.name}</Text>
                </View>

                <View style={styles.controls}>
                  <TouchableOpacity
                    style={styles.btn}
                    onPress={() => {
                      sellProduct(p.id)
                      setCanUndo(true)
                      refresh()
                    }}
                    onLongPress={() => openBulkSale(p)}
                  >
                    <Text style={styles.btnText}>−</Text>
                  </TouchableOpacity>

                  <Text style={styles.qty}>{p.qty}</Text>

                  <TouchableOpacity
                    style={styles.btn}
                    onPress={() => {
                      restockProduct(p.id)
                      setCanUndo(true)
                      refresh()
                    }}
                    onLongPress={() => openBulkRestock(p)}
                  >
                    <Text style={styles.btnText}>+</Text>
                  </TouchableOpacity>

                  <TouchableOpacity
                    style={[
                      styles.undoBtn,
                      !canUndo && styles.undoDisabled,
                    ]}
                    disabled={!canUndo}
                    onPress={() => {
                      undoLastAction()
                      setCanUndo(false)
                      refresh()
                    }}
                  >
                    <Text
                      style={[
                        styles.undoText,
                        !canUndo && styles.undoTextDisabled,
                      ]}
                    >
                      ↺
                    </Text>
                  </TouchableOpacity>
                </View>
              </View>
            ))}

            <Text style={styles.helperText}>
              {t("holdRestock")}
            </Text>
          </>
        ) : (
          <View style={styles.emptyCard}>
            <Text style={styles.emptyTitle}>
              {t("emptyInventoryTitle")}
            </Text>
            <Text style={styles.emptyBody}>
              {t("emptyInventoryBody")}
            </Text>
            <TouchableOpacity
              style={styles.emptyButton}
              onPress={() => router.push("/catalog")}
            >
              <Text style={styles.emptyButtonText}>
                {t("emptyInventoryCta")}
              </Text>
            </TouchableOpacity>
          </View>
        )}
      </View>

      <Modal
        animationType="fade"
        transparent
        visible={!!bulkProduct}
        onRequestClose={closeBulkRestock}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>
              {t("bulkRestock")} {bulkProduct?.name}
            </Text>
            <Text style={styles.modalLabel}>{t("quantity")}</Text>
            <TextInput
              style={styles.modalInput}
              value={bulkQty}
              onChangeText={updateBulkQty}
              keyboardType="number-pad"
              placeholder={t("enterQuantity")}
            />
            <Text style={styles.modalHint}>
              {t("estimatedTotal")}: {formatMoney(estimatedTotalUsd)} (
              {t("qtyUnitCost")})
            </Text>
            <Text style={styles.modalLabel}>{t("totalCost")}</Text>
            <TextInput
              style={styles.modalInput}
              value={bulkTotal}
              onChangeText={updateBulkTotal}
              keyboardType="decimal-pad"
              placeholder="0.00"
            />
            <View style={styles.modalActions}>
              <TouchableOpacity
                style={[styles.modalButton, styles.modalCancel]}
                onPress={closeBulkRestock}
              >
                <Text style={styles.modalCancelText}>{t("cancel")}</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.modalButton, styles.modalConfirm]}
                onPress={applyBulkRestock}
              >
                <Text style={styles.modalConfirmText}>{t("apply")}</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      <Modal
        animationType="fade"
        transparent
        visible={!!bulkSaleProduct}
        onRequestClose={closeBulkSale}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>
              {t("bulkSale")} {bulkSaleProduct?.name}
            </Text>
            <Text style={styles.modalLabel}>{t("quantity")}</Text>
            <TextInput
              style={styles.modalInput}
              value={bulkSaleQty}
              onChangeText={updateBulkSaleQty}
              keyboardType="number-pad"
              placeholder={t("enterQuantity")}
            />
            <Text style={styles.modalHint}>
              {t("estimatedTotal")}:{" "}
              {formatMoney(estimatedSaleTotalUsd)} (
              {t("qtyUnitPrice")})
            </Text>
            <Text style={styles.modalLabel}>{t("totalRevenue")}</Text>
            <TextInput
              style={styles.modalInput}
              value={bulkSaleTotal}
              onChangeText={updateBulkSaleTotal}
              keyboardType="decimal-pad"
              placeholder="0.00"
            />
            <View style={styles.modalActions}>
              <TouchableOpacity
                style={[styles.modalButton, styles.modalCancel]}
                onPress={closeBulkSale}
              >
                <Text style={styles.modalCancelText}>{t("cancel")}</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.modalButton, styles.modalConfirm]}
                onPress={applyBulkSale}
              >
                <Text style={styles.modalConfirmText}>{t("apply")}</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

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
  title: {
    fontSize: 32,
    fontWeight: "bold",
    marginBottom: 10,
    color: BrandColors.headerBackground,
  },
  summaryText: {
    color: BrandColors.textSecondary,
  },
  profit: {
    fontWeight: "bold",
    marginBottom: 10,
    color: BrandColors.headerBackground,
  },
  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 16,
    padding: 14,
    borderRadius: 16,
    backgroundColor: BrandColors.card,
    shadowColor: "#000",
    shadowOpacity: 0.08,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 6 },
    elevation: 2,
  },
  nameWrap: {
    flex: 1,
  },
  name: {
    fontSize: 18,
    color: BrandColors.textPrimary,
  },
  controls: {
    flexDirection: "row",
    alignItems: "center",
  },
  btn: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: BrandColors.accent,
    alignItems: "center",
    justifyContent: "center",
  },
  btnText: {
    color: BrandColors.textOnBrand,
    fontSize: 26,
  },
  qty: {
    marginHorizontal: 10,
    color: BrandColors.textPrimary,
  },
  undoBtn: {
    marginLeft: 10,
    width: 36,
    height: 36,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: BrandColors.cardBorder,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: BrandColors.cardAlt,
  },
  undoDisabled: {
    borderColor: BrandColors.cardBorder,
  },
  undoText: {
    fontSize: 18,
    fontWeight: "bold",
    color: BrandColors.textSecondary,
  },
  undoTextDisabled: {
    color: BrandColors.cardBorder,
  },
  helperText: {
    marginTop: "auto",
    textAlign: "center",
    color: BrandColors.textSecondary,
    fontSize: 13,
    paddingTop: 10,
  },
  emptyCard: {
    marginTop: 24,
    borderWidth: 1,
    borderColor: BrandColors.cardBorder,
    borderRadius: 16,
    padding: 16,
    backgroundColor: BrandColors.card,
  },
  emptyTitle: {
    fontSize: 16,
    fontWeight: "600",
    marginBottom: 6,
    color: BrandColors.textPrimary,
  },
  emptyBody: {
    color: BrandColors.textSecondary,
    marginBottom: 12,
    lineHeight: 20,
  },
  emptyButton: {
    backgroundColor: BrandColors.accent,
    paddingVertical: 10,
    borderRadius: 10,
    alignItems: "center",
  },
  emptyButtonText: {
    color: BrandColors.textOnBrand,
    fontWeight: "600",
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: "rgba(0, 0, 0, 0.5)",
    justifyContent: "center",
    alignItems: "center",
    padding: 20,
  },
  modalCard: {
    width: "100%",
    backgroundColor: BrandColors.card,
    borderRadius: 18,
    padding: 20,
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: "bold",
    marginBottom: 16,
    color: BrandColors.textPrimary,
  },
  modalLabel: {
    fontSize: 14,
    marginBottom: 6,
    color: BrandColors.textSecondary,
  },
  modalInput: {
    borderWidth: 1,
    borderColor: BrandColors.cardBorder,
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 16,
    marginBottom: 12,
    backgroundColor: BrandColors.cardAlt,
    color: BrandColors.textPrimary,
  },
  modalHint: {
    fontSize: 12,
    color: BrandColors.textSecondary,
    marginBottom: 12,
  },
  modalActions: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginTop: 8,
  },
  modalButton: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 12,
    alignItems: "center",
  },
  modalCancel: {
    backgroundColor: BrandColors.accentSoft,
    marginRight: 10,
  },
  modalConfirm: {
    backgroundColor: BrandColors.accent,
    marginLeft: 10,
  },
  modalCancelText: {
    color: BrandColors.accentDark,
    fontWeight: "600",
  },
  modalConfirmText: {
    color: BrandColors.textOnBrand,
    fontWeight: "600",
  },
})
