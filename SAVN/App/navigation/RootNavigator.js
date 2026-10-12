import React from "react";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { Ionicons } from "@expo/vector-icons";

import HomeScreen from "../screens/HomeScreen";
import AddScreen from "../screens/AddScreen";
import HistoryScreen from "../screens/HistoryScreen";
import MoreScreen from "../screens/MoreScreen";

const Tab = createBottomTabNavigator();

const getTabIcon = (routeName, focused) => {
  const color = focused ? "#1B6EF3" : "#9AA0A6";
  switch (routeName) {
    case "Home":
      return <Ionicons name={focused ? "home" : "home-outline"} size={24} color={color} />;
    case "Add":
      return <Ionicons name={focused ? "add-circle" : "add-circle-outline"} size={24} color={color} />;
    case "History":
      return (
        <Ionicons
          name={focused ? "time" : "time-outline"}
          size={24}
          color={color}
        />
      );
    case "More":
      return (
        <Ionicons
          name={focused ? "ellipsis-horizontal" : "ellipsis-horizontal-outline"}
          size={24}
          color={color}
        />
      );
    default:
      return null;
  }
};

const RootNavigator = () => {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarIcon: ({ focused }) => getTabIcon(route.name, focused),
        tabBarActiveTintColor: "#1B6EF3",
        tabBarInactiveTintColor: "#9AA0A6",
        tabBarStyle: {
          height: 64,
          paddingTop: 8,
          paddingBottom: 8,
        },
        tabBarLabelStyle: {
          fontSize: 12,
          fontWeight: "600",
        },
      })}
    >
      <Tab.Screen name="Home" component={HomeScreen} />
      <Tab.Screen name="Add" component={AddScreen} />
      <Tab.Screen name="History" component={HistoryScreen} />
      <Tab.Screen name="More" component={MoreScreen} />
    </Tab.Navigator>
  );
};

export default RootNavigator;
