import React from "react";
import { NavigationContainer } from "@react-navigation/native";
import { StatusBar } from "expo-status-bar";

import RootNavigator from "./navigation/RootNavigator";
import { TransactionsProvider } from "./store/TransactionsContext";

const App = () => {
  return (
    <TransactionsProvider>
      <NavigationContainer>
        <StatusBar style="light" />
        <RootNavigator />
      </NavigationContainer>
    </TransactionsProvider>
  );
};

export default App;
