import { useMemo } from "react"
import { StyleSheet, Text, TouchableOpacity, View } from "react-native"
import { usePathname, useRouter } from "expo-router"

import { useLanguage } from "../hooks/use-language"
import { BrandColors } from "../constants/brand"

const routes = [
  { key: "analytics", path: "/analytics" },
  { key: "insights", path: "/insights" },
  { key: "explore", path: "/explore" },
] as const

export function InsightsSwitcher() {
  const { t } = useLanguage()
  const router = useRouter()
  const pathname = usePathname()

  const activeKey = useMemo(() => {
    const match = routes.find(route => pathname.includes(route.key))
    return match?.key ?? "analytics"
  }, [pathname])

  return (
    <View style={styles.container}>
      {routes.map(route => {
        const isActive = route.key === activeKey
        return (
          <TouchableOpacity
            key={route.key}
            style={[styles.pill, isActive && styles.pillActive]}
            onPress={() => router.push(route.path)}
          >
            <Text
              style={[styles.pillText, isActive && styles.pillTextActive]}
            >
              {t(route.key)}
            </Text>
          </TouchableOpacity>
        )
      })}
    </View>
  )
}

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",
    backgroundColor: BrandColors.backgroundDark,
    borderRadius: 999,
    padding: 4,
    marginTop: 12,
    marginBottom: 18,
  },
  pill: {
    flex: 1,
    paddingVertical: 8,
    alignItems: "center",
    borderRadius: 999,
  },
  pillActive: {
    backgroundColor: BrandColors.card,
    shadowColor: "#000",
    shadowOpacity: 0.08,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 2 },
    elevation: 2,
  },
  pillText: {
    fontSize: 12,
    fontWeight: "600",
    color: BrandColors.textOnBrandMuted,
  },
  pillTextActive: {
    color: BrandColors.textPrimary,
  },
})
