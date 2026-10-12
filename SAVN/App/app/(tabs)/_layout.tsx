import { Tabs } from "expo-router"

import { IconSymbol } from "@/components/ui/icon-symbol"
import { BrandColors } from "../../constants/brand"

export default function TabLayout() {
  return (
    <Tabs
      initialRouteName="index"
      screenOptions={{
        tabBarActiveTintColor: "#ffffff",
        tabBarInactiveTintColor: "rgba(255,255,255,0.7)",
        tabBarLabelStyle: { fontSize: 10, fontWeight: "600" },
        tabBarStyle: {
          backgroundColor: BrandColors.footerBackground,
          borderTopColor: BrandColors.footerBackground,
          borderTopWidth: 0,
          paddingTop: 6,
          paddingBottom: 8,
          height: 62,
          elevation: 0,
          shadowOpacity: 0,
        },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: "Home",
          tabBarIcon: ({ color }) => (
            <IconSymbol name="house.fill" color={color} size={22} />
          ),
        }}
      />
      <Tabs.Screen
        name="catalog"
        options={{
          title: "Add",
          tabBarIcon: ({ color }) => (
            <IconSymbol
              name="plus.circle.fill"
              color={color}
              size={24}
            />
          ),
          tabBarActiveTintColor: "#ffffff",
          tabBarIconStyle: { marginTop: 0 },
        }}
      />
      <Tabs.Screen
        name="history"
        options={{
          title: "History",
          tabBarIcon: ({ color }) => (
            <IconSymbol name="clock.fill" color={color} size={22} />
          ),
        }}
      />
      <Tabs.Screen
        name="settings"
        options={{
          title: "More",
          tabBarIcon: ({ color }) => (
            <IconSymbol
              name="line.3.horizontal"
              color={color}
              size={22}
            />
          ),
        }}
      />

      {/* Hidden routes kept for nested navigation from the More tab. */}
      <Tabs.Screen name="explore" options={{ href: null }} />
      <Tabs.Screen name="analytics" options={{ href: null }} />
      <Tabs.Screen name="insights" options={{ href: null }} />
    </Tabs>
  )
}
