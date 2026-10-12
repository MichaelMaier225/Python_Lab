import { useState } from "react"
import {
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  TouchableOpacity,
  Alert,
  ScrollView,
} from "react-native"
import { useRouter } from "expo-router"

import { useLanguage } from "../../hooks/use-language"
import { useCurrency } from "../../hooks/use-currency"
import { Currency, Language } from "../../store/settings"
import { clearHistory } from "../../store/products"
import { BrandColors } from "../../constants/brand"

const languageOptions: Array<{
  value: Language
  label: string
  detail: string
}> = [
  {
    value: "vi",
    label: "Tiếng Việt",
    detail: "Ngôn ngữ mặc định",
  },
  {
    value: "en",
    label: "English",
    detail: "English labels",
  },
]

export default function SettingsScreen() {
  const { language, setLanguage, t } = useLanguage()
  const [updating, setUpdating] = useState<Language | null>(null)
  const { currency, setCurrency } = useCurrency()
  const router = useRouter()

  const handleSelect = async (next: Language) => {
    setUpdating(next)
    await setLanguage(next)
    setUpdating(null)
  }

  const currencyOptions: Array<{
    value: Currency
    label: string
  }> = [
    { value: "USD", label: t("currencyUSD") },
    { value: "VND", label: t("currencyVND") },
  ]

  const clearHistoryOptions = [
    { key: "hourly", label: t("hourly"), durationMs: 60 * 60 * 1000 },
    { key: "daily", label: t("daily"), durationMs: 24 * 60 * 60 * 1000 },
    {
      key: "weekly",
      label: t("weekly"),
      durationMs: 7 * 24 * 60 * 60 * 1000,
    },
    {
      key: "monthly",
      label: t("monthly"),
      durationMs: 30 * 24 * 60 * 60 * 1000,
    },
    { key: "allTime", label: t("allTime"), durationMs: null },
  ]
  const [selectedClearDuration, setSelectedClearDuration] =
    useState<number | null>(clearHistoryOptions[1].durationMs)

  const quickLinks = [
    {
      key: "analytics",
      label: t("analytics"),
      detail: t("moreAnalyticsHelper"),
      onPress: () => router.push("/analytics"),
    },
    {
      key: "insights",
      label: t("insights"),
      detail: t("moreInsightsHelper"),
      onPress: () => router.push("/insights"),
    },
    {
      key: "explore",
      label: t("explore"),
      detail: t("moreExploreHelper"),
      onPress: () => router.push("/explore"),
    },
  ]

  const handleClearHistory = (durationMs: number | null) => {
    Alert.alert(
      t("clearHistoryWarningTitle"),
      t("clearHistoryWarningBody"),
      [
        {
          text: t("cancel"),
          style: "cancel",
        },
        {
          text: t("clear"),
          style: "destructive",
          onPress: () => {
            clearHistory(durationMs)
          },
        },
      ]
    )
  }

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView
        contentContainerStyle={styles.container}
        showsVerticalScrollIndicator={false}
      >
        <Text style={styles.title}>{t("settingsTitle")}</Text>

        <View style={[styles.card, styles.cardSpacing]}>
          <Text style={styles.sectionTitle}>{t("moreTools")}</Text>
          <Text style={styles.helperText}>{t("moreToolsHelper")}</Text>
          {quickLinks.map(link => (
            <TouchableOpacity
              key={link.key}
              style={styles.linkRow}
              onPress={link.onPress}
            >
              <View style={styles.optionText}>
                <Text style={styles.optionLabel}>{link.label}</Text>
                <Text style={styles.optionDetail}>{link.detail}</Text>
              </View>
              <Text style={styles.linkChevron}>›</Text>
            </TouchableOpacity>
          ))}
        </View>

        <View style={[styles.card, styles.cardSpacing]}>
          <Text style={styles.sectionTitle}>{t("appLanguage")}</Text>
          <Text style={styles.helperText}>
            {t("changeLanguageHelper")}
          </Text>
          {languageOptions.map(option => {
            const isActive = language === option.value
            return (
              <TouchableOpacity
                key={option.value}
                style={[
                  styles.optionRow,
                  isActive && styles.optionRowActive,
                ]}
                onPress={() => handleSelect(option.value)}
              >
                <View style={styles.optionText}>
                  <Text style={styles.optionLabel}>{option.label}</Text>
                  <Text style={styles.optionDetail}>{option.detail}</Text>
                </View>
                <Text style={styles.optionStatus}>
                  {isActive
                    ? "✓"
                    : updating === option.value
                    ? "…"
                    : ""}
                </Text>
              </TouchableOpacity>
            )
          })}
        </View>

        <View style={[styles.card, styles.cardSpacing]}>
          <Text style={styles.sectionTitle}>{t("currency")}</Text>
          <Text style={styles.helperText}>{t("currencyHelper")}</Text>
          {currencyOptions.map(option => {
            const isActive = currency === option.value
            return (
              <TouchableOpacity
                key={option.value}
                style={[
                  styles.optionRow,
                  isActive && styles.optionRowActive,
                ]}
                onPress={() => setCurrency(option.value)}
              >
                <View style={styles.optionText}>
                  <Text style={styles.optionLabel}>{option.label}</Text>
                </View>
                <Text style={styles.optionStatus}>
                  {isActive ? "✓" : ""}
                </Text>
              </TouchableOpacity>
            )
          })}
        </View>

        <View style={[styles.card, styles.cardSpacing]}>
          <Text style={styles.sectionTitle}>{t("clearHistory")}</Text>
          <Text style={styles.helperText}>
            {t("clearHistoryHelper")}
          </Text>
          {clearHistoryOptions.map(option => {
            const isSelected =
              selectedClearDuration === option.durationMs
            return (
              <TouchableOpacity
                key={option.key}
                style={[
                  styles.optionRow,
                  isSelected && styles.optionRowActive,
                ]}
                onPress={() =>
                  setSelectedClearDuration(option.durationMs)
                }
              >
                <Text style={styles.optionLabel}>{option.label}</Text>
                <Text style={styles.optionStatus}>
                  {isSelected ? "✓" : ""}
                </Text>
              </TouchableOpacity>
            )
          })}
          <TouchableOpacity
            style={styles.clearButton}
            onPress={() =>
              handleClearHistory(selectedClearDuration)
            }
          >
            <Text style={styles.clearButtonText}>
              {t("clear")}
            </Text>
          </TouchableOpacity>
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
    paddingBottom: 32,
  },
  title: {
    fontSize: 28,
    fontWeight: "700",
    marginBottom: 6,
    color: BrandColors.headerBackground,
  },
  cardSpacing: {
    marginTop: 16,
  },
  card: {
    borderWidth: 1,
    borderColor: BrandColors.cardBorder,
    borderRadius: 16,
    padding: 16,
    backgroundColor: BrandColors.card,
  },
  linkRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: BrandColors.cardBorder,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: "600",
    marginBottom: 12,
    color: BrandColors.textPrimary,
  },
  optionRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: BrandColors.cardBorder,
  },
  optionRowActive: {
    backgroundColor: BrandColors.cardAlt,
    borderRadius: 12,
    paddingHorizontal: 10,
  },
  optionText: {
    flex: 1,
  },
  optionLabel: {
    fontSize: 15,
    fontWeight: "600",
    color: BrandColors.textPrimary,
  },
  optionDetail: {
    fontSize: 12,
    color: BrandColors.textSecondary,
    marginTop: 2,
  },
  linkChevron: {
    width: 24,
    textAlign: "center",
    fontSize: 22,
    color: BrandColors.textSecondary,
  },
  optionStatus: {
    width: 24,
    textAlign: "center",
    fontSize: 18,
    color: BrandColors.accentDark,
  },
  helperText: {
    fontSize: 12,
    color: BrandColors.textSecondary,
    marginBottom: 12,
  },
  clearButton: {
    marginTop: 8,
    backgroundColor: BrandColors.accent,
    paddingVertical: 12,
    borderRadius: 12,
    alignItems: "center",
  },
  clearButtonText: {
    fontSize: 14,
    fontWeight: "600",
    color: BrandColors.textOnBrand,
  },
})
